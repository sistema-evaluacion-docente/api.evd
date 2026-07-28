# ADR-006: WebSocket para Notificaciones en Tiempo Real

- **Estado**: Aceptado
- **Fecha**: 2026-07-26
- **Decisores**: Equipo de desarrollo

## Contexto

El sistema **api.evd** necesita notificar a los usuarios sobre eventos importantes de forma inmediata:

- Notificaciones manuales creadas por administradores y directores (avisos, alertas, comunicados)
- Notificaciones automáticas generadas al completar el procesamiento de evaluaciones
- Notificaciones automáticas al completar el análisis de IA de comentarios

Sin un mecanismo de push en tiempo real, los usuarios tendrían que hacer polling al endpoint `GET /notifications/me/unread-count` para detectar nuevas notificaciones, lo cual genera:

- Latencia alta entre la creación y la recepción
- Overhead de requests HTTP repetidos innecesarios
- Mala experiencia de usuario (el usuario no sabe si hay notificaciones nuevas hasta que recarga la página)

Las alternativas consideradas fueron:

1. **Polling HTTP**: El cliente consulta periódicamente `/notifications/me/unread-count`
2. **Server-Sent Events (SSE)**: Conexión unidireccional del servidor al cliente
3. **WebSocket bidireccional**: Conexión persistente full-duplex, coherente con los endpoints WS ya existentes (ADR-004 y ADR-005)

## Decisión

Se implementó un **WebSocket unidireccional con autenticación Firebase** que envía notificaciones en tiempo real a cada usuario a través de canales individuales. La arquitectura consiste en:

### Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Notification System                               │
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────────────────────────┐  │
│  │  POST /notifications│    │  evaluation_processor (Background)  │  │
│  │  (Admin/Director)  │    │  _create_process_notification()     │  │
│  └────────┬─────────┘     │  _create_analysis_notification()    │  │
│           │               └──────────────┬───────────────────────┘  │
│           ↓                              ↓                          │
│  ┌────────────────────────────────────────────┐                     │
│  │         NotificationService.create()        │                     │
│  │   (persiste en DB + broadcast por WS)       │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   ↓                                                  │
│  ┌────────────────────────────────────────────┐                     │
│  │    ConnectionManager (shared, channels)     │                     │
│  │    channel: "notifications:{user_id}"       │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   ↓                                                  │
│  ┌────────────────────────────────────────────┐                     │
│  │       WebSocket /ws/notifications           │                     │
│  │       (un WebSocket por usuario conectado)  │                     │
│  └────────────────┬───────────────────────────┘                     │
│                   ↓                                                  │
│  ┌────────────────────────────────────────────┐                     │
│  │          Frontend Client                     │                     │
│  │    (badge de notificaciones en tiempo real) │                     │
│  └────────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Modelo de Datos

```python
class NotificationModel(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String(255), nullable=False)
    message    = Column(Text, nullable=False)
    type       = Column(String(50), nullable=False, default="info")
    read       = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

Los tipos de notificación se definen a nivel de schema (no en la base de datos):

| Tipo      | Uso                                    |
| --------- | -------------------------------------- |
| `info`    | Información general, avisos            |
| `warning` | Advertencias que requieren atención    |
| `error`   | Errores del sistema o de procesamiento |
| `success` | Confirmaciones de acciones completadas |

### NotificationEvent (Evento WebSocket)

```python
class NotificationEvent(BaseWebSocketEvent):
    type: Literal["notification"] = "notification"
    notification_id: int
    user_id: int
    title: str
    message: str
    notification_type: str
```

Todos los eventos heredan de `BaseWebSocketEvent`, que provee `type` y `timestamp` (ISO 8601 UTC). El mensaje que recibe el cliente por WebSocket es:

```json
{
  "type": "notification",
  "timestamp": "2026-07-28T15:30:45.123Z",
  "notification_id": 42,
  "user_id": 7,
  "title": "Evaluación procesada",
  "message": "La evaluación EV-2026-01 ha sido procesada exitosamente",
  "notification_type": "success"
}
```

### ConnectionManager Compartido

El endpoint de notificaciones utiliza el `ConnectionManager` compartido definido en `api/core/websockets/connection_manager.py`, basado en canales de tipo string:

```python
class ConnectionManager:
    _channels: dict[str, set[WebSocket]]

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        async with self._lock:
            self._channels.setdefault(channel, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, channel: str):
        async with self._lock:
            if channel in self._channels:
                self._channels[channel].discard(websocket)
                if not self._channels[channel]:
                    del self._channels[channel]

    async def broadcast(self, channel: str, event: BaseWebSocketEvent):
        async with self._lock:
            connections = self._channels.get(channel, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(event.model_dump_json())
            except Exception:
                await self.disconnect(ws, channel)
```

El canal para notificaciones sigue el patrón `notifications:{user_id}`, lo que garantiza que cada usuario solo reciba sus propias notificaciones.

### WebSocket Endpoint

```python
@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(...)
):
    # 1. Autenticación via Firebase
    decoded = await verify_token(token)
    if not decoded:
        await websocket.close(code=4001)
        return

    # 2. Buscar usuario en DB por Firebase UID
    uid = decoded.get("user_id")
    user = users_repo.get_by_uid(uid)
    if not user:
        await websocket.close(code=4003)
        return

    # 3. Conectar al canal del usuario
    channel = f"notifications:{user.id}"
    await connection_manager.connect(websocket, channel)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, channel)
```

**Códigos de cierre:**

| Código | Significado                               |
| ------ | ----------------------------------------- |
| `4001` | Token Firebase inválido o expirado        |
| `4003` | Usuario no encontrado en la base de datos |

### Flujo de Creación y Broadcast

El `NotificationService` es el orquestador central. Cada vez que se crea una notificación:

```python
class NotificationService:
    async def create(self, data: NotificationCreate, actor_id: int | None = None):
        # 1. Persistir en DB
        notification = self.repository.create(data)

        # 2. Push en tiempo real por WebSocket
        await self._broadcast_notification(notification)

        # 3. Log de auditoría (opcional)
        if actor_id:
            await self.audit_service.log(...)

        return notification

    async def _broadcast_notification(self, notification):
        event = NotificationEvent(
            notification_id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.type,
        )
        channel = f"notifications:{notification.user_id}"

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.connection_manager.broadcast(channel, event))
        except RuntimeError:
            asyncio.run(self.connection_manager.broadcast(channel, event))
```

El patrón `asyncio.get_running_loop()` / `asyncio.run()` permite que el broadcast funcione tanto desde contextos asíncronos (endpoints REST) como síncronos (background tasks del evaluation processor).

### Endpoints REST

| Método | Ruta                             | Auth            | Descripción                                             |
| ------ | -------------------------------- | --------------- | ------------------------------------------------------- |
| `GET`  | `/notifications/me`              | Todos los roles | Listar notificaciones del usuario (paginado, filtrable) |
| `GET`  | `/notifications/me/unread-count` | Todos los roles | Cantidad de notificaciones no leídas                    |
| `POST` | `/notifications/`                | Admin, Director | Crear una notificación manual                           |
| `PUT`  | `/notifications/me/read`         | Todos los roles | Marcar notificaciones como leídas                       |
| `PUT`  | `/notifications/me/read-all`     | Todos los roles | Marcar todas como leídas                                |

### Eventos que Generan Notificaciones

| Trigger                                  | Función                           | Quién recibe                         |
| ---------------------------------------- | --------------------------------- | ------------------------------------ |
| `POST /notifications/` (manual)          | `NotificationService.create()`    | `user_id` especificado en el body    |
| Procesamiento de evaluación completado   | `_create_process_notification()`  | Uploader + Director del departamento |
| Procesamiento de evaluación fallido      | `_create_process_notification()`  | Uploader + Director del departamento |
| Análisis de IA de comentarios completado | `_create_analysis_notification()` | Uploader + Director del departamento |
| Análisis de IA de comentarios fallido    | `_create_analysis_notification()` | Uploader + Director del departamento |

> **Nota**: El `evaluation_processor` crea las notificaciones directamente en la DB (vía `NotificationModel`) y hace broadcast inline vía `notification_manager.broadcast()`, sin pasar por `NotificationService`. Esto significa que estas notificaciones automáticas no generan registros de auditoría.

## Consecuencias

### Positivas

- **Tiempo real**: Las notificaciones se entregan instantáneamente sin polling
- **Aislamiento por usuario**: El patrón de canales `notifications:{user_id}` garantiza que cada usuario solo reciba sus propias notificaciones
- **Coherencia arquitectónica**: Reutiliza el mismo `ConnectionManager` compartido y los mismos `BaseWebSocketEvent` que los endpoints de ADR-004 y ADR-005
- **Persistencia**: A diferencia de los dev logs y los logs de evaluación, las notificaciones se persisten en la base de datos, por lo que no se pierden si el cliente está desconectado
- **Protocolo uniforme**: Todos los eventos WebSocket siguen la misma estructura (`type` + `timestamp` + campos específicos), lo que simplifica el parsing en el frontend
- **Autenticación consistente**: Usa el mismo mecanismo de token Firebase por query param que los otros endpoints WS

### Negativas

- **Sin broker de mensajes**: Todo es en memoria (`asyncio.Queue` + sets de Python). Si el servidor se reinicia, las notificaciones se persisten en DB pero el push en tiempo real se pierde para los clientes conectados en ese instante
- **Un solo proceso**: El `ConnectionManager` mantiene las conexiones en memoria, por lo que no es posible escalar horizontalmente a múltiples workers/procesos sin un broker externo (Redis Pub/Sub, RabbitMQ)
- **El evaluation processor bypassa el service**: Las notificaciones automáticas se crean directamente contra el modelo, sin pasar por `NotificationService`, lo que significa que no se registra auditoría para estas
- **Sin protocolo client→server**: El servidor no interpreta los mensajes del cliente. No hay comandos como "suscribir a otro canal" o "marcar como leída" por WebSocket; esas operaciones requieren endpoints REST
- **Duplicación de ConnectionManager**: A pesar de existir un `ConnectionManager` compartido en `api/core/websockets/`, los endpoints de evaluaciones y dev logs mantienen sus propias instancias locales (ver nota en ADR-005)

### Riesgos mitigados

- **Memory leaks**: Las conexiones se limpian automáticamente en el `except WebSocketDisconnect` del endpoint
- **Conexiones zombi**: El `ConnectionManager.broadcast()` detecta envíos fallidos y elimina la conexión del canal
- **Token exposure**: El token Firebase se pasa por query param; HTTPS lo protege en tránsito
- **Notificaciones perdidas en reconexión**: El cliente puede hacer `GET /notifications/me/unread-count` al reconectar para verificar si hay notificaciones pendientes
- **Compatibilidad sync/async**: El patrón `get_running_loop()` / `asyncio.run()` garantiza que el broadcast funciona desde cualquier contexto

### Alternativas descartadas

| Alternativa                            | Razón de descarte                                                                                                                                    |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Polling HTTP**                       | Alta latencia, overhead de requests repetidos, mala UX                                                                                               |
| **Server-Sent Events**                 | Viable, pero WebSocket es coherente con los endpoints ya implementados (ADR-004, ADR-005)                                                            |
| **Redis Pub/Sub**                      | Añadiría una dependencia externa. Considerado y descartado para dev logs (ADR-004). Podría reconsiderarse si se necesita escalar a múltiples workers |
| **Cola de mensajes (RabbitMQ/Celery)** | Overkill para el caso de uso actual. Solo se justificaría con múltiples procesos o necesidad de retry garantizado                                    |

## Comparación con ADRs de WebSocket anteriores

| Aspecto               | Dev Logs (ADR-004)   | Evaluations (ADR-005)                    | Notifications (ADR-006)                 |
| --------------------- | -------------------- | ---------------------------------------- | --------------------------------------- |
| **Propósito**         | Monitoreo de sistema | Feedback de procesamiento                | Notificaciones de usuario               |
| **Endpoint**          | `/ws/devlogs`        | `/ws/evaluations/{id}`                   | `/ws/notifications`                     |
| **Autenticación**     | Solo `DEBUG`         | Token + roles + evaluación               | Token Firebase                          |
| **Canales**           | Single channel       | Por evaluación (`eval:{id}`)             | Por usuario (`notifications:{user_id}`) |
| **ConnectionManager** | Local (duplicado)    | Local (duplicado)                        | Compartido (`core/websockets/`)         |
| **Persistencia**      | No                   | No (solo logs)                           | Sí (tabla `notifications`)              |
| **Bidireccional**     | No                   | Preparado para sí                        | No (solo server→client)                 |
| **Protocolo**         | JSON plano           | `evaluation_log` / `evaluation_progress` | `notification`                          |
| **Reconexión**        | Pierde estado        | Pierde logs en curso                     | No pierde notificaciones (están en DB)  |

## Implementación

### Archivos clave

- `api/models/notification.py`: Modelo SQLAlchemy `NotificationModel`
- `api/schemas/notification.py`: Enums, DTOs de entrada/salida, filtros
- `api/repositories/notifications.py`: `NotificationsRepository` (CRUD + filtros + mark as read)
- `api/services/notification_service.py`: `NotificationService` (orquestador + broadcast)
- `api/controllers/notifications.py`: `NotificationsController` (delegación)
- `api/routes/notifications.py`: Endpoints REST
- `api/routes/ws_notifications.py`: WebSocket endpoint
- `api/core/websockets/connection_manager.py`: `ConnectionManager` compartido (singleton)
- `api/core/websockets/events.py`: `NotificationEvent` y `BaseWebSocketEvent`
- `api/dependencies/notifications.py`: Factory de inyección de dependencias
- `api/utils/evaluation_processor.py`: Genera notificaciones automáticas

### Autenticación WebSocket

```
Cliente                              Servidor
  │                                     │
  │── WS connect /ws/notifications ────→│
  │   ?token=<firebase_id_token>        │
  │                                     │── verify_token(token)
  │                                     │── firebase_admin.auth.verify_id_token()
  │                                     │── users_repo.get_by_uid(uid)
  │                                     │
  │←── WS accept (o close 4001/4003) ──│
  │                                     │
  │←── {"type":"notification",...} ────│ (cuando se crea una notificación)
  │                                     │
```

### Uso en el frontend

```typescript
interface NotificationEvent {
  type: "notification";
  notification_id: number;
  user_id: number;
  title: string;
  message: string;
  notification_type: "info" | "warning" | "error" | "success";
  timestamp: string;
}

const useNotificationWebSocket = () => {
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const token = getToken();
    const ws = new WebSocket(`${API_URL}/ws/notifications?token=${token}`);

    ws.onmessage = (event) => {
      const data: NotificationEvent = JSON.parse(event.data);
      if (data.type === "notification") {
        setUnreadCount((prev) => prev + 1);
      }
    };

    return () => ws.close();
  }, []);

  return { unreadCount };
};
```

## Referencias

- [ADR-001: Arquitectura por capas](./001-layered-architecture-fastapi-postgres.md)
- [ADR-004: WebSocket para Dev Logs](./004-websocket-dev-logs.md)
- [ADR-005: WebSocket para Evaluaciones](./005-websocket-evaluations.md)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Firebase ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [WebSocket Close Codes (RFC 6455)](https://www.rfc-editor.org/rfc/rfc6455#section-7.4.1)
