# Casos de uso — Sistema de Evaluación Docente (SET)

Los 21 diagramas de casos de uso en PlantUML, organizados por actor y área funcional.
Tabla de contenido lista para pegar en el documento de tesis:

```latex
\begin{table}[H]
    \caption{Diagramas de casos de uso por actor y área funcional. Fuente: elaboración propia.}
    \label{tab:cudiagramas}
    \centering
    \small
    \begin{tabular}{p{4.6cm} p{5.4cm} c c}
        \hline
        \textbf{Actor} & \textbf{Área funcional} & \textbf{Casos} & \textbf{Figura} \\
        \hline
        Todos & Vista de contexto & 10 & \ref{fig:cu00contexto} \\
        Visitante · Usuario autenticado & Acceso, sesión y notificaciones & 6 & \ref{fig:cu01visitantesesion} \\
        Administrador & Estructura institucional & 7 & \ref{fig:cu02adminestructura} \\
        Administrador & Usuarios, auditoría y configuración & 6 & \ref{fig:cu03adminusuarios} \\
        Director & Docentes y oferta académica & 6 & \ref{fig:cu04dirdocentes} \\
        Director & Carga y procesamiento & 6 & \ref{fig:cu05dircarga} \\
        Director & Consulta y descarga & 6 & \ref{fig:cu06dirconsulta} \\
        Director & Comentarios y alertas & 4 & \ref{fig:cu07dircomentarios} \\
        Director & Reportes del departamento & 5 & \ref{fig:cu08dirreportesdepto} \\
        Director & Reportes del docente & 7 & \ref{fig:cu09dirreportesdocente} \\
        Director & Planes: ciclo de vida & 8 & \ref{fig:cu10dirplanesciclo} \\
        Director & Planes: formatos oficiales & 8 & \ref{fig:cu11dirplanesformatos} \\
        Director & Planes: evidencias & 6 & \ref{fig:cu12dirplanesevidencias} \\
        Director & Planes: acciones sugeridas & 5 & \ref{fig:cu13dirplanesacciones} \\
        Docente & Resultados propios & 8 & \ref{fig:cu14docresultados} \\
        Docente & Planes propios & 8 & \ref{fig:cu15docplanes} \\
        Sistema & Procesamiento del PDF y análisis con IA & 9 & \ref{fig:cu16sisprocesamiento} \\
        Sistema & Verificación automática & 10 & \ref{fig:cu17sisverificacion} \\
        Sistema & Automatismos del plan & 3 & \ref{fig:cu18sisciclo} \\
        Sistema & Notificaciones y correo & 4 & \ref{fig:cu19sisavisos} \\
        Sistema & Seguridad, ámbito y auditoría & 6 & \ref{fig:cu20sisseguridad} \\
        \hline
    \end{tabular}
\end{table}
```

| Figura | Archivo |
| --- | --- |
| 00 | `00-contexto.puml` |
| 01 | `01-visitante-y-sesion.puml` |
| 02 | `02-admin-estructura-institucional.puml` |
| 03 | `03-admin-usuarios-auditoria-configuracion.puml` |
| 04 | `04-director-docentes-y-oferta.puml` |
| 05 | `05-director-carga-de-evaluaciones.puml` |
| 06 | `06-director-consulta-de-evaluaciones.puml` |
| 07 | `07-director-comentarios-y-alertas.puml` |
| 08 | `08-director-reportes-del-departamento.puml` |
| 09 | `09-director-reportes-del-docente.puml` |
| 10 | `10-director-planes-ciclo-de-vida.puml` |
| 11 | `11-director-planes-formatos.puml` |
| 12 | `12-director-planes-evidencias.puml` |
| 13 | `13-director-planes-acciones-sugeridas.puml` |
| 14 | `14-docente-mis-resultados.puml` |
| 15 | `15-docente-mis-planes.puml` |
| 16 | `16-sistema-procesamiento-y-analisis.puml` |
| 17 | `17-sistema-verificacion-de-planes.puml` |
| 18 | `18-sistema-ciclo-de-planes.puml` |
| 19 | `19-sistema-avisos-y-correo.puml` |
| 20 | `20-sistema-seguridad-y-auditoria.puml` |
