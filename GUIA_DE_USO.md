# Guía de uso — API Consulta DGII

API para consultar **cédulas** y **RNC** en la DGII (República Dominicana) y recibir la
respuesta en JSON. Funciona como intermediario: recibe tu consulta, la hace en la página
pública de la DGII y te devuelve los datos limpios.

---

## 1. Iniciar la API

Abre una terminal y ejecuta:

```bash
cd ~/api_consulta
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verás algo como `Uvicorn running on http://0.0.0.0:8000`. Deja esa terminal abierta
mientras uses la API.

| Modo | Comando | Quién puede usarla |
|---|---|---|
| Solo este equipo | `.venv/bin/uvicorn app.main:app --port 8000` | Solo tú, en `127.0.0.1` |
| En la red | `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` | Cualquier equipo de tu red |
| Desarrollo | agrega `--reload` | Se reinicia sola al editar el código |

**Detenerla:** presiona `Ctrl + C` en la terminal donde corre.

---

## 2. Direcciones

| Desde | URL base |
|---|---|
| Este mismo equipo | `http://127.0.0.1:8000` |
| Otro equipo en el mismo Wi-Fi/red | `http://192.168.1.26:8000` |
| Por Tailscale | `http://100.123.107.9:8000` |

> La IP de red puede cambiar si el router asigna otra. Para verla: `hostname -I`

**Documentación interactiva:** abre `http://<IP>:8000/docs` en el navegador. Ahí puedes
probar cada consulta con el botón **Try it out** sin escribir código.

---

## 3. Consultas disponibles

### Consultar cédula

```
GET /cedula/{numero}
```

- 11 dígitos, con o sin guiones: `00100000001` o `001-0000000-1`.

Respuesta (ejemplo con datos ficticios):

```json
{
  "cedula": "00100000001",
  "datos": {
    "nombre": "PERSONA DE PRUEBA",
    "estado": "ACTIVO",
    "tipo": "FISICO",
    "rnc_o_cedula": "001-0000000-1",
    "marca": "Participacion en Empresas"
  }
}
```

> La DGII solo muestra cédulas **inscritas en el RNC** (propietarios de vehículos/inmuebles,
> empleados, participación en empresas, etc.). Una cédula válida pero no inscrita devuelve 404.

### Consultar RNC

```
GET /rnc/{numero}
```

- 9 dígitos (empresas) u 11 (personas físicas), con o sin guiones.

```json
{
  "rnc": "401007551",
  "datos": {
    "cedula_rnc": "401-00755-1",
    "nombre_razon_social": "BANCO CENTRAL DE LA REPUBLICA DOMINICANA",
    "nombre_comercial": "",
    "categoria": "",
    "regimen_de_pagos": "NORMAL",
    "estado": "ACTIVO",
    "actividad_economica": "SERV GRALES DE LA ADM PÚBLICA ...",
    "administracion_local": "ADM LOCAL GGC",
    "facturador_electronico": "SI",
    "licencias_de_comercializacion_de_vhm": "N/A"
  }
}
```

### Buscar por nombre o razón social

```
GET /rnc/buscar?nombre={texto}
```

- Mínimo 4 caracteres. Devuelve una lista.

```json
{
  "nombre": "BANCO CENTRAL",
  "total": 1,
  "resultados": [
    { "cedula_rnc": "401-00755-1", "nombre_razon_social": "BANCO CENTRAL DE LA REPUBLICA DOMINICANA", "estado": "ACTIVO", "...": "..." }
  ]
}
```

### Estado del servicio

```
GET /health   →   {"status": "ok"}
```

---

## 4. Códigos de respuesta

| Código | Significado | Qué hacer |
|---|---|---|
| `200` | Encontrado | Leer el campo `datos` |
| `404` | No inscrito en la DGII | Verificar el número |
| `422` | Formato inválido (dígitos de más/menos, letras) | Corregir el número |
| `502` | La DGII no respondió | Reintentar en unos minutos |

Los errores vienen así: `{"detail": "La cédula debe tener 11 dígitos."}`

> Excepción: en `/rnc/buscar`, si `nombre` tiene menos de 4 caracteres, `detail` es una
> **lista** con el detalle de validación (formato estándar de FastAPI), no un texto.

---

## 5. Ejemplos de uso

Reemplaza `127.0.0.1` por `192.168.1.26` si consultas desde otro equipo.

### Navegador

```
http://127.0.0.1:8000/rnc/401-00755-1
```

### curl (terminal)

```bash
curl http://127.0.0.1:8000/rnc/401-00755-1
```

```bash
curl "http://127.0.0.1:8000/rnc/buscar?nombre=BANCO%20CENTRAL"
```

### Python

Requiere la librería `requests` (`pip install requests`).

```python
import requests

r = requests.get("http://127.0.0.1:8000/rnc/401007551", timeout=30)
if r.status_code == 200:
    datos = r.json()["datos"]
    print(datos["nombre_razon_social"], "-", datos["estado"])
elif r.status_code == 404:
    print("No inscrito")
else:
    print("Error:", r.json()["detail"])
```

### JavaScript

```javascript
const r = await fetch("http://127.0.0.1:8000/cedula/00100000001");
if (r.ok) {
  const { datos } = await r.json();
  console.log(datos.nombre, datos.estado);
} else {
  console.log((await r.json()).detail);
}
```

### Excel / Google Sheets (Power Query)

En Excel: **Datos → Obtener datos → Desde la web** y pega la URL, por ejemplo
`http://192.168.1.26:8000/rnc/401007551`. Excel convertirá el JSON en tabla.

---

## 6. Usar desde otros equipos de la red

1. Inicia la API en modo red (`--host 0.0.0.0`).
2. Desde el otro equipo abre `http://192.168.1.26:8000/health`. Si ves `{"status":"ok"}`, funciona.
3. Si no carga, abre el puerto en el firewall:

   ```bash
   sudo ufw allow 8000/tcp
   ```

4. Ambos equipos deben estar en la misma red (o los dos en Tailscale).

---

## 7. Comportamiento y límites

- **Caché:** cada consulta se guarda 10 minutos en memoria. Repetir la misma consulta en
  ese tiempo es instantáneo y no vuelve a llamar a la DGII. Se borra al reiniciar la API.
- **Velocidad:** una consulta nueva tarda ~1–2 segundos (depende de la DGII).
- **Reintento:** si la DGII falla, se reintenta una vez antes de devolver `502`.
- **Uso responsable:** no hagas consultas masivas; la DGII puede bloquear la IP. Para
  procesar miles de RNC, usa el padrón oficial descargable `DGII_RNC.zip`.

---

## 8. Seguridad

- La API **no tiene usuario ni clave**. Mientras corre en modo red, cualquiera en tu red
  (o en tu Tailscale) puede consultar.
- Los datos de cédula son información personal: no la expongas a Internet sin agregar
  autenticación.
- Si solo la usas tú, inicia sin `--host 0.0.0.0`.

---

## 9. Problemas frecuentes

| Problema | Solución |
|---|---|
| `Address already in use` | Ya hay una API corriendo. Ciérrala o usa otro puerto: `--port 8001` |
| `No such file .venv/bin/uvicorn` | Reinstala: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| Otro equipo no conecta | Revisa firewall (sección 6) y que la IP sea la correcta (`hostname -I`) |
| Siempre `502` | Revisa tu conexión a Internet o si el sitio de la DGII está caído |
| Campos vacíos o raros | La DGII pudo cambiar su página; ajusta las constantes en `app/dgii_client.py` |

---

## 10. Pruebas

```bash
cd ~/api_consulta
.venv/bin/python -m pytest -q
```
