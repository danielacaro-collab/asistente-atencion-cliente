// Cliente del asistente. Usa API Gateway como ruta principal y, si falla
// (error de red, 403 o 5xx), reintenta automáticamente con la URL de función de Lambda.
(function () {
  "use strict";
  const cfg = window.ASISTENTE_CONFIG || {};
  const chat = document.getElementById("chat");
  const form = document.getElementById("formulario");
  const input = document.getElementById("pregunta");
  const boton = document.getElementById("enviar");
  const ruta = document.getElementById("ruta");

  if (!cfg.apiUrl) {
    agregarBot({ estado: "error", respuesta: "Falta config.js. Ejecuta infra/deploy.sh o copia config.example.js." });
  }

  // Solo textContent: nunca se inserta HTML proveniente del usuario o de la API (evita XSS).
  function nodo(tag, clase, texto) {
    const el = document.createElement(tag);
    if (clase) el.className = clase;
    if (texto) el.textContent = texto;
    return el;
  }

  function agregarUsuario(texto) {
    const m = nodo("div", "msg usuario");
    m.appendChild(nodo("p", null, texto));
    chat.appendChild(m);
    chat.scrollTop = chat.scrollHeight;
  }

  function agregarBot(d) {
    const m = nodo("div", "msg bot " + (d.estado || ""));
    if (d.estado === "sin_respuesta") m.appendChild(nodo("span", "etiqueta", "No documentado"));
    if (d.estado === "sugerencia") m.appendChild(nodo("span", "etiqueta", "Sin certeza"));
    m.appendChild(nodo("p", null, d.respuesta || d.error || "Sin respuesta."));
    if (typeof d.score === "number") {
      const extra = d.fuente ? " · fuente: " + d.fuente : "";
      m.appendChild(nodo("p", "meta", "similitud " + d.score.toFixed(3) + " · " + d.estado + extra));
    }
    chat.appendChild(m);
    chat.scrollTop = chat.scrollHeight;
  }

  async function llamar(url, pregunta) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: pregunta })
    });
    const datos = await r.json().catch(function () { return {}; });
    return { status: r.status, datos: datos };
  }

  async function preguntar(pregunta) {
    agregarUsuario(pregunta);
    boton.disabled = true;
    try {
      let res, usada = "API Gateway";
      try {
        res = await llamar(cfg.apiUrl, pregunta);
        if ((res.status === 403 || res.status >= 500) && cfg.fallbackUrl && cfg.fallbackUrl !== cfg.apiUrl) {
          throw new Error("API Gateway respondió " + res.status);
        }
      } catch (e) {
        if (!cfg.fallbackUrl || cfg.fallbackUrl === cfg.apiUrl) throw e;
        console.warn("Usando ruta alternativa (URL de función):", e.message);
        res = await llamar(cfg.fallbackUrl, pregunta);
        usada = "Lambda URL";
      }
      if (cfg.apiUrl.indexOf(".lambda-url.") !== -1) usada = "Lambda URL";
      ruta.textContent = usada;
      if (res.status === 200) agregarBot(res.datos);
      else agregarBot({ estado: "error", respuesta: res.datos.error || ("Error HTTP " + res.status) });
    } catch (e) {
      agregarBot({ estado: "error", respuesta: "No se pudo contactar al asistente. Revisa tu conexión." });
    } finally {
      boton.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    const p = input.value.trim();
    if (!p) return;
    input.value = "";
    preguntar(p);
  });

  document.querySelectorAll("#sugeridas button").forEach(function (b) {
    b.addEventListener("click", function () { preguntar(b.textContent); });
  });
})();
