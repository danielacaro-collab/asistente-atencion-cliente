# Guía paso a paso en la consola de AWS (Learner Lab)

Esta guía crea manualmente los mismos recursos que `infra/deploy.sh`. Úsala si prefieres la consola o si quieres capturas de cada paso para el informe. Los nombres coinciden con `infra/config.env`; reemplaza `<CUENTA>` por tu ID de cuenta (12 dígitos, visible en la esquina superior derecha de la consola).

> 📸 Junto a cada paso se indica la **captura** que conviene tomar. En cada captura deben verse la **región** (esquina superior derecha) y la **fecha** (reloj del sistema o columna "Fecha de creación").

| Recurso | Nombre |
|---|---|
| Bucket documentos | `asistente-tecnohogar-docs-<CUENTA>` |
| Bucket web | `asistente-tecnohogar-web-<CUENTA>` |
| Tablas DynamoDB | `asistente-tecnohogar-kb` · `asistente-tecnohogar-consultas` · `asistente-tecnohogar-limites` |
| Lambda | `asistente-tecnohogar-fn` |
| HTTP API | `asistente-tecnohogar-api` |
| Dashboard | `asistente-tecnohogar-dashboard` |

---

## 0. Preparación

1. En AWS Academy → **Learner Lab** → **Start Lab**. Espera a que el círculo junto a "AWS" se ponga **verde** y haz clic en él para abrir la consola.
2. Verifica la región **N. Virginia (us-east-1)** arriba a la derecha.
3. Descarga el repositorio como .zip desde GitHub (o clónalo en CloudShell, ver §3.3).

> ⚠️ En el Learner Lab **no puedes crear roles IAM**. Siempre que se pida un rol, elige el existente **LabRole**.
> ⚠️ **Nunca** copies el contenido de *AWS Details → AWS CLI* (credenciales) en el código, en capturas ni en el video.

---

## 1. Amazon S3

### 1.1 Bucket de documentos (privado)

1. **S3 → Create bucket**.
2. *Bucket type*: General purpose. *Bucket name*: `asistente-tecnohogar-docs-<CUENTA>`.
3. *Object Ownership*: ACLs disabled.
4. *Block Public Access*: dejar **todo marcado** (privado).
5. *Bucket Versioning*: **Enable** (permite recuperar una versión anterior de la documentación).
6. *Default encryption*: **SSE-S3**. → **Create bucket**.
7. Abre el bucket → **Create folder** `documentos` → dentro, **Upload** los 4 archivos de `data/documentos/`.
8. **Create folder** `kb` → **Upload** `data/base_conocimiento.json`.

📸 *Captura 1*: lista de objetos del bucket con las carpetas `documentos/` y `kb/`.

### 1.2 Bucket del frontend (sitio web estático)

1. **Create bucket** → `asistente-tecnohogar-web-<CUENTA>`.
2. *Block Public Access*: **desmarca** "Block all public access" y confirma con la casilla de advertencia (solo este bucket será público, y solo para lectura).
3. **Create bucket**.
4. Pestaña **Properties** → *Static website hosting* → **Edit** → Enable · Host a static website · Index document `index.html` · Error document `index.html` → **Save**. Copia el **Bucket website endpoint** (http://asistente-tecnohogar-web-3024.s3-website-us-east-1.amazonaws.com/).
5. Pestaña **Permissions** → *Bucket policy* → **Edit** → pega `infra/politicas/bucket-policy-web.json` reemplazando `__WEB_BUCKET__` por el nombre del bucket → **Save**.
6. (Los archivos del frontend se suben en el paso 6, cuando ya tengas las URLs de la API.)

📸 *Captura 2*: Properties → Static website hosting habilitado con el endpoint.

---

## 2. Amazon DynamoDB

Repite para cada tabla: **DynamoDB → Tables → Create table**.

| Tabla | Partition key (String) | TTL |
|---|---|---|
| `asistente-tecnohogar-kb` | `id` | No |
| `asistente-tecnohogar-consultas` | `consulta_id` | Sí, atributo `expira` |
| `asistente-tecnohogar-limites` | `clave` | Sí, atributo `expira` |

1. *Table name* y *Partition key* según la tabla. Sin sort key.
2. *Table settings* → **Customize settings** → *Read/write capacity settings* → **On-demand** (pagas solo por solicitud; ideal para tráfico bajo e impredecible).
3. Etiqueta (opcional) `Proyecto = asistente-tecnohogar` → **Create table**.
4. Para `consultas` y `limites`: abre la tabla → pestaña **Additional settings** → *Time to Live (TTL)* → **Turn on** → atributo `expira` → **Turn on TTL**.

### 2.1 Cargar la base de conocimiento

Opción recomendada (1 comando, desde **CloudShell**, icono `>_` en la barra superior):

```bash
git clone https://github.com/danielacaro-collab/asistente-atencion-cliente.git
cd asistente-atencion-cliente
python3 scripts/cargar_base_conocimiento.py --tabla asistente-tecnohogar-kb
```

Alternativa manual: tabla `kb` → **Explore table items** → **Create item** → *JSON view* (desactiva "View DynamoDB JSON") → pega una entrada del JSON → **Create item**. (Son 23 entradas; solo recomendable para mostrar el formato.)

📸 *Captura 3*: lista de las 3 tablas en estado *Active*. *Captura 4*: Explore items de `kb` con las 23 entradas.

---

## 3. AWS Lambda

### 3.1 Empaquetar el código

En tu computadora (o en CloudShell, dentro del repositorio):

```bash
cd src/asistente && zip ../../asistente.zip *.py && cd ../..
```

El .zip contiene solo los 5 archivos `.py` en la **raíz** (sin carpeta). No hay dependencias externas.

### 3.2 Crear la función

1. **Lambda → Create function → Author from scratch**.
2. *Function name*: `asistente-tecnohogar-fn` · *Runtime*: **Python 3.12** · *Architecture*: x86_64.
3. *Permissions* → **Change default execution role** → **Use an existing role** → **LabRole**.
4. **Create function**.
5. *Code* → **Upload from → .zip file** → `asistente.zip` → **Save**.
6. *Runtime settings* → **Edit** → *Handler*: `lambda_function.lambda_handler` → **Save**.
7. **Configuration → General configuration → Edit**: *Memory* 256 MB · *Timeout* 10 s → **Save**.
8. **Configuration → Environment variables → Edit → Add**:

| Key | Value |
|---|---|
| `KB_SOURCE` | `dynamodb` |
| `KB_TABLE` | `asistente-tecnohogar-kb` |
| `LOG_TABLE` | `asistente-tecnohogar-consultas` |
| `RATE_TABLE` | `asistente-tecnohogar-limites` |
| `DOCS_BUCKET` | `asistente-tecnohogar-docs-<CUENTA>` |
| `KB_S3_KEY` | `kb/base_conocimiento.json` |
| `UMBRAL_RESPUESTA` | `0.38` |
| `UMBRAL_SUGERENCIA` | `0.22` |
| `LIMITE_POR_MINUTO` | `30` |
| `MAX_CARACTERES` | `500` |
| `LOG_TTL_DIAS` | `30` |
| `METRIC_NAMESPACE` | `AsistenteAtencionCliente` |
| `ALLOWED_ORIGIN` | `http://asistente-tecnohogar-web-<CUENTA>.s3-website-us-east-1.amazonaws.com` |
| `KB_CACHE_SEGUNDOS` | `300` |
| `DEBUG_SIMILITUD` | `false` |

> Las variables de entorno contienen **solo nombres de recursos y parámetros**, nunca claves. Los permisos para leer/escribir DynamoDB y S3 los otorga **LabRole**.

### 3.3 Probar desde la consola

**Test → Create new event** → nombre `pregunta-ok` → JSON:

```json
{ "pregunta": "¿Aceptan pagos con QR?" }
```

**Test** → debe devolver `statusCode: 200` y `"estado": "respondida"`. Crea un segundo evento `pregunta-fuera` con `{"pregunta": "¿Tienen vacantes de trabajo?"}` → `"estado": "sin_respuesta"`.

📸 *Captura 5*: resultado del test con `estado: respondida`. *Captura 6*: pestaña Configuration → Permissions mostrando **LabRole**. *Captura 7*: variables de entorno.

---

## 4. API Gateway (ruta principal)

1. **API Gateway → Create API → HTTP API → Build**.
2. **Add integration → Lambda** → región us-east-1 → `asistente-tecnohogar-fn` · *Version* 2.0. *API name*: `asistente-tecnohogar-api` → **Next**.
3. *Configure routes*:
   - `ANY` `/preguntar` → integración Lambda (ANY incluye POST y el preflight OPTIONS).
   - `GET` `/salud` → integración Lambda.
4. *Stages*: `$default` con **Auto-deploy** activado → **Next → Create**.
5. **No configures CORS** en API Gateway: la Lambda devuelve las cabeceras CORS (una sola fuente de verdad, igual que para la URL de función).
6. **Protect → Throttling → Edit** (default route throttling): *Rate* 5 · *Burst* 10 → **Save**.
7. Copia el **Invoke URL** (`https://XXXX.execute-api.us-east-1.amazonaws.com`).

La consola agrega automáticamente el permiso para que API Gateway invoque la Lambda (lo verás en Lambda → Configuration → Permissions → Resource-based policy).

Prueba en CloudShell:

```bash
curl -s -X POST https://XXXX.execute-api.us-east-1.amazonaws.com/preguntar \
  -H 'Content-Type: application/json' -d '{"pregunta":"¿A qué hora abren los sábados?"}'
```

📸 *Captura 8*: rutas de la HTTP API. *Captura 9*: configuración de throttling.

---

## 5. Ruta alternativa: URL de función de Lambda

Úsala si API Gateway no está disponible o falla en el lab. Se recomienda crearla **siempre**, así el frontend puede conmutar automáticamente.

1. Lambda `asistente-tecnohogar-fn` → **Configuration → Function URL → Create function URL**.
2. *Auth type*: **NONE**.
3. *Configure cross-origin resource sharing (CORS)*: **dejar desmarcado** (la Lambda ya maneja CORS).
4. **Save**. Copia la URL (`https://XXXXXXXX.lambda-url.us-east-1.on.aws/`).

### 5.1 Permisos

Con *Auth type NONE* la consola crea automáticamente **dos** declaraciones en la política de recursos: `lambda:InvokeFunctionUrl` (condición `FunctionUrlAuthType = NONE`) y `lambda:InvokeFunction` (condición `InvokedViaFunctionUrl = true`). Ver `infra/politicas/lambda-resource-policy-ejemplo.json`.

### 5.2 Si la URL responde 403 Forbidden

Falta una de las dos declaraciones. **Configuration → Permissions → Resource-based policy statements → Add permissions → Function URL** → Auth type NONE → **Save**. Desde CloudShell también:

```bash
aws lambda add-permission --function-name asistente-tecnohogar-fn --statement-id url-invoke-url \
  --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE
aws lambda add-permission --function-name asistente-tecnohogar-fn --statement-id url-invoke-function \
  --action lambda:InvokeFunction --principal '*' --invoked-via-function-url
```

📸 *Captura 10*: Function URL creada con Auth type NONE.

---

## 6. Publicar el frontend

1. Copia `frontend/config.example.js` como `frontend/config.js` y reemplaza las URLs:
   ```js
   window.ASISTENTE_CONFIG = {
     apiUrl: "https://XXXX.execute-api.us-east-1.amazonaws.com/preguntar",
     fallbackUrl: "https://XXXXXXXX.lambda-url.us-east-1.on.aws/preguntar"
   };
   ```
   Si API Gateway no está disponible, pon la URL de función en ambos campos.
2. Bucket `asistente-tecnohogar-web-<CUENTA>` → **Upload** → `index.html`, `app.js`, `styles.css`, `config.js` → **Upload**.
3. Abre el *Bucket website endpoint* en el navegador y haz una pregunta. La etiqueta arriba a la derecha indica la ruta usada (**API Gateway** o **Lambda URL**).

📸 *Captura 11*: el chat con una respuesta `respondida` y otra `No documentado`.

---

## 7. Amazon CloudWatch

### 7.1 Logs

1. **CloudWatch → Log groups → `/aws/lambda/asistente-tecnohogar-fn`** (aparece tras la primera invocación).
2. **Actions → Edit retention setting → 1 week** (controla costo y cumple "mínima retención necesaria").
3. Abre el último *log stream*: verás una línea JSON `"evento": "consulta"` por cada pregunta, con estado, score y latencia.

### 7.2 Métricas personalizadas (EMF)

La Lambda imprime en el log un JSON con formato *Embedded Metric Format*; CloudWatch lo convierte en métricas sin llamar a `PutMetricData`.
**CloudWatch → Metrics → All metrics → AsistenteAtencionCliente → Servicio**: `Consultas`, `Respondidas`, `SinRespuesta`, `Sugerencias`, `Rechazadas`, `ScoreSimilitud`, `LatenciaMs`. (Tardan 1–3 minutos en aparecer la primera vez.)

### 7.3 Dashboard

**Dashboards → Create dashboard** → `asistente-tecnohogar-dashboard` → cancela el asistente de widget → **Actions → View/edit source** → pega `infra/dashboard.json` reemplazando `__REGION__` por `us-east-1`, `__NAMESPACE__` por `AsistenteAtencionCliente` y `__LAMBDA__` por `asistente-tecnohogar-fn` → **Update** → **Save**.

### 7.4 Alarmas

**Alarms → Create alarm → Select metric → AsistenteAtencionCliente → Servicio → SinRespuesta** → *Statistic* Sum · *Period* 15 min → *Greater than* 5 → *Notification*: **Remove** (el lab no requiere SNS) → nombre `asistente-tecnohogar-muchas-sin-respuesta` → **Create alarm**. Repite con `AWS/Lambda → Errors` (> 0 en 5 min) → `asistente-tecnohogar-errores-lambda`.

### 7.5 Consulta de Logs Insights (para evidencias)

**Logs Insights** → grupo `/aws/lambda/asistente-tecnohogar-fn`:

```
fields @timestamp, Estado, ScoreSimilitud, LatenciaMs, Origen
| filter ispresent(Estado)
| stats count(*) as consultas, avg(ScoreSimilitud) as score_medio, pct(LatenciaMs, 90) as p90_ms by Estado
```

📸 *Captura 12*: log stream con las líneas de consulta. *Captura 13*: dashboard con datos. *Captura 14*: resultado de Logs Insights.

---

## 8. Consumo del crédito (Learner Lab)

En la página del Learner Lab, arriba, se muestra **"Used $X of $50"** (o el monto asignado). Toma la captura después de la prueba de aceptación.
También: consola → **Billing and Cost Management → Bills** (puede tener retraso de hasta 24 h).

📸 *Captura 15*: panel del Learner Lab con el crédito usado y la fecha.

---

## 9. Limpieza

Opción rápida: `bash infra/cleanup.sh` en CloudShell. Manual, en este orden:

1. Lambda → Function URL → **Delete**; luego **Actions → Delete function**.
2. API Gateway → `asistente-tecnohogar-api` → **Delete**.
3. DynamoDB → selecciona las 3 tablas → **Delete** (desmarca "Create backup").
4. S3 → cada bucket → **Empty** (escribe *permanently delete*) → **Delete**. El bucket de documentos tiene versionado: *Empty* también borra las versiones.
5. CloudWatch → borra el dashboard, las 2 alarmas y el grupo de logs.
6. Learner Lab → **End Lab**.

📸 *Captura 16*: listas vacías (Lambda, DynamoDB, S3) o la salida de verificación de `cleanup.sh`.

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `AccessDenied` al crear un rol | El lab no permite crear roles | Usa **LabRole** |
| Frontend muestra "No se pudo contactar" | `config.js` con URL incorrecta o error CORS | Revisa la consola del navegador (F12); `ALLOWED_ORIGIN` debe ser exactamente la URL del sitio, sin `/` final |
| 403 en la URL de función | Falta un permiso | §5.2 |
| 403 en el sitio S3 | Bloqueo de acceso público o falta la política | §1.2 pasos 2 y 5 |
| `estado: error` en `/salud` (503) | Nombre de tabla mal escrito o tabla vacía | Revisa variables de entorno y §2.1 |
| Métricas no aparecen | Aún no se procesan los logs | Espera 1–3 minutos |
| Todo dejó de funcionar | La sesión del lab expiró (4 h) | **Start Lab** de nuevo; los recursos se conservan |
