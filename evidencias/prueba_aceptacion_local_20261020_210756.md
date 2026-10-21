# Prueba de aceptación — local

- Fecha: 2026-10-20T21:07:56
- Destino: `local`
- **Resultado: 25/25 aprobados**
- Preguntas con respuesta en la documentación: 14/14
- Preguntas fuera de la documentación reconocidas: 8/8
- Latencia media (cliente): 1 ms

| Caso | Pregunta | Esperado | Obtenido | Estado | Score | OK |
|---|---|---|---|---|---|---|
| A01 | Compré una licuadora hace 3 días, ¿todavía la puedo devolver? | DEV-001 | DEV-001 | respondida | 0.4539 | ✅ |
| A02 | ¿en cuanto tiempo me reembolsan la plata? | DEV-002 | DEV-002 | respondida | 0.6587 | ✅ |
| A03 | ¿Cuántos meses de garantía tiene una laptop? | GAR-001 | GAR-001 | respondida | 0.7803 | ✅ |
| A04 | Se me mojó el celular, ¿lo cubre la garantía? | GAR-002 | GAR-002 | respondida | 0.5853 | ✅ |
| A05 | ¿A qué hora cierran los sábados? | HOR-001 | HOR-001 | respondida | 0.7482 | ✅ |
| A06 | ¿Cuál es la dirección de la sucursal de Equipetrol? | SUC-001 | SUC-001 | respondida | 0.7434 | ✅ |
| A07 | ¿Aceptan pagos con QR? | PAG-001 | PAG-001 | respondida | 0.7131 | ✅ |
| A08 | ¿Puedo comprar una lavadora en 12 cuotas sin interes? | PAG-002 | PAG-002 | respondida | 0.473 | ✅ |
| A09 | ¿El delivery es gratis dentro de Santa Cruz? | ENV-001 | ENV-001 | respondida | 0.6336 | ✅ |
| A10 | ¿Mandan productos a Cochabamba? | ENV-002 | ENV-002 | respondida | 0.5515 | ✅ |
| A11 | ¿Como presento una queja por mal servicio? | REC-001 | REC-001 | respondida | 0.5204 | ✅ |
| A12 | Necesito la factura con mi NIT | FAC-001 | FAC-001 | respondida | 0.7311 | ✅ |
| A13 | ¿Cual es el numero de whatsapp de atencion? | CON-001 | CON-001 | respondida | 0.801 | ✅ |
| A14 | garantia extendida cuanto cuesta | GAR-004 | GAR-004 | respondida | 0.9016 | ✅ |
| B01 | ¿Tienen vacantes de trabajo disponibles? | — (no documentado) | — | sin_respuesta | 0.0103 | ✅ |
| B02 | ¿Venden repuestos para motocicletas? | — (no documentado) | — | sin_respuesta | 0.2164 | ✅ |
| B03 | ¿Quién ganó el partido de fútbol ayer? | — (no documentado) | — | sin_respuesta | 0.0098 | ✅ |
| B04 | ¿Cuál es la contraseña del wifi de la tienda? | — (no documentado) | — | sugerencia | 0.2804 | ✅ |
| B05 | ¿Organizan cursos de cocina para niños? | — (no documentado) | — | sin_respuesta | 0.0074 | ✅ |
| B06 | ¿Cuál es el precio del dólar hoy? | — (no documentado) | — | sin_respuesta | 0.1952 | ✅ |
| B07 | ¿Aceptan mascotas dentro del local? | — (no documentado) | — | sugerencia | 0.2346 | ✅ |
| B08 | ¿Quién es el gerente general de la empresa? | — (no documentado) | — | sin_respuesta | 0.0193 | ✅ |

## Casos de error

| Caso | Descripción | HTTP esperado | HTTP obtenido | Mensaje | OK |
|---|---|---|---|---|---|
| E01 | Pregunta vacía | 400 | 400 | El campo 'pregunta' es obligatorio. | ✅ |
| E02 | JSON inválido | 400 | 400 | El cuerpo debe ser JSON válido: {"pregunta": "..."} | ✅ |
| E03 | Pregunta demasiado larga (> 500 caracteres) | 413 | 413 | La pregunta supera el máximo de 500 caracteres. | ✅ |
