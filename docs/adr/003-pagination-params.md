# ADR-003: Paginacion generica con `PaginationParams` y `PaginationDep`

- **Estado**: Aceptado
- **Fecha**: 2026-07-18
- **Decisores**: Equipo de desarrollo

## Contexto

El proyecto **api.evd** expone multiples endpoints de lista (docentes, evaluaciones, periodos academicos, usuarios, etc.) que requieren paginacion. Se necesitaba un mecanismo que:

- Fuera reutilizable en todos los endpoints de lista sin duplicar logica.
- Se integrara con el sistema de inyeccion de dependencias de FastAPI.
- Validara automaticamente los parametros de entrada (page >= 1, 1 <= limit <= 100).
- Proveyera un calculo estandar del offset para las queries SQLAlchemy.
- Conviviera con el `ResponseEnvelope` y el `Page[T]` schema generico.

## Decision

Se creo el modulo `api/core/pagination.py` compuesto por tres elementos:

### `PaginationParams` (dataclass)

Dataclass que encapsula los parametros de paginacion:

```python
@dataclass
class PaginationParams:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
```

La propiedad `offset` calcula el desplazamiento para queries SQL (`OFFSET (page - 1) * limit`), evitando que cada repository repita esta logica.

### `pagination_params` (dependencia FastAPI)

Funcion que extrae y valida los parametros de paginacion desde query parameters:

```python
def pagination_params(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit)
```

FastAPI genera automaticamente la documentacion OpenAPI para estos query parameters (`page`, `limit`) con sus restricciones de validacion.

### `PaginationDep` (type alias)

Type alias para inyectar la dependencia en endpoints con una sola linea:

```python
PaginationDep = Annotated[PaginationParams, Depends(pagination_params)]
```

### Uso en endpoints

```python
from api.core.pagination import PaginationDep

@router.get("/", response_model=TeacherOut)
async def list_teachers(pagination: PaginationDep):
    # pagination.page, pagination.limit, pagination.offset disponibles
    ...
```

## Consecuencias

### Positivas

- **Reutilizacion**: Un solo modulo de paginacion para todos los endpoints de lista. Nuevos endpoints solo necesitan importar `PaginationDep`.
- **Validacion automatica**: FastAPI valida `page >= 1` y `1 <= limit <= 100` antes de que el endpoint reciba los parametros, rechazando requests invalidos con 422.
- **OpenAPI preciso**: Los query parameters `page` y `limit` aparecen documentados automaticamente en Swagger/ReDoc con sus restricciones.
- **Calculo estandar del offset**: La propiedad `offset` en `PaginationParams` centraliza la logica `(page - 1) * limit`, evitando errores de calculo en repositories.
- **Testabilidad**: `PaginationParams` es una dataclass pura, facil de instanciar en tests sin depender de FastAPI.

### Negativas

- **Limite hardcodeado**: El limite maximo de 100 esta definido en `pagination_params`. Cambiarlo requiere modificar el modulo core (aunque es una decision intencional para evitar queries masivas).
- **Sin cursor-based pagination**: La implementacion usa offset-based pagination, que puede tener problemas de performance en tablas muy grandes con offsets altos. Para el volumen actual del proyecto esto no es un problema.
- **Acoplamiento implicito**: Los endpoints que usan `PaginationDep` deben conocer la estructura de `PaginationParams` (page, limit, offset), aunque esto se mitigaa con type hints.

### Riesgos mitigados

- La validacion de FastAPI (`ge=1`, `le=100`) previene valores invalidos antes de que lleguen al repository, evitando queries con offsets negativos o limites excesivos.
- El uso de `Annotated` + `Depends` sigue la convencion idiomatica de FastAPI, facilitando que nuevos desarrolladores entiendan el patron.
- La dataclass `PaginationParams` es inmutable en la practica (se crea una nueva instancia por request), evitando efectos secundarios.
