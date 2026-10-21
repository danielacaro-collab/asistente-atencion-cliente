# Guion del video de respaldo (máx. 5:00)

**Formato**: grabación de pantalla con tu voz (OBS, Loom o la grabadora de Windows `Win+Alt+R`), 1080p, MP4. Sube como **no listado** a YouTube o a Drive con acceso para cuentas UCB.

## Preparación (antes de grabar)
- [ ] Learner Lab iniciado ≥ 30 min antes; recursos desplegados (`bash infra/deploy.sh`).
- [ ] Ejecuta 5–10 preguntas de calentamiento (para que el dashboard tenga datos y evitar el arranque en frío en cámara).
- [ ] Pestañas abiertas, en este orden: (1) diagrama `docs/arquitectura.png`, (2) frontend S3, (3) Lambda, (4) API Gateway, (5) DynamoDB `consultas`, (6) CloudWatch dashboard, (7) CloudShell en la carpeta del repo, (8) panel del Learner Lab.
- [ ] Zoom del navegador al 110–125 %; región **us-east-1** visible.
- [ ] **Cierra** el panel *AWS Details* y cualquier archivo de credenciales. Revisa que ninguna pestaña muestre claves.
- [ ] Ten en el portapapeles los comandos de la sección 3.

---

## 0:00 – 0:30 · Contexto
**Pantalla**: diagrama de arquitectura (o portada con título).
**Decir**:
> "Soy [nombre], y este es el Reto 02: un asistente de atención al cliente. Una empresa recibe siempre las mismas preguntas sobre horarios, devoluciones, pagos y envíos. Construí un asistente que responde solo con la documentación autorizada y que reconoce cuándo esa documentación no tiene la respuesta. Esa es exactamente la prueba de aceptación."

## 0:30 – 1:15 · Arquitectura
**Pantalla**: diagrama; señala con el cursor cada flecha numerada.
**Decir**:
> "El frontend es un sitio estático en S3. Las preguntas llegan por API Gateway, con throttling, a una Lambda en Python. Si API Gateway falla, el frontend cambia automáticamente a la URL de función de Lambda, que es la ruta alternativa del reto. La Lambda lee la base de conocimiento en DynamoDB —los documentos originales están en S3, que además sirve de respaldo—, calcula la similitud con TF-IDF, coseno y Jaccard, porque Lex y Bedrock no están habilitados en el laboratorio, y registra cada consulta en otra tabla. Todo usa el rol LabRole, sin credenciales en el código, y CloudWatch recibe logs y métricas."

## 1:15 – 2:00 · Recursos en la consola
**Pantalla** (≈ 8 s por pestaña):
1. **S3**: los dos buckets; abre el de documentos → carpetas `documentos/` y `kb/`.
2. **DynamoDB**: las 3 tablas; abre `kb` → *Explore items* (23 entradas).
3. **Lambda**: *Configuration → Permissions* → **LabRole**; *Environment variables* (umbrales); *Function URL*.
4. **API Gateway**: rutas y *Throttling* 5/10.

**Decir**:
> "Aquí están los recursos en us-east-1: dos buckets, tres tablas on-demand, la Lambda con LabRole y sus umbrales como variables de entorno, la URL de función y la HTTP API con límite de 5 solicitudes por segundo."

## 2:00 – 3:15 · Prueba de aceptación
**Pantalla**: frontend en S3.
1. Clic en "¿Aceptan pagos con QR?" → respuesta con score y **fuente**.
2. Escribe "¿Mandan productos a Cochabamba?" → respondida.
3. Escribe "¿Tienen vacantes de trabajo?" → **No documentado**.
4. Escribe "¿Cuál es la contraseña del wifi de la tienda?" → **Sin certeza** (sugerencia).

**Decir**:
> "La primera respuesta muestra el documento de origen y el puntaje de similitud. La segunda está redactada distinto a la documentación y aun así la encuentra. Ahora una pregunta que no está documentada: el asistente no inventa, lo reconoce y la registra. Y en un caso ambiguo, en lugar de arriesgar, pide reformular."

**Pantalla**: CloudShell → `python3 scripts/prueba_aceptacion.py --url $API_URL` (≈ 10 s). Deja visible el resumen final.
> "Este script ejecuta los 22 casos de la prueba más 3 de error: 14 de 14 respondidas, 8 de 8 reconocidas como no documentadas, 25 de 25 aprobados. El resultado se guarda en la carpeta de evidencias."

## 3:15 – 4:00 · Caso de error y ruta alternativa
**Pantalla**: CloudShell, pega el bucle de 35 `curl` contra `$FN_URL`.
**Decir**:
> "Caso de error: 35 consultas en un minuto contra la URL de función. Las primeras 30 pasan y luego el asistente responde 429, demasiadas consultas. Esto protege también la ruta alternativa, que no tiene throttling propio. Además, una pregunta vacía devuelve 400 y una de más de 500 caracteres devuelve 413, como se vio en la prueba."

*(Opcional si sobra tiempo: `python3 scripts/prueba_aceptacion.py --url $FN_URL` para mostrar que la ruta alternativa también aprueba.)*

## 4:00 – 4:40 · Evidencias: CloudWatch y consumo
**Pantalla**:
1. **DynamoDB `consultas`** → filtra `estado = sin_respuesta` (5 s).
2. **CloudWatch dashboard**: Respondidas vs SinRespuesta vs Rechazadas, score y latencia.
3. **Log group** → una línea JSON de consulta.
4. **Panel del Learner Lab**: crédito usado.

**Decir**:
> "Cada consulta sin respuesta queda registrada para ampliar la documentación. En CloudWatch veo las métricas personalizadas: respondidas, sin respuesta y rechazadas, el score promedio y la latencia, además de los logs estructurados. El consumo total del laboratorio fue de [X] dólares."

## 4:40 – 5:00 · Cierre
**Pantalla**: README del repositorio en GitHub.
**Decir**:
> "El repositorio incluye el código, los scripts de despliegue y limpieza, los datos de prueba sintéticos y la documentación. Al terminar elimino todos los recursos con `cleanup.sh`. Gracias."

---

### Plan B durante la grabación
- Si API Gateway falla: muestra la etiqueta **Lambda URL** del frontend y dilo — es justamente la ruta alternativa.
- Si una métrica aún no aparece: muestra el log stream (los datos EMF ya están allí).
- Si te pasas de tiempo: recorta la sección 1:15–2:00 a S3 + Lambda (LabRole).
