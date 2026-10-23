# Resultados obtenidos en AWS (Learner Lab, us-east-1, 22/10/2026)

Resumen transcrito de las capturas de esta carpeta. Cuenta del laboratorio con sufijo de recursos `3024`.

## Prueba de aceptación (`scripts/prueba_aceptacion.py`, 22 preguntas + 3 casos de error)

| Ruta | Resultado | Documentadas | No documentadas | Errores | Latencia media | Captura |
|---|---|---|---|---|---|---|
| API Gateway (ruta principal) | **25/25** | 14/14 | 8/8 | 3/3 | 240 ms | `16_prueba_aceptacion_api_gateway_25de25.png` |
| URL de función (ruta alternativa) | **25/25** | 14/14 | 8/8 | 3/3 | 70 ms | `17_prueba_aceptacion_function_url_y_limite_429.png` |

- Score de las preguntas documentadas: 0,454 – 0,901 (todas `respondida` con la entrada correcta).
- Score máximo de las no documentadas: 0,346 (4 `sin_respuesta`, 4 `sugerencia`; ninguna respuesta inventada).
- Casos de error: pregunta vacía → 400, JSON inválido → 400, pregunta de más de 500 caracteres → 413.

## Caso de error principal: límite de uso

35 solicitudes en menos de un minuto a la URL de función desde el mismo cliente → **30 × HTTP 200 y 5 × HTTP 429**, repetido dos veces con el mismo resultado (`17_…png`).

## Observabilidad y costo

| Evidencia | Resultado | Captura |
|---|---|---|
| Logs Insights por estado | respondida: score medio 0,7194 · sugerencia: 0,2874 · sin_respuesta: 0,0118 | `14_cloudwatch_logs_insights.png` |
| Arranque en frío | 3 461 ms la primera invocación; 2–26 ms en caliente | `06_…png`, `11_…png` |
| Alarmas | errores de Lambda y > 5 consultas sin respuesta en 15 min | `13_cloudwatch_alarmas.png` |
| Consumo del Learner Lab | US$ 0 de US$ 50 | `15_learner_lab_consumo.png` |
