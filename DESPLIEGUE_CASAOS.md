# Despliegue en CasaOS (servidor local en RD) por Tailscale

La API debe correr desde una conexión **en República Dominicana**: la DGII deja abrir
sus páginas desde servidores en el extranjero (Coolify/Contabo, Francia) pero **no
responde las búsquedas**. Desde una conexión dominicana responde en menos de 1 segundo.

Esquema:

```
KaiCredit (Coolify, Francia) ──Tailscale──> CasaOS (RD) :8000 ──> DGII
```

Los dos servidores están en la misma red Tailscale, así que no hay que abrir puertos
en el router ni publicar la API en Internet.

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

## 2. Instalar en CasaOS

1. CasaOS → **App Store** → botón **+** (arriba a la derecha) →
   **Install a customized app** → **Import**.
2. Pegue el contenido de [`casaos/docker-compose.yml`](casaos/docker-compose.yml).
3. Cambie `API_KEY` por la **misma** clave que tiene KaiCredit en `API_CONSULTA_KEY`.
4. **Install**.

## 3. Probar en el servidor CasaOS

```bash
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: SU-CLAVE" http://127.0.0.1:8000/cedula/00117123778
```

Debe devolver el nombre en 1–2 segundos. Anote la IP de Tailscale del servidor:

```bash
tailscale ip -4        # ej. 100.x.y.z
```

## 4. Conectar KaiCredit (Coolify)

1. Desde el **servidor Coolify** (SSH o terminal del host), confirme que llega a CasaOS:

   ```bash
   curl -H "X-API-Key: SU-CLAVE" http://100.x.y.z:8000/cedula/00117123778
   ```

2. Desde el **contenedor de KaiCredit** (Coolify → app KaiCredit → **Terminal**). La
   imagen no trae `curl`; use Node:

   ```bash
   node -e "fetch('http://100.x.y.z:8000/health').then(r=>r.text()).then(console.log).catch(e=>console.log('ERROR',e.cause?.code||e.message))"
   ```

   Debe imprimir `{"status":"ok"}`. Si da `ETIMEDOUT`/`EHOSTUNREACH`, el contenedor no
   sale por Tailscale: vea "Problemas frecuentes".

3. En Coolify → app KaiCredit → **Environment Variables** (no "Build Variable"):

   | Variable | Valor |
   |---|---|
   | `API_CONSULTA_URL` | `http://100.x.y.z:8000` |
   | `API_CONSULTA_KEY` | la misma `API_KEY` de CasaOS |

4. **Restart** de KaiCredit y pruebe registrando un cliente.

Use la **IP** de Tailscale, no el nombre MagicDNS: dentro de los contenedores de Docker
el DNS de Tailscale normalmente no resuelve.

Cuando funcione, la app api-consulta de Coolify ya no hace falta y se puede detener.

## 5. Actualizar

Al hacer push a `main`, GitHub publica la imagen nueva. En CasaOS: abra la app →
**⋮** → **Check then update** (o por SSH: `sudo docker pull ghcr.io/jcgonzalez01/api_consulta:latest`
y reiniciar la app).

## Variables

| Variable | Por defecto | Uso |
|---|---|---|
| `API_KEY` | — | Clave exigida en `X-API-Key`. Úsela aunque sea solo por Tailscale. |
| `CACHE_TTL` | `600` | Segundos que se guarda cada consulta en memoria. |
| `DGII_TIMEOUT` | `6` | Segundos de espera por la DGII en cada intento (hay 2 intentos). |

## Problemas frecuentes

| Problema | Solución |
|---|---|
| CasaOS no descarga la imagen (`denied` / `unauthorized`) | El paquete sigue privado: paso 1. |
| El host Coolify llega a CasaOS pero el contenedor de KaiCredit no | Docker no está enrutando hacia `tailscale0`. Revise que Tailscale corra en el **host** (no en un contenedor) y que no haya reglas de firewall bloqueando `100.64.0.0/10` desde la red de Docker. |
| `ETIMEDOUT` también desde el host Coolify | Revise en el panel de Tailscale que las ACL permitan Coolify → CasaOS puerto 8000. |
| `502` en todas las cédulas | El servidor CasaOS no está saliendo por una conexión de RD (por ejemplo, usa un *exit node* en el extranjero) o la DGII no responde. |
| `401` | La `X-API-Key` no coincide con `API_KEY`. |
