#!/usr/bin/env bash
# =============================================================================
# Despliegue completo del Asistente de Atención al Cliente en AWS Learner Lab.
#
# Uso (recomendado desde AWS CloudShell, que ya tiene la sesión del lab):
#   git clone <tu-repo> && cd asistente-atencion-cliente
#   bash infra/deploy.sh
#
# Es idempotente: si un recurso ya existe, lo reutiliza o lo actualiza.
# No usa ni guarda credenciales: toma la sesión activa de AWS CLI y el rol LabRole.
# =============================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=config.env
source "$RAIZ/infra/config.env"
export AWS_DEFAULT_REGION="$AWS_REGION"

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32m✔\033[0m %s\n' "$*"; }

paso "0. Verificando sesión de AWS"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAB_ROLE_NAME}"
DOCS_BUCKET="${PROYECTO}-docs-${ACCOUNT_ID}"
WEB_BUCKET="${PROYECTO}-web-${ACCOUNT_ID}"
WEB_URL="http://${WEB_BUCKET}.s3-website-${AWS_REGION}.amazonaws.com"
ok "Cuenta ${ACCOUNT_ID} · región ${AWS_REGION} · rol ${ROLE_ARN}"

# ---------------------------------------------------------------------------- S3
crear_bucket() {
  local b="$1"
  if aws s3api head-bucket --bucket "$b" >/dev/null 2>&1; then
    ok "Bucket $b ya existe"
  else
    if [ "$AWS_REGION" = "us-east-1" ]; then
      aws s3api create-bucket --bucket "$b" >/dev/null
    else
      aws s3api create-bucket --bucket "$b" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
    fi
    ok "Bucket $b creado"
  fi
}

paso "1. Buckets S3"
crear_bucket "$DOCS_BUCKET"
aws s3api put-public-access-block --bucket "$DOCS_BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket "$DOCS_BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-versioning --bucket "$DOCS_BUCKET" --versioning-configuration Status=Enabled
ok "Bucket de documentos privado, cifrado (SSE-S3) y con versionado"

crear_bucket "$WEB_BUCKET"
aws s3api put-public-access-block --bucket "$WEB_BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3api put-bucket-website --bucket "$WEB_BUCKET" \
  --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'
sed "s/__WEB_BUCKET__/${WEB_BUCKET}/g" "$RAIZ/infra/politicas/bucket-policy-web.json" > /tmp/politica-web.json
aws s3api put-bucket-policy --bucket "$WEB_BUCKET" --policy file:///tmp/politica-web.json
ok "Bucket web con hosting estático y lectura pública solo de objetos (s3:GetObject)"

# ---------------------------------------------------------------------- DynamoDB
crear_tabla() {
  local t="$1" k="$2"
  if aws dynamodb describe-table --table-name "$t" >/dev/null 2>&1; then
    ok "Tabla $t ya existe"
  else
    aws dynamodb create-table --table-name "$t" --billing-mode PAY_PER_REQUEST \
      --attribute-definitions AttributeName="$k",AttributeType=S \
      --key-schema AttributeName="$k",KeyType=HASH \
      --tags Key=Proyecto,Value="$PROYECTO" >/dev/null
    aws dynamodb wait table-exists --table-name "$t"
    ok "Tabla $t creada (on-demand, clave $k)"
  fi
}
activar_ttl() {
  local estado
  estado=$(aws dynamodb describe-time-to-live --table-name "$1" \
    --query 'TimeToLiveDescription.TimeToLiveStatus' --output text)
  if [ "$estado" != "ENABLED" ] && [ "$estado" != "ENABLING" ]; then
    aws dynamodb update-time-to-live --table-name "$1" \
      --time-to-live-specification Enabled=true,AttributeName=expira >/dev/null
  fi
  ok "TTL activo en $1 (atributo expira)"
}

paso "2. Tablas DynamoDB"
crear_tabla "$KB_TABLE" id
crear_tabla "$LOG_TABLE" consulta_id
crear_tabla "$RATE_TABLE" clave
activar_ttl "$LOG_TABLE"
activar_ttl "$RATE_TABLE"

paso "3. Documentación autorizada → S3 y base de conocimiento → DynamoDB"
aws s3 sync "$RAIZ/data/documentos" "s3://${DOCS_BUCKET}/documentos/" --delete --only-show-errors
aws s3 cp "$RAIZ/data/base_conocimiento.json" "s3://${DOCS_BUCKET}/kb/base_conocimiento.json" --only-show-errors
python3 "$RAIZ/scripts/cargar_base_conocimiento.py" --tabla "$KB_TABLE" --region "$AWS_REGION" \
  --archivo "$RAIZ/data/base_conocimiento.json"

# ------------------------------------------------------------------------ Lambda
paso "4. Función Lambda"
ZIP="/tmp/${LAMBDA_NAME}.zip"
rm -f "$ZIP"
(cd "$RAIZ/src/asistente" && zip -q -r "$ZIP" ./*.py)
ok "Paquete $(du -h "$ZIP" | cut -f1) generado (solo biblioteca estándar + boto3 del runtime)"

ENV_VARS="Variables={KB_SOURCE=dynamodb,KB_TABLE=${KB_TABLE},LOG_TABLE=${LOG_TABLE},RATE_TABLE=${RATE_TABLE},DOCS_BUCKET=${DOCS_BUCKET},KB_S3_KEY=kb/base_conocimiento.json,UMBRAL_RESPUESTA=${UMBRAL_RESPUESTA},UMBRAL_SUGERENCIA=${UMBRAL_SUGERENCIA},LIMITE_POR_MINUTO=${LIMITE_POR_MINUTO},MAX_CARACTERES=${MAX_CARACTERES},LOG_TTL_DIAS=${LOG_TTL_DIAS},METRIC_NAMESPACE=${METRIC_NAMESPACE},ALLOWED_ORIGIN=${WEB_URL},KB_CACHE_SEGUNDOS=300,DEBUG_SIMILITUD=false}"

if aws lambda get-function --function-name "$LAMBDA_NAME" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$LAMBDA_NAME" --zip-file "fileb://$ZIP" >/dev/null
  aws lambda wait function-updated --function-name "$LAMBDA_NAME"
  aws lambda update-function-configuration --function-name "$LAMBDA_NAME" \
    --environment "$ENV_VARS" --timeout 10 --memory-size 256 >/dev/null
  aws lambda wait function-updated --function-name "$LAMBDA_NAME"
  ok "Lambda $LAMBDA_NAME actualizada"
else
  aws lambda create-function --function-name "$LAMBDA_NAME" \
    --runtime python3.12 --handler lambda_function.lambda_handler \
    --role "$ROLE_ARN" --zip-file "fileb://$ZIP" \
    --timeout 10 --memory-size 256 --environment "$ENV_VARS" \
    --tags Proyecto="$PROYECTO" >/dev/null
  aws lambda wait function-active-v2 --function-name "$LAMBDA_NAME"
  ok "Lambda $LAMBDA_NAME creada con LabRole (python3.12, 256 MB, 10 s)"
fi
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_NAME" --query Configuration.FunctionArn --output text)

paso "5. CloudWatch Logs"
LOG_GROUP="/aws/lambda/${LAMBDA_NAME}"
aws logs create-log-group --log-group-name "$LOG_GROUP" 2>/dev/null || true
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days "$LOG_RETENCION_DIAS"
ok "Grupo $LOG_GROUP con retención de ${LOG_RETENCION_DIAS} días"

# ------------------------------------------------------------------ API Gateway
agregar_permiso() {  # ignora el error si el permiso ya existe
  aws lambda add-permission --function-name "$LAMBDA_NAME" "$@" >/dev/null 2>&1 || true
}

paso "6. API Gateway (HTTP API) — ruta principal"
API_URL=""
set +e
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text 2>/dev/null)
if [ -z "$API_ID" ] || [ "$API_ID" = "None" ]; then
  API_ID=$(aws apigatewayv2 create-api --name "$API_NAME" --protocol-type HTTP \
    --target "$LAMBDA_ARN" --query ApiId --output text)
fi
set -e
if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
  agregar_permiso --statement-id apigw-invoke --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*"
  if ! aws apigatewayv2 update-stage --api-id "$API_ID" --stage-name '$default' \
      --default-route-settings "ThrottlingBurstLimit=${API_BURST_LIMIT},ThrottlingRateLimit=${API_RATE_LIMIT}" \
      --cli-read-timeout 20 >/dev/null 2>&1; then
    echo "    ⚠ No se pudo aplicar el throttling; configúralo en la consola (docs/guia_consola_aws.md §4 paso 6)."
  else
    ok "Throttling de la etapa \$default: ${API_RATE_LIMIT} rps / ráfaga ${API_BURST_LIMIT}"
  fi
  API_URL=$(aws apigatewayv2 get-api --api-id "$API_ID" --query ApiEndpoint --output text)
  ok "HTTP API ${API_ID}: ${API_URL}"
else
  echo "    ⚠ No se pudo crear la HTTP API. Se usará solo la URL de función (ruta alternativa)."
fi

paso "7. URL de función de Lambda — ruta alternativa"
FN_URL=$(aws lambda get-function-url-config --function-name "$LAMBDA_NAME" --query FunctionUrl --output text 2>/dev/null || true)
if [ -z "$FN_URL" ] || [ "$FN_URL" = "None" ]; then
  FN_URL=$(aws lambda create-function-url-config --function-name "$LAMBDA_NAME" \
    --auth-type NONE --query FunctionUrl --output text)
fi
FN_URL="${FN_URL%/}"
# Desde oct-2025 una URL pública requiere DOS declaraciones en la política de recursos.
agregar_permiso --statement-id url-invoke-url --action lambda:InvokeFunctionUrl \
  --principal '*' --function-url-auth-type NONE
if ! aws lambda add-permission --function-name "$LAMBDA_NAME" --statement-id url-invoke-function \
     --action lambda:InvokeFunction --principal '*' --invoked-via-function-url >/dev/null 2>&1; then
  aws lambda get-policy --function-name "$LAMBDA_NAME" --output text 2>/dev/null | grep -q url-invoke-function \
    || echo "    ⚠ Tu AWS CLI no soporta --invoked-via-function-url. Si la URL responde 403, agrega el permiso desde la consola (ver docs/guia_consola_aws.md §5.2)."
fi
ok "URL de función: ${FN_URL}"

# --------------------------------------------------------------------- Frontend
paso "8. Frontend estático → S3"
PRINCIPAL="${API_URL:-$FN_URL}"
cat > "$RAIZ/frontend/config.js" <<EOF
// Generado por infra/deploy.sh — no contiene secretos, solo URLs públicas.
window.ASISTENTE_CONFIG = {
  apiUrl: "${PRINCIPAL}/preguntar",
  fallbackUrl: "${FN_URL}/preguntar"
};
EOF
aws s3 sync "$RAIZ/frontend" "s3://${WEB_BUCKET}/" --delete --only-show-errors \
  --exclude "config.example.js" --cache-control "no-cache"
ok "Sitio publicado: ${WEB_URL}"

# ------------------------------------------------------------ CloudWatch extras
paso "9. Dashboard y alarmas de CloudWatch"
sed -e "s/__REGION__/${AWS_REGION}/g" -e "s/__NAMESPACE__/${METRIC_NAMESPACE}/g" \
    -e "s/__LAMBDA__/${LAMBDA_NAME}/g" "$RAIZ/infra/dashboard.json" > /tmp/dashboard.json
aws cloudwatch put-dashboard --dashboard-name "$DASHBOARD_NAME" --dashboard-body file:///tmp/dashboard.json >/dev/null
aws cloudwatch put-metric-alarm --alarm-name "${PROYECTO}-muchas-sin-respuesta" \
  --alarm-description "Más de 5 consultas sin respuesta en 15 min: ampliar la documentación" \
  --namespace "$METRIC_NAMESPACE" --metric-name SinRespuesta --dimensions Name=Servicio,Value=asistente \
  --statistic Sum --period 900 --evaluation-periods 1 --threshold 5 \
  --comparison-operator GreaterThanThreshold --treat-missing-data notBreaching
aws cloudwatch put-metric-alarm --alarm-name "${PROYECTO}-errores-lambda" \
  --alarm-description "La función Lambda registró errores" \
  --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value="$LAMBDA_NAME" \
  --statistic Sum --period 300 --evaluation-periods 1 --threshold 0 \
  --comparison-operator GreaterThanThreshold --treat-missing-data notBreaching
ok "Dashboard ${DASHBOARD_NAME} y 2 alarmas creadas"

# ---------------------------------------------------------------------- Salidas
cat > "$RAIZ/infra/salidas.env" <<EOF
ACCOUNT_ID=${ACCOUNT_ID}
DOCS_BUCKET=${DOCS_BUCKET}
WEB_BUCKET=${WEB_BUCKET}
WEB_URL=${WEB_URL}
API_ID=${API_ID:-}
API_URL=${API_URL}
FN_URL=${FN_URL}
EOF

paso "Listo ✅"
cat <<EOF
    Frontend:          ${WEB_URL}
    API Gateway:       ${API_URL:-"(no disponible)"}/preguntar
    URL de función:    ${FN_URL}/preguntar
    Dashboard:         https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards/dashboard/${DASHBOARD_NAME}

    Prueba de aceptación:
      python3 scripts/prueba_aceptacion.py --url ${PRINCIPAL}
      python3 scripts/prueba_aceptacion.py --url ${FN_URL}     # ruta alternativa
EOF
