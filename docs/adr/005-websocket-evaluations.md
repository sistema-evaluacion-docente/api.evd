# ADR-005: WebSocket para Evaluaciones con Logs Detallados

- **Estado**: Aceptado
- **Fecha**: 2026-07-21
- **Decisores**: Equipo de desarrollo

## Contexto

El sistema **api.evd** procesa evaluaciones docentes desde archivos PDF en background tasks. Este proceso puede tardar varios minutos dependiendo del número de docentes y comentarios. Los usuarios necesitan:

- **Feedback en tiempo real** del progreso del procesamiento
- **Logs detallados** de cada acción (docente creado, materia creada, notas creadas, etc.)
- **Notificaciones** cuando el procesamiento se completa o falla
- **Visibilidad** del análisis de IA de comentarios (progreso y resultados)

El problema específico es que el procesamiento de evaluaciones involucra:

1. Parsing del PDF (extracción de datos de docentes, materias, notas, comentarios)
2. Creación/actualización de usuarios, docentes, materias, grupos académicos
3. Inserción de evaluation_scores y evaluation_question_scores
4. Inserción de comentarios
5. Análisis de IA de todos los comentarios (clasificación de riesgo y categoría pedagógica)

Sin WebSocket, el usuario tendría que hacer polling para saber el estado, lo cual es ineficiente y no proporciona feedback granular del progreso.

## Decisión

Se implementó un **WebSocket bidireccional con autenticación y autorización** que envía logs detallados del procesamiento de evaluaciones. La arquitectura consiste en:

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation Processing                     │
│                                                              │
│  Upload PDF → Background Task → process_evaluation()        │
│                                      ↓                       │
│                          _broadcast_log() (por cada acción) │
│                                      ↓                       │
│                          ConnectionManager (channels)       │
│                                      ↓                       │
│                          WebSocket /ws/evaluations/{id}     │
│                                      ↓                       │
│                          Frontend (FloatingLogs component)  │
└─────────────────────────────────────────────────────────────┘
```

### ConnectionManager con Channels

```python
class ConnectionManager:
    """Manages WebSocket connections with channel-based isolation."""
    
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, evaluation_id: int):
        """Connect to a specific evaluation channel."""
        await websocket.accept()
        if evaluation_id not in self.active_connections:
            self.active_connections[evaluation_id] = []
        self.active_connections[evaluation_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, evaluation_id: int):
        """Disconnect from evaluation channel."""
        if evaluation_id in self.active_connections:
            self.active_connections[evaluation_id].remove(websocket)
            if not self.active_connections[evaluation_id]:
                del self.active_connections[evaluation_id]
    
    async def broadcast(self, evaluation_id: int, event: dict):
        """Broadcast event to all connections in evaluation channel."""
        if evaluation_id in self.active_connections:
            for connection in self.active_connections[evaluation_id]:
                try:
                    await connection.send_json(event)
                except Exception:
                    # Connection closed, will be cleaned up on disconnect
                    pass
```

### WebSocket Endpoint con Auth

```python
@router.websocket("/ws/evaluations/{evaluation_id}")
async def ws_evaluation(
    websocket: WebSocket,
    evaluation_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for evaluation processing logs."""
    
    # 1. Authenticate user
    user = await authenticate_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    
    # 2. Check permissions (ADMIN or DIRECTOR)
    if not has_evaluation_access(user):
        await websocket.close(code=4003)
        return
    
    # 3. Check evaluation exists and user has access
    evaluation = await get_evaluation(evaluation_id)
    if not evaluation or not user_can_access_evaluation(user, evaluation):
        await websocket.close(code=4004)
        return
    
    # 4. Connect to channel
    await manager.connect(websocket, evaluation_id)
    
    try:
        # 5. Send initial state
        await websocket.send_json({
            "type": "evaluation_log",
            "level": "info",
            "message": "Conectado al procesamiento de evaluación",
            "timestamp": datetime.now().isoformat()
        })
        
        # 6. Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed (ping/pong, etc.)
    except WebSocketDisconnect:
        manager.disconnect(websocket, evaluation_id)
```

### Broadcast de Logs Detallados

```python
def _broadcast_log(
    evaluation_id: int,
    level: str,  # "info", "success", "warning", "error"
    message: str,
    teacher_name: str | None = None,
    teacher_code: str | None = None,
    course_name: str | None = None,
    course_code: str | None = None
):
    """Broadcast detailed log to evaluation channel."""
    event = {
        "type": "evaluation_log",
        "level": level,
        "message": message,
        "teacher_name": teacher_name,
        "teacher_code": teacher_code,
        "course_name": course_name,
        "course_code": course_code,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        asyncio.create_task(
            connection_manager.broadcast(evaluation_id, event)
        )
    except RuntimeError:
        # No event loop running (e.g., in tests)
        pass
```

### Uso en process_evaluation()

```python
def process_evaluation(evaluation_id: int, parsed_data: dict):
    """Process evaluation PDF and broadcast detailed logs."""
    
    _broadcast_log(
        evaluation_id,
        "info",
        "Iniciando procesamiento de evaluación"
    )
    
    for teacher_data in parsed_data["teachers"]:
        # Create user
        user = create_user(teacher_data)
        _broadcast_log(
            evaluation_id,
            "success",
            f"Usuario creado: {user.name}",
            teacher_name=user.name,
            teacher_code=user.institutional_code
        )
        
        # Create teacher
        teacher = create_teacher(user.id, teacher_data)
        _broadcast_log(
            evaluation_id,
            "success",
            f"Docente registrado: {teacher.name}",
            teacher_name=teacher.name,
            teacher_code=teacher.institutional_code
        )
        
        for course_data in teacher_data["courses"]:
            # Create course
            course = create_course(course_data)
            _broadcast_log(
                evaluation_id,
                "info",
                f"Materia creada: {course.name}",
                course_name=course.name,
                course_code=course.code
            )
            
            # Create academic group and scores
            create_academic_group_and_scores(teacher.id, course.id, course_data)
            _broadcast_log(
                evaluation_id,
                "success",
                f"Notas creadas para {teacher.name} en {course.name}",
                teacher_name=teacher.name,
                course_name=course.name
            )
    
    _broadcast_log(
        evaluation_id,
        "success",
        f"Procesamiento completado: {len(parsed_data['teachers'])} docentes procesados"
    )
```

### Frontend Integration

```typescript
interface EvaluationLogEvent {
  type: 'evaluation_log'
  evaluation_id: number
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  teacher_name?: string
  teacher_code?: string
  course_name?: string
  course_code?: string
  timestamp: string
}

const useEvaluationWebSocket = (evaluationId: number | null) => {
  const [logs, setLogs] = useState<EvaluationLogEvent[]>([])
  const [lastEvent, setLastEvent] = useState<EvaluationProgressEvent | null>(null)
  
  useEffect(() => {
    if (!evaluationId) return
    
    const token = getToken()
    const ws = new WebSocket(
      `${API_URL}/ws/evaluations/${evaluationId}?token=${token}`
    )
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'evaluation_log') {
        setLogs(prev => [...prev, data])
      } else if (data.type === 'evaluation_progress') {
        setLastEvent(data)
      }
    }
    
    return () => ws.close()
  }, [evaluationId])
  
  return { logs, lastEvent, clearLogs: () => setLogs([]) }
}
```

## Consecuencias

### Positivas

- **Feedback granular**: El usuario ve cada acción del procesamiento en tiempo real
- **Transparencia**: Se muestra exactamente qué se está creando/actualizando
- **Mejor UX**: No hay incertidumbre sobre el progreso del procesamiento
- **Debugging**: Los logs detallados facilitan identificar problemas en el procesamiento
- **Contexto rico**: Cada log incluye información relevante (docente, materia, código)
- **Aislamiento por evaluación**: Cada evaluación tiene su propio canal, sin interferencias
- **Autenticación y autorización**: Solo usuarios con permisos pueden ver los logs

### Negativas

- **Complejidad de autenticación**: WebSocket no soporta headers HTTP, requiere token en query param
- **Gestión de conexiones**: Cada evaluación activa mantiene conexiones abiertas
- **Broadcast overhead**: Cada log genera un broadcast a todos los suscriptores del canal
- **No persistente**: Los logs se pierden si el cliente se desconecta y reconecta
- **Duplicación de ConnectionManager**: Se creó un ConnectionManager específico para evaluaciones (no reutiliza el de dev logs)

### Riesgos mitigados

- **Memory leaks**: Las conexiones se limpian automáticamente en el finally block
- **Conexiones zombi**: WebSocketDetect exception maneja desconexiones inesperadas
- **Unauthorized access**: Triple verificación (token, permisos, acceso a evaluación específica)
- **Error handling**: Los errores de broadcast se capturan y registran sin romper el procesamiento
- **Token exposure**: El token se pasa por query param (HTTPS lo protege en tránsito)

### Diferencias con ADR-004 (Dev Logs)

| Aspecto | Dev Logs (ADR-004) | Evaluations (ADR-005) |
|---------|-------------------|----------------------|
| **Propósito** | Monitoreo de sistema | Feedback de procesamiento |
| **Autenticación** | Solo DEBUG mode | Token + permisos |
| **Canales** | Single channel | Multi-channel (por evaluación) |
| **Contenido** | Requests/responses/DB ops | Logs de negocio detallados |
| **ConnectionManager** | Global | Por evaluación |
| **Persistencia** | No | No |
| **Bidireccional** | No (solo server→client) | Sí (preparado para client→server) |

## Implementación

### Archivos clave

- `api/routes/ws_evaluations.py`: WebSocket endpoint y ConnectionManager
- `api/utils/evaluation_processor.py`: process_evaluation() con broadcasts
- `api/core/websockets/events.py`: EvaluationProgressEvent y EvaluationLogEvent
- `front.evd/src/features/evaluations/hooks/useEvaluationWebSocket.ts`: Hook de React
- `front.evd/src/features/evaluations/components/FloatingLogs.tsx`: UI de logs

### Estructura de logs

```typescript
{
  type: "evaluation_log",
  level: "success",
  message: "Docente registrado: Juan Pérez",
  teacher_name: "Juan Pérez",
  teacher_code: "12345",
  course_name: null,
  course_code: null,
  timestamp: "2026-07-21T15:30:45.123Z"
}
```

### Niveles de log

| Nivel | Uso | Color en UI |
|-------|-----|-------------|
| `info` | Acciones informativas (inicio, progreso) | Azul |
| `success` | Acciones completadas exitosamente | Verde |
| `warning` | Advertencias no críticas | Amarillo |
| `error` | Errores que no detienen el procesamiento | Rojo |

### Ejemplos de logs generados

```
[info] Iniciando procesamiento de evaluación
[success] Usuario creado: Juan Pérez (12345)
[success] Docente registrado: Juan Pérez (12345)
[info] Materia creada: Estructuras de Datos (MATH101)
[success] Notas creadas para Juan Pérez en Estructuras de Datos
[success] Procesamiento completado: 15 docentes procesados
[info] Iniciando análisis de IA de comentarios
[info] Analizando comentario 1/45...
[success] Comentario clasificado: Riesgo bajo, Categoría: Dominio del tema
[success] Análisis completado: 45 comentarios procesados
```

## Referencias

- [ADR-004: WebSocket para Dev Logs](./004-websocket-dev-logs.md)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Authentication Best Practices](https://www.rfc-editor.org/rfc/rfc6455)
- [Background Tasks in FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/)
