# Despliegue en Coolify

La app se despliega con el `Dockerfile` del repositorio.

**Instancia actual:** `https://api-consulta.kaisoftrd.com` (servidor `37.60.234.15`).

> ⚠️ **No uses guion bajo (`_`) en el dominio.** Let's Encrypt no emite certificados para
> nombres como `api_consulta.kaisoftrd.com`; Traefik muestra entonces `TRAEFIK DEFAULT CERT`
> y `curl` falla con *"no alternative certificate subject name matches"*. Usa guion: `api-consulta`.

---

## 1. Conectar GitHub (solo la primera vez)

El repositorio `jcgonzalez01/api_consulta` es **privado**.

1. **Sources → + Add → GitHub App**, ponle un nombre y pulsa **Register now**.
2. En GitHub: autoriza la app → **Repository access → Only select repositories** → `api_consulta`.
3. Vuelve a Coolify y verifica que la fuente aparezca conectada.

(Alternativa: **Deploy Key** — Coolify te da la clave pública; agrégala en GitHub →
repo → Settings → Deploy keys, solo lectura.)

## 2. Crear la aplicación

1. **Projects → (tu proyecto) → production → + New**.
2. **Private Repository (with GitHub App)** → elige la app del paso 1.
3. Repositorio: `jcgonzalez01/api_consulta`, rama: `main`.
4. **Build Pack: `Dockerfile`** (no Nixpacks).
5. **Ports Exposes: `8000`**.
6. **Continue**.

## 3. Variables de entorno

Pestaña **Environment Variables**:

| Variable | Valor | Obligatoria |
|---|---|---|
| `API_KEY` | clave larga y secreta | **Sí** en Internet: sin ella cualquiera puede consultar |
| `CACHE_TTL` | `600` | No (segundos de caché) |

Generar una clave:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Guárdala en un lugar seguro: la necesitas para consultar. **No la subas al repositorio.**

## 4. Dominio y HTTPS

1. **DNS** (en el proveedor de `kaisoftrd.com`): registro **A**

   | Tipo | Nombre | Valor |
   |---|---|---|
   | A | `api-consulta` | `37.60.234.15` |

2. **Coolify → Configuration → General → Domains**:

   ```
   https://api-consulta.kaisoftrd.com
   ```

3. **Save** → **Redeploy**. El certificado de Let's Encrypt se genera en 1–2 minutos.

Comprobar que el DNS ya apunta bien:

```bash
getent hosts api-consulta.kaisoftrd.com
```

Debe mostrar `37.60.234.15`.

## 5. Health check (opcional)

El `Dockerfile` ya incluye un `HEALTHCHECK` contra `/health`. Si además lo configuras en
Coolify (**Health Checks**): path `/health`, puerto `8000`.

## 6. Desplegar

1. **Deploy** (arriba a la derecha).
2. Sigue el progreso en **Deployments / Logs**. Al final debe aparecer
   `Uvicorn running on http://0.0.0.0:8000`.
3. Despliegue automático en cada `git push`: **Configuration → Advanced → Auto Deploy**.

## 7. Probar

```bash
curl https://api-consulta.kaisoftrd.com/health
```

Respuesta esperada: `{"status":"ok"}`

```bash
curl -H "X-API-Key: TU_CLAVE" https://api-consulta.kaisoftrd.com/rnc/401-00755-1
```

Sin el encabezado `X-API-Key` la respuesta es `401` (eso confirma que la clave está activa).

Documentación interactiva: `https://api-consulta.kaisoftrd.com/docs` → botón **Authorize**
→ pega la clave.

Verificar el certificado:

```bash
echo | openssl s_client -connect api-consulta.kaisoftrd.com:443 -servername api-consulta.kaisoftrd.com 2>/dev/null | openssl x509 -noout -subject -issuer
```

Debe mostrar un emisor de **Let's Encrypt**, no `TRAEFIK DEFAULT CERT`.

---

## Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `curl: (60) SSL: no alternative certificate subject name matches` | Dominio con `_`, o el certificado aún no se emitió | Usa `-` en el dominio (sección 4); espera 1–2 min y redeploy |
| Certificado `TRAEFIK DEFAULT CERT` | Let's Encrypt no pudo emitir | DNS no apunta a `37.60.234.15`, dominio con `_`, o puertos 80/443 cerrados en el servidor |
| `Could not resolve host` | Falta el registro DNS o aún no propaga | Crea el registro A; comprueba con `getent hosts` |
| "Repository not found" al crear | La GitHub App no tiene acceso a `api_consulta` | Sección 1, paso 2 |
| Build falla buscando Nixpacks | Build Pack incorrecto | Cambia a **Dockerfile** |
| `502` / "no available server" | Puerto mal configurado o contenedor arrancando | Ports Exposes = `8000`; revisa **Logs** |
| Siempre `401` | Falta `X-API-Key` o no coincide con `API_KEY` | Revisa la clave en Environment Variables |
| Siempre `502` en consultas | El servidor no llega a la DGII | Revisa salida a Internet del servidor; la DGII pudo bloquear la IP |

Prueba rápida ignorando el certificado (solo diagnóstico, nunca en producción):

```bash
curl -k https://api-consulta.kaisoftrd.com/health
```

---

## Notas

- **Una réplica / un worker:** la caché es en memoria; con varias réplicas cada una tiene
  la suya (funciona igual, solo cachea menos).
- **IP de salida:** las consultas a la DGII salen desde `37.60.234.15`. Evita consultas
  masivas para que no la bloqueen.
- **Logs:** pestaña **Logs** del recurso en Coolify.
