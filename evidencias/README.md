# Evidencias

Esta carpeta guarda las capturas y resultados de las pruebas. **Revisa cada captura antes de subirla: ninguna debe mostrar credenciales ni el panel "AWS Details".**

## Generadas automáticamente
| Archivo | Cómo se genera |
|---|---|
| `prueba_aceptacion_api-gateway_<fecha>.md/.json` | `python3 scripts/prueba_aceptacion.py --url $API_URL` |
| `prueba_aceptacion_function-url_<fecha>.md/.json` | `python3 scripts/prueba_aceptacion.py --url $FN_URL` |
| `prueba_aceptacion_local_<fecha>.md/.json` | `python3 scripts/prueba_aceptacion.py --local` (sin AWS; incluida como referencia) |
| `sin_respuesta.csv` | `python3 scripts/consultas_sin_respuesta.py --tabla asistente-tecnohogar-consultas --csv evidencias/sin_respuesta.csv` |
| `captura_frontend_local.png` | Frontend probado en local con conmutación a la ruta alternativa (referencia) |

## Capturas a tomar en AWS (nombre sugerido)
| # | Archivo | Contenido |
|---|---|---|
| 01 | `01_s3_docs.png` | Bucket de documentos con `documentos/` y `kb/` |
| 02 | `02_s3_web_hosting.png` | Static website hosting habilitado |
| 03 | `03_dynamodb_tablas.png` | Las 3 tablas activas |
| 04 | `04_dynamodb_kb_items.png` | Ítems de la base de conocimiento |
| 05 | `05_lambda_test.png` | Test exitoso desde la consola |
| 06 | `06_lambda_labrole.png` | Rol de ejecución LabRole |
| 07 | `07_lambda_env.png` | Variables de entorno |
| 08 | `08_apigw_rutas.png` | Rutas de la HTTP API |
| 09 | `09_apigw_throttling.png` | Throttling 5/10 |
| 10 | `10_lambda_function_url.png` | Function URL (Auth NONE) |
| 11 | `11_frontend.png` | Chat con respuesta y "No documentado" |
| 12 | `12_cloudwatch_logs.png` | Log stream con líneas de consulta |
| 13 | `13_cloudwatch_dashboard.png` | Dashboard con datos |
| 14 | `14_logs_insights.png` | Conteo por estado |
| 15 | `15_learner_lab_consumo.png` | Crédito usado con fecha |
| 16 | `16_limpieza.png` | Salida de `cleanup.sh` / consolas vacías |
| E1 | `E1_prueba_aceptacion.png` | Terminal con el resumen 25/25 |
| E2 | `E2_limite_429.png` | Bucle `curl` mostrando 200 … 429 |
| E3 | `E3_consultas_sin_respuesta.png` | Tabla `consultas` filtrada por estado |

## Evidencias tomadas en AWS (22/10/2026)
La carpeta `aws/` contiene las 17 capturas del despliegue real y `aws/RESULTADOS_AWS.md` con el resumen de resultados: prueba de aceptación 25/25 por API Gateway y por la URL de función, límite de uso (30 × 200, 5 × 429), Logs Insights y consumo del Learner Lab (US$ 0).
