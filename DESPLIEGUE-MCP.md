# Despliegue del servicio MCP a producción

Servicio nuevo `ab-mcp` en `mcp.alejandrobenitez.com`, con OAuth 2.1 provisto por
Django (django-oauth-toolkit). Sin migraciones propias: las únicas tablas nuevas
son las de `oauth2_provider`.

## Antes de empezar

- [ ] Snapshot del servidor hecha
- [ ] Registro DNS `mcp.alejandrobenitez.com` → `161.35.112.21` (tipo A), propagado
- [ ] Verificar propagación: `dig +short mcp.alejandrobenitez.com`

## 1. Traer el código

```sh
ssh ab-webpage
cd /ruta/al/repo
git pull
```

## 2. Ajustar `.env.prod`

No hace falta ninguna clave nueva: OAuth usa las tablas de la base. Solo revisar
que `ALLOWED_HOSTS` incluya el subdominio nuevo, porque Django emite ahí el
metadata del authorization server:

```
ALLOWED_HOSTS=alejandrobenitez.com,www.alejandrobenitez.com,links.alejandrobenitez.com,fractalia.alejandrobenitez.com,admin.alejandrobenitez.com,mcp.alejandrobenitez.com
CSRF_TRUSTED_ORIGINS=https://admin.alejandrobenitez.com,https://fractalia.alejandrobenitez.com,https://links.alejandrobenitez.com,https://mcp.alejandrobenitez.com
```

## 3. Migrar y levantar

```sh
docker compose -f 3-docker-compose.reservas.prod.yml build django mcp
docker compose -f 3-docker-compose.reservas.prod.yml up -d django
docker exec ab-django python manage.py migrate          # crea las tablas de oauth2_provider
docker compose -f 3-docker-compose.reservas.prod.yml up -d mcp
```

## 4. Verificar

```sh
# El servicio arrancó y exige token
curl -s -o /dev/null -w '%{http_code}\n' https://mcp.alejandrobenitez.com/mcp   # 401

# Publica su metadata de resource server (RFC 9728)
curl -s https://mcp.alejandrobenitez.com/.well-known/oauth-protected-resource/mcp | jq

# Django publica el metadata de authorization server, con registro dinámico
curl -s https://admin.alejandrobenitez.com/o/.well-known/oauth-authorization-server | jq
```

Lo que tiene que dar:

| Chequeo | Esperado |
|---|---|
| `/mcp` sin token | `401` con cabecera `WWW-Authenticate` |
| `authorization_servers` del recurso | `https://admin.alejandrobenitez.com/o` |
| `code_challenge_methods_supported` | `["S256"]` — sin `plain` |
| `grant_types_supported` | sin `implicit` ni `password` |
| `registration_endpoint` | presente |

Si el servicio no levanta, mirá `docker logs ab-mcp`: está hecho para **fallar
cerrado**, así que si no puede armar la autenticación no arranca en vez de
quedar abierto.

## 5. Conectar desde Claude

En **Configuración → Conectores → Añadir conector personalizado**:

- Nombre: `Fractalia`
- URL: `https://mcp.alejandrobenitez.com/mcp`
- OAuth Client ID y Secreto: **dejar vacíos** — el registro dinámico está
  habilitado y Claude se registra solo

Al conectar, Claude abre el login de Django. Iniciás sesión con tu usuario del
admin y aprobás el permiso `fractalia:operar`. Desde ahí el conector queda
asociado a ese usuario.

## Operación

**Ver quién tiene acceso** — admin de Django, sección *Django OAuth Toolkit*:

- *Applications*: los clientes registrados (Claude crea el suyo vía DCR)
- *Access tokens*: las sesiones activas, con usuario y vencimiento

**Cortar el acceso a alguien**: borrar sus access tokens y refresh tokens desde
el admin. Corta al instante, porque el MCP valida contra esas tablas en cada
llamada. Para cortar de raíz, desactivar el usuario en *Users*.

**Vencimientos**: access token 8 horas, refresh 30 días con rotación y
protección de reuso.

## Notas

- El MCP no publica puertos al host: solo se llega por Traefik.
- Tokens guardados hasheados en base (`COMPLIANT_BCP_RFC9700_TOKEN_STORAGE`).
- El certificado de `mcp.alejandrobenitez.com` queda en los registros públicos
  de Certificate Transparency, así que el subdominio es descubrible. Por eso la
  autenticación no es opcional.

## Vuelta atrás

```sh
docker compose -f 3-docker-compose.reservas.prod.yml stop mcp
docker compose -f 3-docker-compose.reservas.prod.yml rm -f mcp
```

Quitar el servicio no toca nada de lo existente: Django, el calendario y el
admin siguen funcionando igual. Las tablas de `oauth2_provider` quedan vacías
sin efecto. Para revertir del todo, restaurar la snapshot.
