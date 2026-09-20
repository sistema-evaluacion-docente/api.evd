# Casos de uso — Sistema de Evaluación Docente (SET)

Los 21 diagramas de casos de uso en PlantUML, organizados por actor y área funcional.
`render-pdf.sh` genera los PDF en `pdf/` y `casos-de-uso-latex.txt` es la subsección completa
para la tesis. Tabla de contenido lista para pegar en el documento de tesis:

```latex
\begin{longtable}{|>{\footnotesize\raggedright\arraybackslash\hspace{0pt}}p{0.25\textwidth}|>{\footnotesize\raggedright\arraybackslash\hspace{0pt}}p{0.37\textwidth}|>{\footnotesize\centering\arraybackslash\hspace{0pt}}p{0.08\textwidth}|>{\footnotesize\centering\arraybackslash\hspace{0pt}}p{0.09\textwidth}|}
\caption{Diagramas de casos de uso por actor y área funcional. Fuente: elaboración propia.}\label{tab:cudiagramas}\\
\hline
\textbf{\footnotesize Actor} & \textbf{\footnotesize Área funcional} & \textbf{\footnotesize Casos} & \textbf{\footnotesize Figura} \\ \hline
\endfirsthead

\multicolumn{4}{l}{\small\itshape Continuación de la Tabla \ref{tab:cudiagramas}}\\
\hline
\textbf{\footnotesize Actor} & \textbf{\footnotesize Área funcional} & \textbf{\footnotesize Casos} & \textbf{\footnotesize Figura} \\ \hline
\endhead

\multicolumn{4}{r}{\small Continúa en la siguiente página}\\
\endfoot

\hline
\endlastfoot

Todos & Vista de contexto & 10 & \ref{fig:cu00contexto} \\ \hline
Visitante · Usuario autenticado & Acceso, sesión y notificaciones & 5 & \ref{fig:cu01visitantesesion} \\ \hline
Administrador & Estructura institucional & 7 & \ref{fig:cu02adminestructura} \\ \hline
Administrador & Usuarios, auditoría y configuración & 6 & \ref{fig:cu03adminusuarios} \\ \hline
Director & Docentes y oferta académica & 6 & \ref{fig:cu04dirdocentes} \\ \hline
Director & Carga y procesamiento & 6 & \ref{fig:cu05dircarga} \\ \hline
Director & Consulta y descarga & 6 & \ref{fig:cu06dirconsulta} \\ \hline
Director & Comentarios y alertas & 4 & \ref{fig:cu07dircomentarios} \\ \hline
Director & Reportes del departamento & 5 & \ref{fig:cu08dirreportesdepto} \\ \hline
Director & Reportes del docente & 7 & \ref{fig:cu09dirreportesdocente} \\ \hline
Director & Planes: ciclo de vida & 8 & \ref{fig:cu10dirplanesciclo} \\ \hline
Director & Planes: formatos oficiales & 7 & \ref{fig:cu11dirplanesformatos} \\ \hline
Director & Planes: evidencias & 6 & \ref{fig:cu12dirplanesevidencias} \\ \hline
Director & Planes: acciones sugeridas & 5 & \ref{fig:cu13dirplanesacciones} \\ \hline
Docente & Resultados propios & 8 & \ref{fig:cu14docresultados} \\ \hline
Docente & Planes propios & 8 & \ref{fig:cu15docplanes} \\ \hline
Sistema & Procesamiento del PDF y análisis con IA & 8 & \ref{fig:cu16sisprocesamiento} \\ \hline
Sistema & Verificación automática & 6 & \ref{fig:cu17sisverificacion} \\ \hline
Sistema & Automatismos del plan & 3 & \ref{fig:cu18sisciclo} \\ \hline
Sistema & Notificaciones y correo & 4 & \ref{fig:cu19sisavisos} \\ \hline
Sistema & Seguridad, ámbito y auditoría & 6 & \ref{fig:cu20sisseguridad} \\
\end{longtable}
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
