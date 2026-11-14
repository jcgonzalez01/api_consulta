# API Consulta DGII (Cédula y RNC)

API REST en FastAPI que consulta las páginas públicas de la DGII:

- Cédula: `consultas/ciudadanos.aspx`
- RNC: `consultas/rnc.aspx`

Las páginas son ASP.NET WebForms. Para cada consulta, el cliente hace un GET para obtener
`__VIEWSTATE`/`__EVENTVALIDATION`, luego el POST con el número y parsea la tabla de resultados.

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Ejecutar

```bash
.venv/bin/uvicorn app.main:app --reload
```

Documentación interactiva: http://127.0.0.1:8000/docs

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/cedula/{numero}` | Cédula de 11 dígitos (acepta guiones) |
| GET | `/rnc/{numero}` | RNC de 9 dígitos o cédula de 11 |
| GET | `/rnc/buscar?nombre=...` | Búsqueda por nombre/razón social (mín. 4 caracteres) |

Ejemplo:

```bash
curl http://127.0.0.1:8000/rnc/401-00755-1
```

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
    "actividad_economica": "...",
    "administracion_local": "ADM LOCAL GGC",
    "facturador_electronico": "SI",
    "licencias_de_comercializacion_de_vhm": "N/A"
  }
}
```

Códigos: `401` falta la API key (si está activada), `422` formato inválido, `404` no encontrado, `502` la DGII no respondió.

## Clave de acceso (opcional)

Si defines la variable de entorno `API_KEY`, todas las consultas (excepto `/health`)
exigen el encabezado `X-API-Key`:

```bash
API_KEY=mi-clave .venv/bin/uvicorn app.main:app
curl -H "X-API-Key: mi-clave" http://127.0.0.1:8000/rnc/401007551
```

Sin la clave, la respuesta es `401`. Ver `.env.example`.

## Docker / Coolify

```bash
docker build -t api-consulta .
docker run -p 8000:8000 -e API_KEY=mi-clave api-consulta
```

Guía paso a paso para Coolify: [DESPLIEGUE_COOLIFY.md](DESPLIEGUE_COOLIFY.md).

## Notas

- Respuestas en caché 10 minutos (en memoria) para no saturar a la DGII.
- Si la DGII cambia los nombres de los campos del formulario, ajustar las constantes al
  inicio de `app/dgii_client.py`.
- Alternativa offline para RNC: el padrón `DGII_RNC.zip` publicado por la DGII.

## Pruebas

```bash
.venv/bin/python -m pytest -q
```
