// Copia este archivo como config.js y reemplaza las URLs (infra/deploy.sh lo hace solo).
// Solo contiene URLs públicas de endpoints: NO pongas claves ni tokens aquí.
window.ASISTENTE_CONFIG = {
  apiUrl: "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/preguntar",
  fallbackUrl: "https://XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.lambda-url.us-east-1.on.aws/preguntar"
};
