# Despliegue en Coolify

La app se despliega con el `Dockerfile` del repositorio.

## 1. Dar acceso al repositorio

El repositorio `jcgonzalez01/api_consulta` es **privado**. En Coolify:

- **Sources → + Add → GitHub App** y autoriza el acceso a `api_consulta`, o
- usa una **Deploy Key** (Coolify te da la clave pública; agrégala en GitHub →
  repo → Settings → Deploy keys, solo lectura).

## 2. Crear el recurso

1. **Projects → (tu proyecto) → + New → Application**.
2. Elige **Private Repository (with GitHub App)** (o *with Deploy Key*).
3. Repositorio: `jcgonzalez01/api_consulta`, rama: `main`.
4. **Build Pack: `Dockerfile`** (ubicación `/Dockerfile`).
5. **Ports Exposes: `8000`**.

## 3. Variables de entorno

En **Environment Variables**:

| Variable | Valor | Obligatoria |
|---|---|---|
| `API_KEY` | una clave larga y secreta | **Recomendada**: sin ella la API queda abierta en Internet |
| `CACHE_TTL` | `600` | No (segundos de caché) |

Generar una clave:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Marca `API_KEY` como **secret / no visible en build**.

## 4. Dominio y HTTPS

En **Domains** pon, por ejemplo, `https://api-dgii.tudominio.com`. Coolify (Traefik/Caddy)
genera el certificado SSL automáticamente. El DNS del dominio debe apuntar (registro A)
a la IP del servidor de Coolify.

## 5. Health check

El `Dockerfile` ya incluye un `HEALTHCHECK` contra `/health`. Si además lo configuras en
Coolify (**Health Checks**): path `/health`, puerto `8000`, método `GET`.

## 6. Desplegar

Pulsa **Deploy**. Para despliegue automático en cada `git push`, activa
**Auto Deploy** (con GitHub App viene activo por defecto).

## 7. Probar

```bash
curl https://api-dgii.tudominio.com/health
```

```bash
curl -H "X-API-Key: TU_CLAVE" https://api-dgii.tudominio.com/rnc/401-00755-1
```

La documentación queda en `https://api-dgii.tudominio.com/docs`. Para probar desde ahí,
pulsa **Authorize** y pega la clave.

## Notas

- **Una sola réplica / un worker:** la caché es en memoria; con varias réplicas cada una
  tiene su propia caché (funciona igual, solo cachea menos).
- **IP del servidor:** las consultas a la DGII salen desde la IP del servidor de Coolify.
  Si haces muchas consultas, la DGII podría bloquear esa IP.
- **Logs:** pestaña **Logs** del recurso en Coolify.
