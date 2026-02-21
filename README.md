# Portafolio Alejandro Benítez

Arquitectura de producción con Django, React + Vite y Traefik con HTTPS automático, subdominios aislados y sesión compartida entre dominios.

## 🏗️ Arquitectura

```
Internet
    ↓
Traefik v2.10 (reverse proxy + HTTPS automático)
    ├── alejandrobenitez.com → React Frontend (Nginx)
    ├── www.alejandrobenitez.com → React Frontend (Nginx)
    ├── links.alejandrobenitez.com → Django (app_links en /)
    ├── fractalia.alejandrobenitez.com → Django (app_fractalia en /fractalia/)
    └── admin.alejandrobenitez.com → Django (admin en /admin/)
        ↓
    Django Uvicorn (8000)
        ↓
    PostgreSQL 16 (interno)
```

**Características:**
- ✅ HTTPS automático con Let's Encrypt
- ✅ HTTP → HTTPS redirect global
- ✅ Sesión compartida entre todos los subdominios
- ✅ WhiteNoise para servir archivos estáticos
- ✅ Single Django app con múltiples apps internas
- ✅ Red Docker compartida `traefik_public`

---

## 📦 Componentes

### Frontend (`ab-frontend/`)
- React 19 + Vite 6
- Tailwind CSS 4
- Framer Motion + GSAP (animaciones)
- Servido vía Nginx en contenedor

### Backend (`ab_reservas_project/`)
Proyecto Django único con 2 apps:

**1. `app_links`** - Agregador de links (Linktree-style)
- Ruta: `/` en `links.alejandrobenitez.com`
- Modelo: Link (nombre, URL, orden, activo)

**2. `app_fractalia`** - Calendario de disponibilidad + reservas
- Rutas:
  - `/fractalia/calendario/` - Página del calendario
  - `/fractalia/api/disponibilidad/` - Slots horarios
  - `/fractalia/api/dias-disponibilidad/` - Disponibilidad por día
  - `/fractalia/api/reserva-pendiente/` - Crear reserva pendiente
- Modelos: Resource, WeeklyAvailability, Booking, PendingBooking
- Integración WhatsApp (número del recurso)

### Reverse Proxy (Traefik)
- Descubre servicios automáticamente vía Docker labels
- Emite certificados Let's Encrypt (HTTP-01 challenge)
- Redirect de `/` a rutas específicas usando regex

---

## 🔐 Sesión Compartida Entre Dominios

### ¿Cómo funciona?

Django configura `SESSION_COOKIE_DOMAIN = '.alejandrobenitez.com'` (con punto inicial).

Esto hace que la cookie de sesión sea válida para **todos** los subdominios:

1. Usuario hace login en `admin.alejandrobenitez.com/admin/`
2. Django crea session cookie válida para `.alejandrobenitez.com`
3. Usuario navega a `fractalia.alejandrobenitez.com/fractalia/calendario/`
4. Browser envía automáticamente la cookie al mismo dominio (.alejandrobenitez.com)
5. Django reconoce `request.user` como autenticado y de staff

### Casos de uso

**En templates/vistas de fractalia:**
```python
def calendario(request):
    es_admin = request.user.is_authenticated and request.user.is_staff
    # Si es admin, mostrar panel de gestión
    return render(request, 'calendario.html', {
        'es_admin': es_admin,
        'user': request.user
    })
```

**En JavaScript (fetch):**
```javascript
// Las cookies se envían automáticamente con fetch (credentials: 'include')
const response = await fetch('https://fractalia.alejandrobenitez.com/fractalia/api/disponibilidad/', {
    credentials: 'include',
    headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    }
});
```

### Limitaciones

- Solo funciona para subdominio principal y sus hijos (`.alejandrobenitez.com`)
- En desarrollo local (`localhost:8000`), la cookie no se comparte (host diferente)
- CSRF protection requiere que ambos originenes estén en `CSRF_TRUSTED_ORIGINS`

---

## 🚀 Despliegue (Producción)

### Prerequisitos

1. **Servidor Linux** con Docker y Docker Compose
2. **Dominio** con registros DNS:
   ```
   alejandrobenitez.com          A  <VPS_IP>
   www.alejandrobenitez.com      A  <VPS_IP>
   links.alejandrobenitez.com    A  <VPS_IP>
   fractalia.alejandrobenitez.com A  <VPS_IP>
   admin.alejandrobenitez.com    A  <VPS_IP>
   ```
   ⚠️ **Deben existir ANTES de levantar Traefik** (Let's Encrypt HTTP-01 challenge)

3. **Red Docker compartida:**
   ```bash
   docker network create traefik_public
   ```

### Pasos de despliegue

```bash
# 1. Clonar repo
git clone <repo> && cd ale-benitez-port

# 2. Crear .env.prod con secretos reales
cp ab_reservas_project/.env ab_reservas_project/.env.prod

# Editar .env.prod:
nano ab_reservas_project/.env.prod
# - DEBUG=0
# - SECRET_KEY: generar con: python -c "import secrets; print(secrets.token_urlsafe(50))"
# - POSTGRES_PASSWORD: contraseña segura
# - ALLOWED_HOSTS y demás están listos

# 3. Regenerar poetry.lock (importante tras agregar whitenoise)
cd ab_reservas_project && poetry lock && cd ..

# 4. Levantar Traefik + Frontend
docker compose -f 1-docker-compose.prod.yml up -d --build

# 5. Levantar Django + DB
docker compose -f 3-docker-compose.reservas.prod.yml up -d --build

# 6. Verificar logs
docker compose -f 1-docker-compose.prod.yml logs -f traefik
docker compose -f 3-docker-compose.reservas.prod.yml logs -f ab-django

# 7. Esperar certs de Let's Encrypt (grep ACME en traefik logs)
docker compose -f 1-docker-compose.prod.yml logs traefik | grep -i acme
```

### `.env.prod` - Ejemplo

```dotenv
DEBUG=0
SECRET_KEY=your-random-50-char-key-here
DJANGO_SETTINGS_MODULE=ab_reservas_project.settings

# Dominios
ALLOWED_HOSTS=alejandrobenitez.com,www.alejandrobenitez.com,fractalia.alejandrobenitez.com,links.alejandrobenitez.com,admin.alejandrobenitez.com
SESSION_COOKIE_DOMAIN=.alejandrobenitez.com

# Base de datos (PostgreSQL)
DATABASE=postgresql
POSTGRES_DB=ab_reservas_prod
POSTGRES_USER=ab_user
POSTGRES_PASSWORD=your-strong-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

**⚠️ NUNCA commitear `.env.prod` a git** (está en `.gitignore`)

---

## 💻 Desarrollo Local

### Opción 1: Frontend dev + Django dev separados

**Terminal 1 - Frontend:**
```bash
docker compose -f 0-docker-compose.dev.yml up
# Accesible en http://localhost:5173
```

**Terminal 2 - Django:**
```bash
docker compose -f 2-docker-compose.reservas.yml up
# Accesible en http://localhost:8000
```

### Opción 2: Desarrollo completo local

```bash
cd ab-frontend && pnpm dev &
cd ab_reservas_project && poetry run python manage.py runserver &
```

**Requisitos locales:**
- Node.js 18+, pnpm 10+
- Python 3.12, Poetry 2.1+
- PostgreSQL 16 (o SQLite para dev rápido)

---

## 🔧 Configuración Importante

### settings.py - Puntos clave

```python
# Línea 37: ALLOWED_HOSTS lee desde .env
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Líneas 179-192: CSRF_TRUSTED_ORIGINS se construye automáticamente
# Si CSRF_TRUSTED_ORIGINS env var NO está definida:
#   - En prod (DEBUG=0): usa https://[host] para cada ALLOWED_HOST
#   - En dev (DEBUG=1): agrega http://localhost:8000, http://127.0.0.1:8000

# Línea 194: SESSION_COOKIE_DOMAIN para sesión compartida
SESSION_COOKIE_DOMAIN = os.environ.get('SESSION_COOKIE_DOMAIN', None)
# En prod: '.alejandrobenitez.com' (punto = todos los subdominos)
# En dev: None (solo localhost)

# Líneas 58: WhiteNoise para statics
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← aquí
    ...
]

# Líneas 164-171: Compresión de statics
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

### Traefik - Routing

**Router 1: links → Django root**
```
Host: links.alejandrobenitez.com
Path: / (cualquiera)
→ Django recibe GET / → app_links
```

**Router 2: fractalia → Django con redirect**
```
Host: fractalia.alejandrobenitez.com
Path: /
→ Traefik redirect → https://fractalia.alejandrobenitez.com/fractalia/calendario/

Path: /fractalia/* (regex no matchea)
→ Django recibe GET /fractalia/* → app_fractalia
```

**Router 3: admin → Django con redirect**
```
Host: admin.alejandrobenitez.com
Path: /
→ Traefik redirect → https://admin.alejandrobenitez.com/admin/

Path: /admin/* (regex no matchea)
→ Django recibe GET /admin/* → admin
```

---

## 📊 Monitoreo

### Ver logs en vivo

```bash
# Traefik
docker compose -f 1-docker-compose.prod.yml logs -f traefik

# Django + DB
docker compose -f 3-docker-compose.reservas.prod.yml logs -f ab-django
docker compose -f 3-docker-compose.reservas.prod.yml logs -f db

# Todo
docker compose -f 1-docker-compose.prod.yml -f 3-docker-compose.reservas.prod.yml logs -f
```

### Health checks

```bash
# Traefik expone puerto 80/443
curl -I http://localhost/

# Django en la red interna
docker compose -f 3-docker-compose.reservas.prod.yml exec ab-django curl http://localhost:8000/admin/

# DB
docker compose -f 3-docker-compose.reservas.prod.yml exec db pg_isready
```

---

## 🗄️ Base de Datos

### Dump de datos (excluir admin)

```bash
# Desde producción con PostgreSQL
docker compose -f 3-docker-compose.reservas.prod.yml exec db pg_dump \
  -U ab_user \
  -d ab_reservas_prod \
  --exclude-table-data='auth_*' \
  --exclude-table-data='django_session' \
  --exclude-table-data='django_content_type' \
  > backup_clean.sql
```

### Migrations

```bash
# Crear migración
docker compose -f 3-docker-compose.reservas.prod.yml exec ab-django \
  poetry run python manage.py makemigrations

# Aplicar
docker compose -f 3-docker-compose.reservas.prod.yml exec ab-django \
  poetry run python manage.py migrate
```

---

## 🛠️ Troubleshooting

### CSRF token mismatch
**Causa:** Origin no está en `CSRF_TRUSTED_ORIGINS`
**Solución:** Verificar que `ALLOWED_HOSTS` en `.env.prod` incluya todos los dominios

### Let's Encrypt timeout
**Causa:** DNS no resuelve o firewall bloquea puerto 80
**Solución:**
```bash
# Verificar DNS
nslookup fractalia.alejandrobenitez.com

# Verificar puerto 80
curl -v http://fractalia.alejandrobenitez.com/.well-known/acme-challenge/test
```

### Sesión no se comparte entre dominios
**Causa:** `SESSION_COOKIE_DOMAIN` no está en `.env.prod`
**Solución:** Agregar `SESSION_COOKIE_DOMAIN=.alejandrobenitez.com` y reiniciar Django

---

## 📚 Estructura de archivos

```
ale-benitez-port/
├── 0-docker-compose.dev.yml          # Frontend dev
├── 1-docker-compose.prod.yml         # PROD: Traefik + Frontend
├── 3-docker-compose.reservas.prod.yml # PROD: Django + DB
│
├── ab-frontend/                      # React + Vite
│   ├── Dockerfile                    # Multi-stage: Node → Nginx
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│
├── ab_reservas_project/              # Django
│   ├── Dockerfile
│   ├── entrypoint.sh                 # collectstatic + migrate + uvicorn
│   ├── .env.prod                     # Secretos (no commitear)
│   ├── pyproject.toml                # Poetry deps (django, uvicorn, psycopg, whitenoise)
│   │
│   ├── ab_reservas_project/          # Settings
│   │   ├── settings.py               # Configuración principal
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── app_links/                    # Links aggregator
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   └── app_fractalia/                # Studio calendar
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       └── templates/
│
└── nginx/
    └── nginx.conf                    # SPA routing + caching
```

---

## 🔐 Seguridad (Producción)

Checklist antes de producción:

- ✅ `DEBUG=0` en `.env.prod`
- ✅ `SECRET_KEY` generado con `secrets.token_urlsafe(50)`
- ✅ HTTPS/TLS habilitado (Traefik con Let's Encrypt)
- ✅ CSRF protection activa
- ✅ Session cookies secure (`CSRF_COOKIE_SECURE = not DEBUG`)
- ✅ PostgreSQL con contraseña fuerte
- ✅ `.env.prod` en `.gitignore` (no commitear secretos)
- ✅ Firewall: solo puertos 80, 443 abiertos
- ✅ DB interna: no expuesta a internet (red Docker aislada)

---

## 📞 Soporte

Para problemas o preguntas, revisar:
- Logs de Traefik: `docker compose -f 1-docker-compose.prod.yml logs traefik`
- Logs de Django: `docker compose -f 3-docker-compose.reservas.prod.yml logs ab-django`
- Settings.py: Configuración centralizada de Django
- Plan de arquitectura: `/home/jose/.claude/plans/cozy-gliding-tarjan.md`

---

**Última actualización:** Feb 2026
**Versiones:**
- Django 5.2.8
- React 19.1.0
- Traefik 2.10
- PostgreSQL 16 (Alpine)
- Uvicorn 0.38+
