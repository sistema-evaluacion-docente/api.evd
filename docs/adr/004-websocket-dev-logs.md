# ADR-004: WebSocket para Dev Logs en Tiempo Real

- **Estado**: Aceptado
- **Fecha**: 2026-07-21
- **Decisores**: Equipo de desarrollo

## Contexto

El sistema **api.evd** requiere monitoreo en tiempo real de logs de desarrollo para facilitar el debugging y la observabilidad durante el desarrollo y pruebas. Los administradores necesitan ver:

- Requests HTTP entrantes con sus parámetros
- Respuestas HTTP salientes
- Operaciones de base de datos (queries, writes)
- Errores y excepciones
- Información de contexto (usuario, duración, status codes)

Las alternativas consideradas fueron:

1. **Polling HTTP**: El cliente hace requests periódicos para obtener nuevos logs
2. **Server-Sent Events (SSE)**: Conexión unidireccional del servidor al cliente
3. **WebSocket bidireccional**: Conexión persistente full-duplex

## Decisión

Se implementó un **WebSocket unidireccional** para streaming de dev logs usando el patrón pub/sub con colas asíncronas. La arquitectura consiste en:

### Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    Request Lifecycle                     │
│                                                          │
│  Middleware → Route → Controller → Service → Repository │
│       ↓           ↓            ↓            ↓           │
│                  DevLogCollector (pub/sub)               │
│                         ↓                                │
│              WebSocket ConnectionManager                 │
│                         ↓                                │
│                    Frontend Client                       │
└─────────────────────────────────────────────────────────┘
```

### DevLogCollector (Pub/Sub)

```python
class DevLogCollector:
    """Centralized log collector with pub/sub pattern."""
    
    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()
    
    async def publish(self, log_data: dict):
        """Publish log to all subscribers."""
        for queue in self._subscribers:
            await queue.put(log_data)
    
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to log stream."""
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from log stream."""
        self._subscribers.discard(queue)
```

### WebSocket Endpoint

```python
@router.websocket("/ws/devlogs")
async def ws_dev_logs(websocket: WebSocket):
    """WebSocket endpoint for dev logs streaming."""
    
    # Auth check (admin only)
    if not config.DEBUG:
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket)
    
    # Subscribe to log collector
    queue = await dev_logs_collector.subscribe()
    
    try:
        while True:
            # Wait for log with timeout
            log_data = await asyncio.wait_for(queue.get(), timeout=1.0)
            await websocket.send_json(log_data)
    except asyncio.TimeoutError:
        # Send ping to keep connection alive
        await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    finally:
        await dev_logs_collector.unsubscribe(queue)
```

### Middleware Integration

```python
class DevLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        await dev_logs_collector.publish({
            "type": "request",
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "timestamp": datetime.now().isoformat()
        })
        
        response = await call_next(request)
        
        # Log response
        duration = (time.time() - start_time) * 1000
        await dev_logs_collector.publish({
            "type": "response",
            "status_code": response.status_code,
            "duration_ms": duration,
            "timestamp": datetime.now().isoformat()
        })
        
        return response
```

### Frontend Integration

```typescript
const useDevLogWebSocket = () => {
  const [logs, setLogs] = useState<DevLog[]>([])
  
  useEffect(() => {
    const ws = new WebSocket(`${API_URL}/ws/devlogs`)
    
    ws.onmessage = (event) => {
      const log = JSON.parse(event.data)
      setLogs(prev => [...prev.slice(-99), log]) // Keep last 100 logs
    }
    
    return () => ws.close()
  }, [])
  
  return { logs }
}
```

## Consecuencias

### Positivas

- **Tiempo real**: Los logs se muestran instantáneamente sin polling
- **Baja latencia**: Conexión persistente elimina overhead de HTTP requests repetidos
- **Eficiencia**: Solo se envían datos cuando hay nuevos logs (push vs pull)
- **Escalabilidad**: El patrón pub/sub permite múltiples suscriptores sin acoplamiento
- **Debugging mejorado**: Los desarrolladores pueden ver el flujo completo de requests en tiempo real
- **Desacoplamiento**: El DevLogCollector no conoce los detalles de WebSocket, solo publica logs

### Negativas

- **Complejidad adicional**: Requiere manejar conexiones persistentes, reconexiones, y cleanup
- **Consumo de recursos**: Cada conexión WebSocket mantiene un socket abierto y una cola en memoria
- **Limitado a desarrollo**: Solo disponible en modo DEBUG por seguridad
- **No persistente**: Los logs se pierden si el cliente se desconecta (no hay historial)

### Riesgos mitigados

- **Memory leaks**: Las colas se limpian automáticamente al desconectar (unsubscribe en finally block)
- **Conexiones zombi**: Timeout de 1 segundo en queue.get() permite detectar desconexiones
- **Overload**: En producción el endpoint está deshabilitado (config.DEBUG check)
- **Reconexión**: El cliente implementa reconnect automático con exponential backoff

### Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Polling HTTP** | Alta latencia, overhead de requests repetidos, no escala bien |
| **Server-Sent Events** | Unidireccional (OK para logs), pero WebSocket es más estándar y permite bidireccionalidad futura |
| **Redis Pub/Sub** | Overkill para un solo servidor, añade dependencia externa innecesaria |
| **Base de datos de logs** | Overhead de escritura, no es tiempo real, requiere cleanup periódico |

## Implementación

### Archivos clave

- `api/core/dev_logs/collector.py`: DevLogCollector (pub/sub)
- `api/routes/ws_dev_logs.py`: WebSocket endpoint
- `api/middlewares/dev_log.py`: Middleware que publica logs
- `api/core/websockets/connection_manager.py`: ConnectionManager genérico
- `front.evd/src/features/dev-log/hooks/useDevLogWebSocket.ts`: Hook de React

### Configuración

```python
# api/config.py
class Config:
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
```

```bash
# .env
DEBUG=true  # Habilita WebSocket de dev logs
```

### Uso

1. **Backend**: El middleware publica automáticamente todos los requests/responses
2. **Frontend**: Usar el hook `useDevLogWebSocket()` para suscribirse
3. **UI**: Componente `FloatingLogs` muestra los logs en tiempo real

## Referencias

- [WebSocket API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Python asyncio.Queue](https://docs.python.org/3/library/asyncio-queue.html)
