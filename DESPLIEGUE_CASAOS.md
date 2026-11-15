# Despliegue en CasaOS (servidor local en RD)

La API debe correr desde una conexión **en República Dominicana**: la DGII deja abrir
sus páginas desde servidores en el extranjero (Coolify/Contabo, Francia) pero **no
responde las búsquedas**. Desde una conexión dominicana responde en menos de 1 segundo.

Esquema:

```
KaiCredit (Coolify) ──HTTPS──> api-consulta.kaisoftrd.com ──Cloudflare Tunnel──> CasaOS (RD) ──> DGII
```

El túnel sale desde el servidor CasaOS hacia Cloudflare, así que **no hay que abrir
puertos en el router** ni tener IP fija.

---

## 1. La imagen Docker

Cada push a `main` publica la imagen con GitHub Actions
(`.github/workflows/docker.yml`) en:

```
ghcr.io/jcgonzalez01/api_consulta:latest     (amd64 + arm64)
```

El repositorio es privado, así que el paquete también nace privado. Una sola vez:

- **Opción A (recomendada):** GitHub → perfil → **Packages** → `api_consulta` →
  **Package settings** → **Change visibility** → **Public**. La imagen no contiene
  claves (la `API_KEY` va en las variables del contenedor).
- **Opción B:** dejarlo privado e iniciar sesión en el servidor CasaOS (por SSH):

  ```bash
  echo TOKEN_CON_read:packages | sudo docker login ghcr.io -u jcgonzalez01 --password-stdin
  ```

## 2. Crear el Cloudflare Tunnel

1. [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → **Networks** →
   **Tunnels** → **Create a tunnel** → **Cloudflared** → nombre `api-consulta`.
2. En "Install and run a connector" elija **Docker** y copie **solo el token**
   (el texto largo después de `--token`).
3. **Public Hostname**:
   - Subdomain: `api-consulta` · Domain: `kaisoftrd.com`
   - Service: **HTTP** · URL: `api-consulta:8000`
4. Si ya existe un registro DNS `api-consulta` apuntando a Coolify, Cloudflare pedirá
   reemplazarlo: acepte (o bórrelo antes en **DNS → Records**).

> El dominio `kaisoftrd.com` debe estar administrado en Cloudflare.

## 3. Instalar en CasaOS

1. CasaOS → **App Store** → botón **+** (arriba a la derecha) →
   **Install a customized app** → **Import**.
2. Pegue el contenido de [`casaos/docker-compose.yml`](casaos/docker-compose.yml).
3. Cambie:
   - `API_KEY` (servicio api-consulta): la **misma** clave que tiene KaiCredit en
     `API_CONSULTA_KEY`.
   - `TUNNEL_TOKEN` (servicio cloudflared): el token del paso 2.
4. **Install**.

## 4. Probar

En la red local (cambie la IP por la del servidor CasaOS):

```bash
curl http://IP-CASAOS:8000/health
curl -H "X-API-Key: SU-CLAVE" http://IP-CASAOS:8000/cedula/00117123778
```

Por Internet (desde cualquier lugar):

```bash
curl -H "X-API-Key: SU-CLAVE" https://api-consulta.kaisoftrd.com/cedula/00117123778
```

Debe devolver el nombre en 1–2 segundos. En el túnel de Cloudflare el estado debe
quedar **HEALTHY**.

Cuando funcione, apague la app api-consulta en Coolify para que no haya dos
apuntando al mismo dominio.

## 5. Actualizar

Al hacer push a `main`, GitHub publica la imagen nueva. En CasaOS: abra la app →
**⋮** → **Check then update** (o por SSH: `sudo docker pull ghcr.io/jcgonzalez01/api_consulta:latest`
y reiniciar la app).

## Variables

| Variable | Por defecto | Uso |
|---|---|---|
| `API_KEY` | — | Clave exigida en `X-API-Key`. **Obligatoria** si se publica en Internet. |
| `CACHE_TTL` | `600` | Segundos que se guarda cada consulta en memoria. |
| `DGII_TIMEOUT` | `6` | Segundos de espera por la DGII en cada intento (hay 2 intentos). |
| `TUNNEL_TOKEN` | — | Token del Cloudflare Tunnel (servicio `cloudflared`). |

## Problemas frecuentes

| Problema | Solución |
|---|---|
| CasaOS no descarga la imagen (`denied` / `unauthorized`) | El paquete sigue privado: paso 1. |
| `502` en todas las cédulas | El servidor no está en RD o la DGII no responde; probar el `curl` del paso 4 en la red local. |
| `401` | La `X-API-Key` no coincide con `API_KEY`. |
| Túnel `DOWN` / `INACTIVE` | Token mal copiado; revise los logs del contenedor `api-consulta-tunel`. |
| Error 1033 en el dominio | El túnel no está conectado (contenedor cloudflared detenido). |
