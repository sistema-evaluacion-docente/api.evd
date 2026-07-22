# ADR-002: EnvelopeRouter para Response Envelope automatico

- **Estado**: Aceptado
- **Fecha**: 2026-07-18
- **Decisores**: Equipo de desarrollo

## Contexto

El proyecto **api.evd** requiere que todas las respuestas de la API sigan un formato estandar (envelope):

```json
{
  "status": "success",
  "data": <payload>,
  "pagination": { ... } | null,
  "error": { ... } | null,
  "timestamp": "<ISO 8601>"
}
```

Inicialmente, esta funcionalidad se implemento con `ResponseEnvelopeMiddleware` (`api/core/middleware.py`), que intercepta cada respuesta JSON y la envuelve en el envelope. Este enfoque funciona, pero tiene limitaciones:

1. **OpenAPI desactualizado**: El middleware opera en tiempo de ejecucion, por lo que los schemas generados automaticamente por FastAPI no reflejan la estructura real del envelope. El cliente ve `{ "id": 1, "name": "..." }` en la documentacion, pero recibe `{ "status": "success", "data": { ... }, ... }`.
2. **Sin type-checking de respuesta**: Al envolver la respuesta fuera del pipeline de validacion de FastAPI, no hay garantia en tiempo de desarrollo de que el `response_model` declarado coincida con lo que realmente se devuelve.
3. **Exclusiones manuales**: El middleware requiere mantener listas de paths excluidos (`/docs`, `/openapi.json`, `/uploads`) y logica condicional para respuestas no-JSON o de error.
4. **Dificil de testear a nivel de ruta**: No es posible indicar por-endpoint si una ruta debe o no llevar envelope sin agregar headers o convenciones ad-hoc.

Se necesitaba un mecanismo que:

- Mantenga el `response_model` de FastAPI alineado con la estructura real del envelope.
- Genere documentacion OpenAPI correcta automaticamente.
- Permita opt-out por-endpoint.
- Conviva con el middleware existente para errores y casos especiales.

## Decision

Se creo un `EnvelopeRouter` personalizado (`api/core/router.py`) compuesto por dos clases:

### `EnvelopeAPIRoute(APIRoute)`

Sobrescribe `get_route_handler()` para pasar `response_field=None` al handler de FastAPI. Esto **desactiva la validacion de respuesta** en tiempo de ejecucion, pero **mantiene el `response_model`** para que OpenAPI genere la documentacion correcta.

```python
class EnvelopeAPIRoute(APIRoute):
    def get_route_handler(self):
        return get_request_handler(
            ...
            response_field=None,  # skip response validation
            ...
        )
```

### `EnvelopeRouter(APIRouter)`

Sobrescribe `add_api_route()` para envolver automaticamente el `response_model` en `ResponseEnvelope[T]` cuando `envelope=True` (valor por defecto).

```python
class EnvelopeRouter(APIRouter):
    def add_api_route(self, path, endpoint, *, response_model=None, envelope=True, **kwargs):
        if envelope and response_model is not None:
            response_model = ResponseEnvelope[response_model]
        super().add_api_route(path, endpoint, response_model=response_model, **kwargs)
```

### Uso en rutas

Todos los modulos de rutas usan `EnvelopeRouter` en lugar de `APIRouter`:

```python
from api.core.router import EnvelopeRouter

router = EnvelopeRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=UserOut)  # OpenAPI muestra ResponseEnvelope[UserOut]
async def list_users(...):
    ...
```

### Opt-out por endpoint

Se puede desactivar el envelope para un endpoint especifico:

```python
@router.get("/health", response_model=HealthResponseSchema, envelope=False)
async def health_check():
    ...
```

## Consecuencias

### Positivas

- **OpenAPI preciso**: La documentacion generada refleja la estructura real del envelope (`status`, `data`, `pagination`, `error`, `timestamp`), mejorando la experiencia del cliente.
- **Type safety**: El `response_model` envuelto en `ResponseEnvelope[T]` permite que FastAPI valide y documente correctamente la forma de la respuesta.
- **Opt-out explicito**: El parametro `envelope=False` permite excluir endpoints individuales sin depender de listas de paths en el middleware.
- **Compatibilidad con el middleware**: El `EnvelopeRouter` complementa al `ResponseEnvelopeMiddleware` existente. El middleware sigue siendo util para envolver respuestas de error (status >= 400) y casos donde no hay `response_model` declarado.
- **Cero overhead en runtime**: Al pasar `response_field=None`, se evita la serializacion doble (FastAPI no serializa la respuesta dos veces).

### Negativas

- **Router personalizado**: Los desarrolladores deben usar `EnvelopeRouter` en lugar de `APIRouter`. Importar `APIRouter` directamente romperia el contrato del envelope a nivel de OpenAPI.
- **Dualidad middleware + router**: Existen dos mecanismos de envelope (middleware y router) que operan en capas distintas. Esto puede causar confusion sobre cual es responsable de que.
- **Response validation desactivado**: Al pasar `response_field=None`, FastAPI no valida que la respuesta del endpoint coincida con el `response_model` declarado. La validacion queda en manos del developer y los tests.

### Riesgos mitigados

- La convencion de usar `EnvelopeRouter` esta establecida en todos los modulos de rutas existentes (`users`, `teachers`, `academic_periods`), lo que reduce el riesgo de inconsistencia.
- El middleware sigue cubriendo los casos de error y las respuestas sin `response_model`, evitando huecos en el formato del envelope.
