# Casos de uso — Sistema de Evaluación Docente (SET)

Diagramas de casos de uso en PlantUML del aplicativo, derivados de:

- **Tabla 36** del documento de tesis — actores del sistema y su ámbito de actuación.
- **Tabla 37** — los requisitos funcionales `RF-1.1` … `RF-8.2`.
- **Tabla 35** — la delimitación del alcance (`FA-1` … `FA-5`).
- La implementación de `DistilUmbert-back` (FastAPI) y `DistilUmbert-front` (React).

Los diagramas se organizan **por actor y área funcional**: cada uno tiene un solo actor y entre 4 y
10 casos de uso, de modo que quepa legible en una página. Un caso que dos roles comparten se
modela una vez para cada uno, con su propio código.

## Índice de diagramas

| Archivo | Actor | Área | Casos |
| --- | --- | --- | --- |
| `00-contexto.puml` | todos | Vista de contexto | 9 |
| `10-visitante-y-sesion.puml` | Visitante · Usuario autenticado | Acceso, sesión y notificaciones | 7 |
| `20-admin-estructura-institucional.puml` | Administrador | Estructura institucional | 8 |
| `21-admin-usuarios-auditoria-configuracion.puml` | Administrador | Usuarios, auditoría y configuración | 7 |
| `30-director-docentes-y-oferta.puml` | Director | Docentes y oferta académica | 7 |
| `31-director-carga-de-evaluaciones.puml` | Director | Carga y procesamiento | 6 |
| `32-director-consulta-de-evaluaciones.puml` | Director | Consulta y descarga | 6 |
| `33-director-comentarios-y-alertas.puml` | Director | Comentarios y alertas | 4 |
| `34-director-reportes-del-departamento.puml` | Director | Reportes del departamento | 5 |
| `35-director-reportes-del-docente.puml` | Director | Reportes del docente | 6 |
| `36-director-planes-ciclo-de-vida.puml` | Director | Planes: ciclo de vida | 8 |
| `37-director-planes-formatos.puml` | Director | Planes: formatos oficiales | 8 |
| `38-director-planes-evidencias.puml` | Director | Planes: evidencias | 6 |
| `39-director-configuracion-departamental.puml` | Director | Configuración departamental | 4 |
| `40-docente-mis-resultados.puml` | Docente | Resultados propios | 7 |
| `41-docente-mis-planes.puml` | Docente | Planes propios | 8 |
| `50-sistema-procesamiento-y-analisis.puml` | Sistema | Procesamiento del PDF y análisis con IA | 10 |
| `51-sistema-verificacion-de-planes.puml` | Sistema | Verificación automática | 10 |
| `52-sistema-ciclo-de-planes.puml` | Sistema | Reglas del ciclo del plan | 8 |
| `53-sistema-avisos-y-correo.puml` | Sistema | Notificaciones y correo | 5 |
| `54-sistema-seguridad-y-auditoria.puml` | Sistema | Seguridad, ámbito y auditoría | 9 |

## Actores

| Actor | Ámbito (Tabla 36) |
| --- | --- |
| Visitante | Página pública de presentación y pantalla de ingreso. |
| Administrador | Estructura institucional, configuraciones institucionales y auditoría. **Excluido de los datos internos de un departamento.** |
| Director de Departamento | Todo lo relativo a su propio departamento. |
| Docente | Únicamente sus propios resultados y sus propios planes. |
| Sistema | Procesamiento en segundo plano, análisis de IA, verificación de planes, notificaciones y correo. |

`Visitante` es la generalización de `Usuario autenticado`, y de este derivan los tres roles
autenticados. Un mismo usuario puede acumular varios roles y elige con cuál opera (`RF-1.2`).
`Firebase Auth` y el `Servidor de correo (SMTP)` son sistemas externos, coherentes con `FA-2`.

## Notación

Vale para los 21 diagramas; se enuncia aquí una sola vez en lugar de repetirla en cada figura.

- Cada caso de uso lleva bajo su nombre, en gris, el **requisito funcional de la Tabla 37 que lo
  origina**.
- Un caso de uso **sin requisito debajo** corresponde a funcionalidad que el aplicativo expone pero
  que la Tabla 37 no recoge. No es un olvido del diagrama: se listan todos en
  «[Casos de uso sin requisito en la Tabla 37](#casos-de-uso-sin-requisito-en-la-tabla-37)», y su
  procedencia real —Tabla 36, Tabla 35 o el grupo de requisitos al que pertenecen— consta en la
  columna «RF» de la especificación.
- Los óvalos **amarillos** corresponden al actor `Sistema`: procesos que se ejecutan sin
  intervención humana.
- Tres casos de uso son **transversales a todo el sistema** y no se dibujan en los demás diagramas:
  `CU-SIS-35` (autorización por rol), `CU-SIS-37` (confinamiento al ámbito) y `CU-SIS-42`
  (auditoría de cada mutación). Toda petición pasa por los dos primeros y toda mutación queda
  registrada por el tercero. Dibujar un `include` desde cada caso de uso los volvía ilegibles.
- Solo se conservan las relaciones `include`/`extend` que describen una inclusión o una extensión
  real. Las precondiciones (p. ej. el acta debe estar completa para cerrarla) se documentan en la
  columna «Detalle» de la especificación, no como relación.

---

# Especificación de los casos de uso

La columna «Detalle» recoge las operaciones que el caso agrupa y las reglas de negocio que antes
figuraban como notas dentro de los diagramas.

## Visitante y sesión

| Código | Caso de uso | RF | Detalle |
| --- | --- | --- | --- |
| CU-VIS-01 | Consultar la página pública de presentación | Tabla 36 | Ruta `/`, única accesible sin autenticar junto con la pantalla de ingreso. |
| CU-VIS-02 | Iniciar sesión con correo y contraseña o con cuenta de Google | RF-1.1 | La identidad y las contraseñas residen en Firebase Auth (`FA-2`). El sistema valida el token y lo vincula con las tablas locales `users` y `user_roles`. |
| CU-USR-01 | Seleccionar el rol con el que se opera | RF-1.2 | Extiende el inicio de sesión cuando la cuenta acumula varios roles. La selección se persiste en el navegador. |
| CU-USR-02 | Cerrar sesión | — | |
| CU-USR-03 | Consultar y actualizar el perfil propio | — | |
| CU-USR-04 | Gestionar las notificaciones propias | RF-7.1 | Agrupa: consultar el listado paginado, consultar el conteo de no leídas, marcar una notificación como leída y marcarlas todas. |
| CU-USR-05 | Recibir las notificaciones en tiempo real y abrir el plan enlazado | — | Canal WebSocket `/ws/notifications`. El campo `link` de la notificación lleva al plan correspondiente. |

## Administrador

| Código | Caso de uso | RF | Detalle |
| --- | --- | --- | --- |
| CU-ADM-01 | Gestionar facultades | RF-2.1 | Crear, consultar, actualizar y eliminar. |
| CU-ADM-02 | Gestionar departamentos | RF-2.2 | Crear, consultar, actualizar y eliminar. |
| CU-ADM-03 | Asignar o retirar el director de un departamento | RF-2.2 · RF-2.6 | |
| CU-ADM-04 | Gestionar programas académicos | RF-2.3 | |
| CU-ADM-05 | Gestionar el catálogo de directores | RF-2.6 | |
| CU-ADM-06 | Gestionar periodos académicos | — | |
| CU-ADM-07 | Activar o cerrar un periodo académico | — | Extiende la gestión de periodos. |
| CU-ADM-08 | Gestionar cursos y grupos académicos | RF-2.4 | `RF-2.4` nombra a Admin y Director; el director gestiona los grupos de su departamento en `CU-DIR-06`. |
| CU-ADM-09 | Gestionar usuarios, sus roles y su estado | RF-1.3 | Agrupa: crear un usuario, consultar el listado paginado, reemplazar sus roles y activarlo o desactivarlo. |
| CU-ADM-10 | Consultar el historial de auditoría | RF-8.2 | Listado paginado y consulta de un evento por identificador. |
| CU-ADM-11 | Seguir los eventos de la base de datos en modo depuración | — | Canal `/ws/devlogs`, disponible solo con `DEBUG=true`. |
| CU-ADM-12 | Gestionar las configuraciones institucionales | Tabla 36 | Agrupa consultar, consultar por clave, crear, actualizar y eliminar. El administrador solo ve y administra las institucionales: lo que cada departamento configure es asunto de su director. |
| CU-ADM-13 | Consultar el historial de cambios de una configuración | — | `settings_history` lleva el mismo `department_id`, de modo que los historiales no se mezclan. |
| CU-ADM-14 | Fijar el umbral institucional que dispara el plan | RF-6.1 | `improvement_plan.score_threshold` es una clave institucional: existe una sola fila, la global, y quien la consume la lee sin departamento. |
| CU-ADM-15 | Reabrir el acta cerrada de un plan | RF-6.8 | Excepción explícita al ámbito de la Tabla 36: es una acción de gobierno, no una consulta de datos departamentales. Solo un administrador puede reabrir un acta. |

## Director de Departamento

| Código | Caso de uso | RF | Detalle |
| --- | --- | --- | --- |
| CU-DIR-01 | Gestionar los docentes de su departamento | — | |
| CU-DIR-02 | Crear un docente junto con su usuario de acceso | — | |
| CU-DIR-03 | Cargar docentes de forma masiva desde un archivo Excel | FA-3 | La entrada de datos del sistema son el PDF oficial y las cargas por Excel; no hay integración por API con los sistemas académicos. |
| CU-DIR-04 | Consultar los docentes con sus promedios | — | Admite filtrar por modalidad del grupo. |
| CU-DIR-05 | Renombrar una materia conservando su código | RF-2.5 | El código se conserva para no romper el histórico ni las comparaciones entre periodos. |
| CU-DIR-06 | Gestionar los grupos académicos y su modalidad | RF-2.4 | La modalidad (presencial o a distancia) se obtiene del título del PDF durante la carga y se persiste en el grupo. |
| CU-DIR-07 | Consultar los periodos disponibles | — | |
| CU-DIR-08 | Cargar los PDF oficiales de evaluación del periodo | RF-3.1 · RF-3.2 | El campo del formulario acepta uno o dos PDF: el de programas presenciales y el de programas a distancia. Ambos quedan bajo una sola evaluación. |
| CU-DIR-09 | Seguir el progreso del procesamiento en tiempo real | RF-3.4 | Canal `/ws/evaluations/{id}`. La evaluación transita por `PROCESSING → COMPLETED`, o `FAILED`. |
| CU-DIR-10 | Reprocesar el análisis de IA de una evaluación | — | |
| CU-DIR-11 | Activar o desactivar una evaluación | — | |
| CU-DIR-12 | Eliminar una evaluación y sus datos derivados | — | Arrastra puntajes, comentarios y datos asociados. |
| CU-DIR-13 | Consultar el catálogo de las 22 preguntas | — | Las 22 preguntas se agrupan en 4 dimensiones. |
| CU-DIR-14 | Consultar las evaluaciones por identificador, periodo y listado | RF-3.5 | |
| CU-DIR-15 | Consultar el resumen y los promedios por dimensión | RF-3.5 | |
| CU-DIR-16 | Consultar el detalle por dimensión | RF-3.5 | |
| CU-DIR-17 | Descargar el PDF original de la evaluación | RF-3.6 | El directorio de cargas no se publica como contenido estático: los archivos salen solo por endpoints con verificación de permisos (`CU-SIS-38`). |
| CU-DIR-18 | Descargar el reporte PDF de un docente | RF-3.6 · RF-5.9 | Solo las páginas del docente dentro del PDF de la evaluación. |
| CU-DIR-19 | Exportar a Excel el resumen de la evaluación | — | |
| CU-DIR-20 | Consultar y filtrar los comentarios | RF-4.2 | Agrupa el listado filtrado y paginado y la consulta de un comentario por identificador. |
| CU-DIR-21 | Contar los comentarios por departamento y por docente | RF-4.2 | |
| CU-DIR-22 | Consultar las alertas de riesgo alto de un docente | RF-4.4 | Es una consulta filtrada de `CU-DIR-20`. |
| CU-DIR-23 | Corregir la clasificación de riesgo y de categoría de un comentario | RF-4.3 | Las salidas automáticas son insumo para la decisión humana y nunca un veredicto: la corrección manual forma parte del diseño. Dispara la re-verificación de los planes que citaban ese comentario (`CU-SIS-19`). |
| CU-DIR-24 | Consultar el panel de resumen | — | |
| CU-DIR-25 | Consultar los promedios del departamento y compararlos con el periodo anterior | RF-5.1 | |
| CU-DIR-26 | Generar el reporte del departamento por rango de periodos | RF-5.2 | Agrupa el reporte general y el reporte por materias. |
| CU-DIR-27 | Consultar el ranking de desempeño y la distribución de calificaciones | RF-5.6 | Ranking paginado y ordenable. |
| CU-DIR-28 | Listar las materias y comparar a los docentes que dictan la misma | RF-5.7 | |
| CU-DIR-29 | Consultar el historial del docente en los periodos evaluados | RF-5.3 | |
| CU-DIR-30 | Comparar al docente con el periodo anterior y con su departamento | RF-5.3 | |
| CU-DIR-31 | Consultar los promedios por dimensión y la matriz del docente | RF-5.4 | |
| CU-DIR-32 | Consultar los cursos del docente y sus comentarios por materia | RF-5.5 | Agrupa el listado de cursos por periodo, la agrupación de comentarios por materia y el historial en una materia concreta. |
| CU-DIR-33 | Comparar el desempeño de un docente entre dos periodos | RF-5.8 | |
| CU-DIR-34 | Descargar el reporte de evaluación del docente en Excel | RF-5.9 | Opcionalmente incluye los comentarios agrupados por materia. |
| CU-DIR-35 | Consultar los docentes en riesgo y los candidatos a plan | RF-6.1 | Dos vistas: los docentes en riesgo que aún no tienen plan, y todos los evaluados con sus indicadores débiles. |
| CU-DIR-36 | Crear un plan con sus compromisos y las asignaturas involucradas | RF-6.2 · RF-6.3 | El periodo de origen es aquel donde se detectó el bajo desempeño; el de verificación es el semestre siguiente. |
| CU-DIR-37 | Consultar los planes del departamento | RF-6.2 | |
| CU-DIR-38 | Editar un plan | RF-6.2 | La lista de ítems y la de asignaturas se reemplazan por completo al enviarlas. |
| CU-DIR-39 | Eliminar un plan | RF-6.2 | |
| CU-DIR-40 | Cerrar el plan con su resultado y su motivo | RF-6.4 | Estados: `BORRADOR → EN_SEGUIMIENTO → RESULTADO_DISPONIBLE → CERRADO_CUMPLIDO` o `CERRADO_NO_CUMPLIDO`. |
| CU-DIR-41 | Consultar los cursos y el historial de planes de un docente | RF-6.5 | |
| CU-DIR-42 | Consultar el resultado de la verificación del plan | RF-6.13 | `plan.status` es lo que el director firmó; `verification.result` —`MEJORO`, `NO_MEJORO` o `SIN_DATOS`— es lo que dijeron las notas. |
| CU-DIR-43 | Mantener el catálogo de acciones sugeridas del departamento | RF-6.6 | Se guarda como una configuración del ámbito del departamento. El director lee la institucional pero crea la suya propia para sobreescribirla. |
| CU-DIR-44 | Registrar el caso reportado por un programa académico (Formato 1) | RF-6.7 | El caso es interno al departamento y no se le comunica al docente. |
| CU-DIR-45 | Elaborar el acta del Formato 2 y justificar sus ítems con comentarios | RF-6.8 | Número, fecha, ítems, asignaturas y observaciones del Consejo. Los formatos se organizan en cinco aspectos: los cuatro del mapa de dimensiones más «Observaciones de los Estudiantes», que se justifica citando comentarios. |
| CU-DIR-46 | Cerrar el acta y congelar su contenido | RF-6.8 | El acta tiene su propio ciclo de vida —`BORRADOR → CERRADA → FIRMADA`— independiente del estado del plan. Al cerrarla se congela solo su contenido; el resto del plan sigue editable. Precondición: el acta debe estar completa. |
| CU-DIR-47 | Registrar los puntos de control y las notas de seguimiento (Formato 3) | RF-6.9 | |
| CU-DIR-48 | Generar y descargar el formato oficial en PDF o en Word | RF-6.10 | WeasyPrint y Jinja2; el Formato 3 se imprime en horizontal. La copia en Word no se almacena: es el borrador de trabajo, siempre generado del plan tal como está. |
| CU-DIR-49 | Cargar la versión firmada del formato | RF-6.10 | Cargar el Formato 2 firmado lleva el acta a `FIRMADA` (`CU-SIS-25`) y avisa al docente. |
| CU-DIR-50 | Eliminar la versión firmada | RF-6.10 | |
| CU-DIR-51 | Solicitar al docente un entregable de evidencia concreto | RF-6.11 | Estados de la solicitud: `PENDIENTE → EN_REVISION → APROBADA` o `RECHAZADA`. |
| CU-DIR-52 | Editar la solicitud de evidencia | — | |
| CU-DIR-53 | Consultar las solicitudes de evidencia del plan | RF-6.11 | |
| CU-DIR-54 | Comentar en el hilo de la solicitud | RF-6.11 | |
| CU-DIR-55 | Aprobar o rechazar la evidencia entregada | RF-6.11 · RF-6.12 | Un rechazo devuelve la solicitud a `PENDIENTE` y deja un comentario de sistema (`CU-SIS-28`). |
| CU-DIR-56 | Descargar el archivo de la evidencia | RF-6.11 | |
| CU-DIR-57 | Consultar las configuraciones vigentes de su departamento y las heredadas | Tabla 36 | El valor del departamento gana y el institucional es el respaldo. |
| CU-DIR-58 | Crear una configuración propia para sobreescribir el valor institucional | Tabla 36 | Un director puede leer las institucionales pero no modificarlas. |
| CU-DIR-59 | Actualizar o eliminar una configuración de su departamento | Tabla 36 | |
| CU-DIR-60 | Consultar el historial de cambios de una configuración | — | |

## Docente

| Código | Caso de uso | RF | Detalle |
| --- | --- | --- | --- |
| CU-DOC-01 | Consultar el panel de resumen propio | — | |
| CU-DOC-02 | Consultar los periodos y las materias propias | — | |
| CU-DOC-03 | Consultar el historial propio en los periodos evaluados | RF-5.3 | |
| CU-DOC-04 | Compararse con el periodo anterior y con el departamento | RF-5.3 | |
| CU-DOC-05 | Consultar los promedios por dimensión y la matriz propia | RF-5.4 | |
| CU-DOC-06 | Consultar los comentarios recibidos por materia | RF-5.5 | |
| CU-DOC-07 | Descargar el reporte PDF de la propia evaluación | RF-3.6 · RF-5.9 | Un docente solo puede descargar su propio reporte. |
| CU-DOC-08 | Consultar los planes de mejoramiento propios | RF-6.2 | El docente accede únicamente a los suyos. |
| CU-DOC-09 | Consultar el resultado de la verificación del plan | RF-6.13 | |
| CU-DOC-10 | Descargar el formato oficial del plan | RF-6.10 | El Formato 1 no se le comunica al docente. |
| CU-DOC-11 | Consultar las solicitudes de evidencia | RF-6.11 | |
| CU-DOC-12 | Cargar el archivo de la evidencia solicitada | RF-6.11 · RF-6.12 | La entrega lleva la solicitud a `EN_REVISION` (`CU-SIS-27`). |
| CU-DOC-13 | Eliminar una evidencia cargada | — | |
| CU-DOC-14 | Comentar en el hilo de la solicitud | RF-6.11 | |
| CU-DOC-15 | Descargar el archivo de una evidencia | RF-6.11 | |

## Sistema

| Código | Caso de uso | RF | Detalle |
| --- | --- | --- | --- |
| CU-SIS-01 | Validar que ambos PDF coincidan en periodo y departamento y sean de modalidades distintas | RF-3.2 | Un PDF cuyo título no declare la modalidad se rechaza. |
| CU-SIS-02 | Rechazar la carga de un departamento ajeno al del director (403) | RF-1.5 · RF-3.1 | El rechazo ocurre antes de guardar nada. Un administrador puede subir la evaluación de cualquier departamento. |
| CU-SIS-03 | Procesar la evaluación en segundo plano | RF-3.4 | |
| CU-SIS-04 | Extraer del PDF el docente, el curso, el grupo, las 22 preguntas y los comentarios | RF-3.3 | Las 22 preguntas se agrupan en 4 dimensiones. |
| CU-SIS-05 | Persistir los grupos, los puntajes y los comentarios extraídos | RF-3.3 | |
| CU-SIS-06 | Emitir el progreso del procesamiento en tiempo real | RF-3.4 | |
| CU-SIS-07 | Registrar el fallo y dejar la evaluación en `FAILED` | RF-3.4 | Extiende el procesamiento cuando el PDF no se puede parsear o persistir. |
| CU-SIS-08 | Clasificar el comentario por nivel de riesgo y categoría pedagógica | RF-4.1 | Se dispara al terminar el procesamiento del PDF y puede relanzarse a mano (`CU-DIR-10`). |
| CU-SIS-09 | Ejecutar los modelos de HuggingFace dentro del mismo proceso de la API | RF-4.1 · FA-5 | Configurados con `HUGGINGFACE_RISK_MODEL` y `HUGGINGFACE_CATEGORY_MODEL`. La inferencia es local, no un servicio externo. |
| CU-SIS-10 | Registrar el modelo y la confianza de la clasificación | — | |
| CU-SIS-11 | Verificar los indicadores del plan al terminar el procesamiento del PDF | RF-6.13 | El plan se cierra al firmar el Formato 3, antes de que existan las notas que probarían la mejora: por eso el cierre no puede ser el momento de la comparación. |
| CU-SIS-12 | Promediar al docente sobre todos sus grupos del periodo para dictar el veredicto | RF-6.13 | Es lo que pactó el acta. |
| CU-SIS-13 | Guardar aparte el desglose por asignatura del mismo indicador | RF-6.13 | Permite ver el caso en que la meta se alcanza en general pero una materia sigue baja. |
| CU-SIS-14 | Verificar los compromisos cualitativos al terminar el análisis de IA | RF-6.13 · RF-4.1 | Segunda pasada: necesita el nivel de riesgo y la categoría pedagógica ya calculados. |
| CU-SIS-15 | Levantar alerta solo con riesgo `ALTO` en la misma categoría pedagógica | RF-6.13 | La categoría debe ser la misma que motivó el compromiso. |
| CU-SIS-16 | Guardar los hallazgos de riesgo `MEDIO` como contexto, sin alerta | RF-6.13 | |
| CU-SIS-17 | Dictar el veredicto por reincidencia cuando todos los compromisos son cualitativos | RF-6.13 | Un plan sin ninguna meta medible no tiene número que lo juzgue. En cuanto el acta pactó una meta medible, mandan las notas: un comentario que reaparece no deshace una meta alcanzada. |
| CU-SIS-18 | Registrar la verificación conservando el riesgo y la categoría del comentario | RF-6.13 | Se guarda en `improvement_plan_verifications` y sus tablas `_items`, `_courses` y `_comments`. |
| CU-SIS-19 | Re-verificar el plan cuando se reclasifica a mano un comentario citado | RF-6.13 · RF-4.3 | Mantiene alineados el plan y el comentario. Ahí no se notifica al director: es quien acaba de hacer el cambio. |
| CU-SIS-20 | Dejar intacto el cierre firmado por el director | RF-6.4 · RF-6.13 | La verificación nunca reescribe el cierre. |
| CU-SIS-21 | Sugerir candidatos a plan entre los docentes bajo el umbral o con riesgo alto | RF-6.1 · RF-4.4 | Se consideran el promedio, cualquier indicador y la acumulación de comentarios de riesgo alto. |
| CU-SIS-22 | Registrar el periodo de origen en el que se detectó el bajo desempeño | RF-6.3 | |
| CU-SIS-23 | Heredar el catálogo institucional de acciones cuando el departamento no tiene uno propio | RF-6.6 | |
| CU-SIS-24 | Impedir la edición del contenido congelado del acta | RF-6.8 | Ítems, asignaturas, número y fecha del acta y observaciones del Consejo. |
| CU-SIS-25 | Llevar el acta a `FIRMADA` al cargar el Formato 2 firmado | RF-6.8 · RF-6.10 | La firma —no un paso de cierre aparte— es lo que pone el acuerdo en vigor. |
| CU-SIS-26 | Regenerar la matriz de seguimiento cada vez que se registra un seguimiento | — | El Formato 3 imprime la sección de seguimientos, así que se vuelve a renderizar. |
| CU-SIS-27 | Llevar la solicitud de evidencia a `EN_REVISION` tras la entrega | RF-6.12 | |
| CU-SIS-28 | Devolver la solicitud a `PENDIENTE` con un comentario de sistema al rechazarla | RF-6.12 | El comentario le indica al docente que debe reenviar. |
| CU-SIS-29 | Notificar a la contraparte cada transición del plan y del ciclo de evidencias | RF-6.12 · RF-7.1 | El aviso sale aunque quien actúa sea el destinatario: una misma cuenta puede ser las dos partes —un director con un plan a su propio nombre— y callar la notificación dejaría ese plan sin rastro del ciclo. |
| CU-SIS-30 | Alertar al director cuando una meta no se alcanzó o reaparece la queja del plan | RF-6.13 · RF-7.1 | La alerta va al director, no al docente, y solo cuando hay algo que decidir: una meta incumplida, una meta alcanzada en el promedio pero no en todas las asignaturas, o un comentario de riesgo alto que repite la observación del plan. |
| CU-SIS-31 | Enviar el correo institucional del evento del plan | RF-7.2 | |
| CU-SIS-32 | Emitir la notificación en tiempo real | — | |
| CU-SIS-33 | Continuar la operación aunque el aviso no se pueda entregar | — | Los avisos son de mejor esfuerzo: la mutación ya está persistida y auditada cuando se intentan enviar. |
| CU-SIS-34 | Validar el token de identidad en cada petición | RF-1.1 | Firebase resuelve la identidad y PostgreSQL los permisos: la autorización se lee de la base local, no del token. |
| CU-SIS-35 | Autorizar el endpoint y la ruta según el rol del usuario | RF-1.4 | Cada endpoint declara de forma explícita los roles habilitados. |
| CU-SIS-36 | Ocultar del menú lo que el rol no puede abrir | RF-1.4 | Comodidad de interfaz; el control efectivo reside en la API. |
| CU-SIS-37 | Confinar al director a su departamento y al docente a sus propios datos (403) | RF-1.5 | Pedir un recurso ajeno responde 403, no un dato distinto ni un listado vacío. |
| CU-SIS-38 | Verificar el permiso antes de entregar un archivo cargado | RF-3.6 | El directorio de cargas queda fuera de cualquier directorio estático. |
| CU-SIS-39 | Derivar el ámbito de la configuración de quien pregunta, nunca de un parámetro | RF-1.5 | Cada rol queda confinado a su propio ámbito. |
| CU-SIS-40 | Resolver el valor efectivo: el del departamento gana y el institucional es el respaldo | Tabla 36 | La unicidad de la clave es por ámbito. Una clave que admita sobreescritura departamental se lee resolviendo el ámbito; una institucional, sin departamento. |
| CU-SIS-41 | Rechazar con 403 el acceso a un ámbito ajeno | RF-1.5 | Un departamento distinto al propio se rechaza, nunca se ignora: contestar con el valor institucional a quien preguntó por otro departamento lo llevaría a guardar donde no quería. |
| CU-SIS-42 | Registrar el evento de auditoría de cada mutación | RF-8.1 | Con el usuario responsable y una descripción legible en español (`RNF-6.1`). Se registra desde la capa de servicios, en la misma operación que persiste el cambio. |

---

## Matriz de trazabilidad — Tabla 37 → casos de uso

| RF | Casos de uso |
| --- | --- |
| RF-1.1 | CU-VIS-02, CU-USR-02, CU-SIS-34 |
| RF-1.2 | CU-USR-01 |
| RF-1.3 | CU-ADM-09, CU-USR-03, CU-DIR-02 |
| RF-1.4 | CU-SIS-35, CU-SIS-36 |
| RF-1.5 | CU-SIS-02, CU-SIS-37, CU-SIS-39, CU-SIS-41 |
| RF-2.1 | CU-ADM-01 |
| RF-2.2 | CU-ADM-02, CU-ADM-03 |
| RF-2.3 | CU-ADM-04 |
| RF-2.4 | CU-ADM-08, CU-DIR-01, CU-DIR-04, CU-DIR-06 |
| RF-2.5 | CU-DIR-05 |
| RF-2.6 | CU-ADM-03, CU-ADM-05 |
| RF-3.1 | CU-DIR-08, CU-SIS-02 |
| RF-3.2 | CU-DIR-08, CU-SIS-01 |
| RF-3.3 | CU-DIR-13, CU-SIS-04, CU-SIS-05 |
| RF-3.4 | CU-DIR-09, CU-SIS-03, CU-SIS-06, CU-SIS-07 |
| RF-3.5 | CU-DIR-11, CU-DIR-12, CU-DIR-14, CU-DIR-15, CU-DIR-16 |
| RF-3.6 | CU-DIR-17, CU-DIR-18, CU-DOC-07, CU-SIS-38 |
| RF-4.1 | CU-DIR-10, CU-SIS-08, CU-SIS-09, CU-SIS-10, CU-SIS-14 |
| RF-4.2 | CU-DIR-20, CU-DIR-21 |
| RF-4.3 | CU-DIR-23, CU-SIS-19 |
| RF-4.4 | CU-DIR-22, CU-SIS-21 |
| RF-5.1 | CU-DIR-24, CU-DIR-25, CU-DOC-01 |
| RF-5.2 | CU-DIR-26 |
| RF-5.3 | CU-DIR-29, CU-DIR-30, CU-DOC-03, CU-DOC-04 |
| RF-5.4 | CU-DIR-31, CU-DOC-05 |
| RF-5.5 | CU-DIR-32, CU-DOC-02, CU-DOC-06 |
| RF-5.6 | CU-DIR-27 |
| RF-5.7 | CU-DIR-28 |
| RF-5.8 | CU-DIR-33 |
| RF-5.9 | CU-DIR-18, CU-DIR-19, CU-DIR-34, CU-DOC-07 |
| RF-6.1 | CU-ADM-14, CU-DIR-35, CU-SIS-21 |
| RF-6.2 | CU-DIR-36, CU-DIR-37, CU-DIR-38, CU-DIR-39, CU-DOC-08 |
| RF-6.3 | CU-DIR-36, CU-SIS-22 |
| RF-6.4 | CU-DIR-40, CU-SIS-20 |
| RF-6.5 | CU-DIR-41 |
| RF-6.6 | CU-DIR-43, CU-SIS-23 |
| RF-6.7 | CU-DIR-44 |
| RF-6.8 | CU-ADM-15, CU-DIR-45, CU-DIR-46, CU-SIS-24, CU-SIS-25 |
| RF-6.9 | CU-DIR-47, CU-SIS-26 |
| RF-6.10 | CU-DIR-48, CU-DIR-49, CU-DIR-50, CU-DOC-10, CU-SIS-25 |
| RF-6.11 | CU-DIR-51 a CU-DIR-56, CU-DOC-11 a CU-DOC-15 |
| RF-6.12 | CU-DIR-55, CU-DOC-12, CU-SIS-27, CU-SIS-28, CU-SIS-29 |
| RF-6.13 | CU-DIR-42, CU-DOC-09, CU-SIS-11 a CU-SIS-20, CU-SIS-30 |
| RF-7.1 | CU-USR-04, CU-USR-05, CU-SIS-29, CU-SIS-30, CU-SIS-32 |
| RF-7.2 | CU-SIS-31, CU-SIS-33 |
| RF-8.1 | CU-ADM-11, CU-ADM-13, CU-DIR-60, CU-SIS-42 |
| RF-8.2 | CU-ADM-10 |

