# Checklist de cobertura por módulo

Antes de dar por completa la suite de tests de un módulo (ej. Users, Orders),
verifica lo siguiente.

## Service

- [ ] Caso feliz (crear/obtener/actualizar/eliminar con datos válidos)
- [ ] Cada excepción de negocio custom tiene su propio test (una por caso,
      no un solo test genérico de "errores")
- [ ] Se verifica que el repository fue llamado con los argumentos correctos
      (`assert_called_once_with`), no solo que el resultado sea el esperado
- [ ] Transformaciones de datos antes de guardar (hashing, normalización,
      defaults) están cubiertas
- [ ] El repository jamás se instancia real dentro de estos tests — siempre mock

## Repository

- [ ] CRUD básico contra DB real de test
- [ ] Constraints de base de datos (unique, not null, foreign key) lanzan el
      error esperado
- [ ] Caso de "no encontrado" (get de un ID inexistente devuelve None, no excepción)
- [ ] Cada query compleja (join, agregación) tiene al menos un test que
      verifica el resultado con datos sembrados (seed) conocidos
- [ ] Si hay paginación (`skip`/`limit`), está testeada con datos suficientes
      para verificar el corte

## Endpoint / API

- [ ] Status code de éxito (200/201/204 según corresponda)
- [ ] Status code de validación fallida (422) con payload inválido
- [ ] Cada excepción de negocio del service se traduce al status code HTTP
      correcto (409, 404, 403, etc.)
- [ ] El `response_model` no expone campos que no debería (ej. `hashed_password`
      nunca debe aparecer en la respuesta de un endpoint de User)
- [ ] El service está mockeado vía `app.dependency_overrides` — el endpoint
      no debe tocar una base de datos real en estos tests

## General

- [ ] Cada archivo de test corresponde 1:1 a un archivo de origen
- [ ] Nombres de test siguen `test_<método>_<escenario>_<resultado>`
- [ ] No hay tests que dependan del orden de ejecución de otros tests
- [ ] `pytest tests/ -v` corre sin warnings de fixtures no usadas o mal configuradas
- [ ] Si se agregó un módulo nuevo, se actualizó `conftest.py` solo si la
      fixture es realmente reutilizable — fixtures de un solo uso van en el
      propio archivo de test, no en conftest
