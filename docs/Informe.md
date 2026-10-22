# Borrador del informe técnico (PDF)

> Archivo final: **`PF_R02_CaroArrazolaDanielaAlejandra.pdf`** · Carta o A4 · letra 11 pt · **máx. 12 páginas** sin anexos.
> Los textos entre `[corchetes]` se completan después de desplegar. Las 📸 remiten a las capturas de `docs/guia_consola_aws.md` (región y fecha visibles).
> Extensión objetivo por sección según la rúbrica entre paréntesis.

---

## 0. Carátula (1 pág.)

- **Universidad Católica Boliviana** — Computación en la Nube — Proyecto Final
- **Reto 02: Asistente inteligente de atención al cliente**
- Estudiante: Daniela Alejandra Caro Arrazola · daniela.caro@ucb.edu.bo
- Fecha: [23/10/2026]
- Repositorio: [https://github.com/danielacaro-collab/asistente-atencion-cliente/]
- Video de respaldo: [enlace no listado YouTube / Drive con acceso UCB]
- (Opcional) miniatura del diagrama de arquitectura.

---

## 1. Resumen ejecutivo (½ pág.) — *Problema de negocio*

TecnoHogar, una cadena de tiendas de electrodomésticos y tecnología, recibe todos los días las mismas preguntas: horarios, devoluciones, garantías, medios de pago y envíos. Responderlas una por una ocupa el tiempo del personal y, cuando cada persona responde a su manera, el cliente recibe información inconsistente.

Se construyó un **asistente web** que contesta estas preguntas al instante **usando únicamente la documentación oficial de la empresa**. Cada respuesta indica de qué documento proviene. Cuando la pregunta no está cubierta por la documentación, el asistente **no inventa**: lo dice con claridad, ofrece los canales de contacto humano y guarda la pregunta para que el equipo decida si debe documentarla.

La solución funciona completamente en la nube de AWS, sin servidores que administrar, y solo genera costo cuando alguien la usa.

**Resultado de la prueba de aceptación:** [25/25] verificaciones aprobadas: el asistente respondió correctamente las [14/14] preguntas cubiertas por la documentación y reconoció las [8/8] preguntas no cubiertas, además de manejar correctamente 3 entradas inválidas. Tiempo de respuesta promedio: [X] ms. Costo del proyecto en el laboratorio: [US$ X].

---

## 2. Problema y alcance (1 pág.) — *Problema de negocio*

### 2.1 Caso real
Una empresa recibe consultas repetitivas sobre **productos, políticas, horarios y procedimientos** por WhatsApp, correo y en tienda. Estimación de referencia (supuesto para el caso): el 60–70 % de las consultas son preguntas frecuentes con respuesta ya documentada.

### 2.2 Usuarios afectados
- **Clientes**: esperan horas por una respuesta simple o reciben datos contradictorios.
- **Personal de atención**: dedica tiempo a preguntas repetitivas en lugar de casos complejos (reclamos, ventas a empresas).
- **Responsable de políticas/calidad**: no sabe qué preguntas no están cubiertas por la documentación.

### 2.3 Alcance — qué entra
- Interfaz web de chat publicada en S3.
- API HTTPS (API Gateway) y ruta alternativa (URL de función de Lambda) para recibir preguntas.
- Base de 23 respuestas autorizadas en DynamoDB, derivadas de 4 documentos oficiales en S3 (devoluciones y garantías; horarios, sucursales y contacto; productos, precios y pagos; envíos, pedidos y reclamos).
- Búsqueda de la respuesta más relevante por **similitud de texto** (TF-IDF, coseno y Jaccard) implementada en Python.
- Reconocimiento de preguntas sin respuesta y **registro de todas las consultas** en DynamoDB.
- **Límites de uso** (throttling en API Gateway + límite por cliente) y manejo seguro de credenciales (LabRole, sin claves en el código).
- Métricas, logs, dashboard y alarmas en CloudWatch.

### 2.4 Alcance — qué queda fuera
- Comprensión semántica avanzada o generación de texto con IA (Lex y Bedrock no están habilitados en el Learner Lab).
- Conversaciones de varios turnos (cada pregunta se responde de forma independiente).
- Consultas sobre datos personales del cliente (estado real de un pedido, saldo de crédito): requieren autenticación e integración con sistemas internos.
- Idiomas distintos del español.
- Autenticación de usuarios y panel de administración web (las consultas sin respuesta se revisan con un script).
- Dominio propio y HTTPS en el frontend (se propone CloudFront para producción).

### 2.5 Prueba de aceptación (tal como se definió)
> *Responder preguntas sustentadas por el material de prueba y reconocer cuándo la documentación no contiene la respuesta.*

Operacionalización (`data/casos_prueba.json`):
- **14 preguntas cubiertas**, redactadas distinto a la documentación (p. ej. "¿Mandan productos a Cochabamba?"): deben devolver `estado = respondida` y la entrada correcta.
- **8 preguntas no cubiertas** (vacantes, wifi, precio del dólar, mascotas…): deben devolver `sin_respuesta` o `sugerencia`, nunca una respuesta.
- **3 casos de error**: pregunta vacía (400), JSON inválido (400), pregunta > 500 caracteres (413).
- Criterio de aprobación: 100 % de los casos.

---

## 3. Arquitectura (2 pág.) — *Arquitectura*

📸 Insertar `docs/arquitectura.png` a ancho completo.

### 3.1 Flujo de datos
(Resumir los 10 pasos de `docs/arquitectura.md` §2 en un párrafo o lista numerada que coincida con los números del diagrama.)

### 3.2 Justificación por servicio
(Copiar la tabla de `docs/arquitectura.md` §4: servicio, por qué, alternativa descartada.) Puntos a destacar en el texto:
- **Arquitectura 100 % serverless**: costo cero en reposo, sin parches ni servidores — clave en un laboratorio con crédito limitado.
- **Dos rutas de entrada al mismo código**: API Gateway (principal, con throttling) y URL de función (alternativa exigida por el reto). El frontend conmuta automáticamente.
- **DynamoDB para tres usos distintos** (base de conocimiento, registro y contador de límites), cada uno aprovechando una característica: lectura rápida, TTL y contadores atómicos.
- **S3 como fuente de verdad documental** y respaldo si DynamoDB falla (degradación controlada).

### 3.3 Algoritmo de similitud
Fórmula y umbrales (copiar de README §"Cómo decide el asistente"). Explicar en 4–5 líneas: normalización → TF-IDF → coseno con la mejor variante → Jaccard de trigramas → factor de cobertura → umbral. Mencionar que el umbral se calibró con los casos de prueba (mínimo documentado 0.454, máximo no documentado 0.280).

---

## 4. Implementación (2–3 pág.) — *Implementación e integración*

### 4.1 Pasos de despliegue
1. Inicio del Learner Lab y verificación de región us-east-1.
2. Creación de buckets S3 (documentos privado/cifrado/versionado; web con hosting estático).
3. Creación de 3 tablas DynamoDB on-demand y TTL.
4. Carga de documentos a S3 y de la base de conocimiento a DynamoDB.
5. Creación de la Lambda con LabRole, variables de entorno y prueba desde consola.
6. Creación de la HTTP API con throttling.
7. Creación de la URL de función (ruta alternativa).
8. Publicación del frontend con las URLs.
9. Configuración de CloudWatch (retención, dashboard, alarmas).

Todo está automatizado en `infra/deploy.sh` (idempotente) y documentado manualmente en `docs/guia_consola_aws.md`. [Indicar cuál se usó.]

### 4.2 Configuración relevante
| Servicio | Parámetro | Valor |
|---|---|---|
| Lambda | Runtime / memoria / timeout | Python 3.12 / 256 MB / 10 s |
| Lambda | Rol | LabRole |
| Lambda | Umbrales | 0.38 respuesta · 0.22 sugerencia |
| API Gateway | Throttling | 5 rps · ráfaga 10 |
| Lambda | Límite por cliente | 30 consultas/minuto |
| DynamoDB | Capacidad | On-demand |
| DynamoDB | TTL | consultas 30 días · límites 2 min |
| CloudWatch | Retención de logs | 7 días |

### 4.3 Capturas (una o dos por servicio, con región y fecha visibles)
- 📸 1 Bucket de documentos con `documentos/` y `kb/`.
- 📸 2 Bucket web con *Static website hosting* habilitado.
- 📸 3 Las 3 tablas DynamoDB activas · 📸 4 ítems de la tabla `kb`.
- 📸 5 Test de la Lambda exitoso · 📸 6 LabRole como rol de ejecución · 📸 7 variables de entorno.
- 📸 8 Rutas de la HTTP API · 📸 9 throttling.
- 📸 10 Function URL creada.
- 📸 11 Frontend funcionando.

### 4.4 Fragmento de código clave
Incluir (máx. 20 líneas) la función `clasificar()` y la línea del cálculo del score de `similitud.py`. El resto, en anexos y en el repositorio.

---

## 5. Pruebas y resultados (1–2 pág.) — *Implementación; seguridad y pruebas*

### 5.1 Ejecución de la prueba de aceptación
```
python3 scripts/prueba_aceptacion.py --url <API_URL>
```
📸 Salida de la terminal en CloudShell + tabla de `evidencias/prueba_aceptacion_api-gateway_<fecha>.md`.

| Métrica | Resultado |
|---|---|
| Preguntas documentadas respondidas correctamente | [14/14] |
| Preguntas no documentadas reconocidas | [8/8] ([6] sin_respuesta, [2] sugerencia) |
| Casos de error con el código HTTP correcto | [3/3] |
| Latencia media medida por el cliente | [X ms] (arranque en frío: [Y ms]) |
| Falsos positivos (respuesta a una pregunta no documentada) | [0] |

Ejemplos para el texto:
- ✅ "¿Mandan productos a Cochabamba?" → ENV-002, score [0.55]: aunque "mandan" y "Cochabamba" no son la redacción del documento, el diccionario de sinónimos y las variantes resuelven la consulta.
- ✅ "¿Tienen vacantes de trabajo disponibles?" → `sin_respuesta`, score [0.01]: ninguna palabra aparece en la documentación.
- ⚠️ "¿Cuál es la contraseña del wifi de la tienda?" → `sugerencia`, score [0.28]: comparte "tienda" con sucursales, pero el factor de cobertura evita responder. El asistente pide reformular en vez de inventar.

### 5.2 Ruta alternativa
Repetir la prueba con la URL de función: `python3 scripts/prueba_aceptacion.py --url <FN_URL>` → [25/25]. 📸 salida.

### 5.3 Caso de error / condición límite
Elegir uno principal y documentarlo con captura:
- **Límite de uso**: 35 solicitudes en un minuto → las primeras 30 devuelven 200 y las siguientes **429** con `Retry-After: 60`. 📸 salida del bucle `curl`, y la métrica `Rechazadas` en CloudWatch.
- Complementarios: JSON inválido (400), pregunta de 600 caracteres (413), simulación de caída de API Gateway (el frontend muestra la etiqueta "Lambda URL").

### 5.4 Registro de consultas sin respuesta
📸 Tabla `consultas` filtrada por `estado = sin_respuesta`, o salida de `scripts/consultas_sin_respuesta.py`. Explicar que esta lista es la retroalimentación para ampliar la documentación.

### 5.5 Pruebas automatizadas
43 pruebas con `pytest` + `moto` (DynamoDB y S3 simulados): similitud, validación, límite de uso, respaldo S3, formato EMF y que la IP no se guarde en claro. 📸 `pytest -q` → `43 passed`.

---

## 6. Seguridad, observabilidad y costo (1 pág.) — *Seguridad, pruebas y costo*

### 6.1 Secretos y permisos
- **Cero credenciales en el código o en el repositorio.** La Lambda obtiene permisos temporales del rol **LabRole**; los scripts usan la sesión de CloudShell. El `.gitignore` excluye archivos de credenciales, `.env`, llaves y las salidas del despliegue. 📸 Configuration → Permissions con LabRole.
- Las variables de entorno contienen solo nombres de recursos y parámetros.
- *Limitación reconocida*: LabRole es amplio. En producción se crearía un rol propio con mínimo privilegio (`dynamodb:Scan` en `kb`, `PutItem` en `consultas`, `UpdateItem` en `limites`, `s3:GetObject` en `kb/*`). Incluir esa política en anexos.
- **Datos**: bucket de documentos privado, cifrado SSE-S3 y versionado; el bucket web solo permite `s3:GetObject`. La IP del cliente se guarda como hash SHA-256; las consultas expiran a los 30 días (TTL).
- **Aplicación**: validación de entrada y tamaño, CORS restringido al origen del sitio, el frontend inserta texto con `textContent` (previene XSS), los errores internos no exponen detalles (solo en logs).
- **Abuso**: throttling de API Gateway (5 rps) + límite por cliente de 30/min que también protege la URL de función.

### 6.2 Observabilidad
- **Logs**: una línea JSON por consulta (estado, score, latencia, origen) en `/aws/lambda/asistente-tecnohogar-fn`, retención 7 días. 📸 12.
- **Métricas personalizadas (EMF)**: Consultas, Respondidas, SinRespuesta, Sugerencias, Rechazadas, ScoreSimilitud, LatenciaMs. 📸 13 dashboard.
- **Alarmas**: más de 5 consultas sin respuesta en 15 min (indica documentación faltante) y errores de Lambda.
- 📸 14 Logs Insights con conteo por estado.

### 6.3 Costo
📸 15 Panel del Learner Lab: **"Used $[X] of $[50]"** con fecha.
Estimación: con tráfico de prueba (cientos de solicitudes) todos los servicios quedan dentro de capas gratuitas o en centavos: Lambda (1 M solicitudes gratis/mes), HTTP API (US$ 1 por millón), DynamoDB on-demand (centavos por millón de operaciones), S3 (centavos por GB). No hay recursos con costo por hora (sin EC2, RDS ni NAT).

---

## 7. Limitaciones y ruta alternativa (½ pág.) — *Documentación y defensa*

- **Servicios no habilitados**: Amazon Lex (chatbots conversacionales) y Amazon Bedrock (modelos de lenguaje) no están disponibles en el Learner Lab. Por eso la búsqueda se implementó algorítmicamente en Python (TF-IDF + coseno + Jaccard). Ventajas: costo nulo, resultado explicable (score visible) y sin riesgo de que el modelo "invente". Desventaja: comprensión solo léxica; sinónimos fuera del diccionario o preguntas muy indirectas pueden caer en *sugerencia*.
- **Ruta alternativa**: se creó la **URL de función de Lambda** (Auth NONE, dos declaraciones de permiso). Usa el mismo código porque el formato del evento es idéntico; el frontend conmuta automáticamente si API Gateway devuelve error. [Indicar si fue necesaria durante el desarrollo.] Como la URL no tiene throttling propio, el límite por cliente en DynamoDB la protege.
- **Qué haría distinto en producción**:
  - CloudFront + HTTPS + dominio propio delante de S3; AWS WAF ante la API.
  - Rol IAM propio de mínimo privilegio en lugar de LabRole.
  - Bedrock *Knowledge Bases* (RAG) o embeddings para búsqueda semántica, manteniendo el umbral y el registro.
  - Pipeline CI/CD (GitHub Actions + SAM/CDK) en vez de scripts.
  - Panel de administración autenticado (Cognito) para revisar consultas sin respuesta y editar la base.
  - Alarmas con notificación SNS al equipo.

---

## 8. Conclusiones y limpieza (½ pág.) — *Documentación y defensa*

### 8.1 Lecciones aprendidas
- Una arquitectura serverless resuelve el caso con costo casi nulo y sin administración, ideal para cargas bajas e intermitentes.
- Sin IA gestionada, un algoritmo clásico bien calibrado cumple la prueba de aceptación; el **umbral** y el **factor de cobertura** son lo que permite reconocer preguntas fuera de la documentación.
- Tener la ruta alternativa (URL de función) lista desde el inicio da resiliencia ante fallas del laboratorio.
- La observabilidad (métricas de consultas sin respuesta) convierte al asistente en una herramienta para mejorar la documentación.
- [Agregar una lección personal: un error que te costó resolver, p. ej. el 403 de la URL de función por la segunda declaración de permiso.]

### 8.2 Limpieza
`bash infra/cleanup.sh` eliminó: URL de función, HTTP API, Lambda, 3 tablas, 2 buckets (con sus versiones), dashboard, alarmas y grupo de logs. 📸 16 salida de verificación con listas vacías, o consolas de Lambda, DynamoDB y S3 vacías, con fecha. Finalmente **End Lab**.

---

## A. Anexos (libre)

- A.1 Código de `similitud.py` y `lambda_function.py` (o enlace a líneas del repositorio).
- A.2 `infra/politicas/bucket-policy-web.json` y `lambda-resource-policy-ejemplo.json`.
- A.3 Política de mínimo privilegio propuesta para producción:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": "dynamodb:Scan", "Resource": "arn:aws:dynamodb:us-east-1:CUENTA:table/asistente-tecnohogar-kb"},
      {"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "arn:aws:dynamodb:us-east-1:CUENTA:table/asistente-tecnohogar-consultas"},
      {"Effect": "Allow", "Action": "dynamodb:UpdateItem", "Resource": "arn:aws:dynamodb:us-east-1:CUENTA:table/asistente-tecnohogar-limites"},
      {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::asistente-tecnohogar-docs-CUENTA/kb/*"},
      {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:us-east-1:CUENTA:log-group:/aws/lambda/asistente-tecnohogar-fn:*"}
    ]
  }
  ```
- A.4 Tabla completa de resultados de la prueba de aceptación (`evidencias/*.md`).
- A.5 `infra/dashboard.json`.
- A.6 Capturas adicionales.

---

## Lista de verificación antes de subir
- [ ] Nombre del archivo correcto y un único PDF ≤ 12 páginas (sin anexos).
- [ ] Carátula con correo, reto, repositorio y video.
- [ ] Diagrama legible con justificación por servicio.
- [ ] Capturas con región y fecha visibles; ninguna muestra credenciales.
- [ ] Prueba de aceptación y caso de error documentados.
- [ ] Captura del consumo del Learner Lab.
- [ ] Repositorio con README, sin credenciales; docente con acceso.
- [ ] Video ≤ 5 min, con voz.
- [ ] Evidencia de limpieza.
