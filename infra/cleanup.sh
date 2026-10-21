#!/usr/bin/env bash
# =============================================================================
# Elimina TODOS los recursos del proyecto (ejecutar al terminar la defensa).
#   bash infra/cleanup.sh          # pide confirmación
#   bash infra/cleanup.sh --si     # sin confirmación
# Al final lista lo que quede para usarlo como evidencia de limpieza.
# =============================================================================
set -uo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=config.env
source "$RAIZ/infra/config.env"
export AWS_DEFAULT_REGION="$AWS_REGION"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DOCS_BUCKET="${PROYECTO}-docs-${ACCOUNT_ID}"
WEB_BUCKET="${PROYECTO}-web-${ACCOUNT_ID}"

if [ "${1:-}" != "--si" ]; then
  read -r -p "Se eliminarán todos los recursos de '${PROYECTO}' en ${AWS_REGION}. ¿Continuar? (escribe si): " r
  [ "$r" = "si" ] || { echo "Cancelado."; exit 1; }
fi

echo "==> URL de función, API Gateway y Lambda"
aws lambda delete-function-url-config --function-name "$LAMBDA_NAME" 2>/dev/null && echo "    URL de función eliminada"
for id in $(aws apigatewayv2 get-apis --query "Items[?Name=='${API_NAME}'].ApiId" --output text 2>/dev/null); do
  aws apigatewayv2 delete-api --api-id "$id" && echo "    HTTP API $id eliminada"
done
aws lambda delete-function --function-name "$LAMBDA_NAME" 2>/dev/null && echo "    Lambda eliminada"

echo "==> DynamoDB"
for t in "$KB_TABLE" "$LOG_TABLE" "$RATE_TABLE"; do
  aws dynamodb delete-table --table-name "$t" >/dev/null 2>&1 && echo "    Tabla $t eliminada"
done

echo "==> S3 (vaciar, incluidas versiones, y borrar)"
vaciar_bucket() {
  local b="$1"
  aws s3api head-bucket --bucket "$b" >/dev/null 2>&1 || return 0
  # Borra objetos, versiones antiguas y marcadores de borrado (bucket versionado)
  python3 -c "import boto3, sys; boto3.resource('s3').Bucket(sys.argv[1]).object_versions.delete()" "$b"
  aws s3api delete-bucket --bucket "$b" && echo "    Bucket $b eliminado"
}
vaciar_bucket "$DOCS_BUCKET"
vaciar_bucket "$WEB_BUCKET"

echo "==> CloudWatch"
aws cloudwatch delete-dashboards --dashboard-names "$DASHBOARD_NAME" 2>/dev/null && echo "    Dashboard eliminado"
aws cloudwatch delete-alarms --alarm-names "${PROYECTO}-muchas-sin-respuesta" "${PROYECTO}-errores-lambda" 2>/dev/null \
  && echo "    Alarmas eliminadas"
aws logs delete-log-group --log-group-name "/aws/lambda/${LAMBDA_NAME}" 2>/dev/null && echo "    Grupo de logs eliminado"

rm -f "$RAIZ/infra/salidas.env"

echo
echo "==> Verificación (captura esta salida para /evidencias y la sección 8 del informe)"
date -u +"Fecha UTC: %Y-%m-%d %H:%M:%S"
echo "Región: ${AWS_REGION}"
echo "Lambdas restantes:   $(aws lambda list-functions --query "Functions[?starts_with(FunctionName, '${PROYECTO}')].FunctionName" --output text)"
echo "Tablas restantes:    $(aws dynamodb list-tables --query "TableNames[?starts_with(@, '${PROYECTO}')]" --output text)"
echo "Buckets restantes:   $(aws s3api list-buckets --query "Buckets[?starts_with(Name, '${PROYECTO}')].Name" --output text)"
echo "APIs restantes:      $(aws apigatewayv2 get-apis --query "Items[?Name=='${API_NAME}'].ApiId" --output text)"
echo "(Vacío = limpieza completa. Las tablas pueden figurar unos segundos en estado DELETING.)"
