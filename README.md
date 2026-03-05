# Centro de Cargas 

**Sistema de reportes de problemas tecnológicos en aulas**
Sistemas — Servicio Comunitario · Fundación Azteca

---

## Características

- **Formulario público** (`/`) — Los profesores reportan problemas desde su celular
- **Notificación WhatsApp** — Cada reporte envía un mensaje instantáneo al TIC vía CallMeBot
- **Panel Admin** (`/admin`) — Vista de todos los reportes, protegida con login
- **Código QR** (`/qr`) — Genera un QR imprimible que enlaza al formulario
- **Mobile-first** — Diseñado para usarse en teléfono

---

## Requisitos

- Python 3.10+
- pip

---

## Instalación Local

```bash
# 1. Clonar el repositorio
git clone <tu-repo-url>
cd centro-de-cargas

# 2. Crear entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus valores reales

# 5. Ejecutar
uvicorn main:app --reload --port 8000
```

Abre `http://localhost:8000` en tu navegador.

---

## Configuración de CallMeBot (una sola vez)

CallMeBot permite enviar mensajes de WhatsApp gratis vía API.

1. Agrega el contacto **+34 644 71 99 23** a tus contactos de WhatsApp
2. Envía el mensaje: `I allow callmebot to send me messages`
3. Espera la respuesta — te darán un **API key**
4. Coloca tu número (con código de país, ej. `521234567890`) y tu API key en las variables de entorno:
   ```
   CALLMEBOT_PHONE=521234567890
   CALLMEBOT_APIKEY=123456
   ```

> **Nota:** El primer mensaje puede tardar unos segundos. Si no llega, verifica que el contacto esté agregado y que hayas enviado el mensaje de autorización.

---

## Deploy en Railway

1. Sube el proyecto a un repositorio de GitHub

2. Ve a [railway.app](https://railway.app) y crea un nuevo proyecto desde GitHub

3. Railway detectará el `Procfile` automáticamente

4. Configura las **variables de entorno** en Railway → Settings → Variables:
   | Variable | Valor |
   |---|---|
   | `CALLMEBOT_PHONE` | Tu número con código de país |
   | `CALLMEBOT_APIKEY` | Tu API key de CallMeBot |
   | `ADMIN_EMAIL` | Email para login admin |
   | `ADMIN_PASSWORD` | Contraseña para login admin |
   | `SECRET_KEY` | Una cadena aleatoria larga |
   | `BASE_URL` | `https://tu-app.up.railway.app` |

5. Haz deploy. Railway asignará un dominio público automáticamente.

6. Actualiza `BASE_URL` con el dominio asignado para que el QR funcione correctamente.

---

## Endpoints

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Formulario público de reportes |
| `/api/report` | POST | Envía un reporte (usado por el form) |
| `/admin` | GET | Panel admin (login requerido) |
| `/admin/login` | POST | Autenticación admin |
| `/admin/logout` | GET | Cierra sesión admin |
| `/qr` | GET | Genera imagen QR del formulario |
| `/health` | GET | Health check |

---

## Estructura del Proyecto

```
centro-de-cargas/
├── main.py            # Aplicación FastAPI completa
├── logo.txt           # Logo en base64
├── requirements.txt   # Dependencias Python
├── Procfile           # Comando de inicio para Railway
├── .env.example       # Plantilla de variables de entorno
└── README.md          # Este archivo
```

---

## Licencia

Uso interno — Sistemas, Servicio Comunitario, uso común.
