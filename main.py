"""
Centro de Cargas — Classroom Tech Issue Reporter
FastAPI + SQLite + CallMeBot WhatsApp notifications
"""

import os
import io
import sqlite3
import hashlib
import hmac
import html as html_mod
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
import qrcode
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
CALLMEBOT_PHONE = os.getenv("CALLMEBOT_PHONE", "")
CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DB_PATH = os.getenv("DB_PATH", "reports.db")

app = FastAPI(title="Centro de Cargas")

# ─── Templates & Logo ────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

LOGO_B64 = ""
logo_file = BASE_DIR / "logo.txt"
if logo_file.exists():
    LOGO_B64 = logo_file.read_text().strip()

FORM_TPL = (BASE_DIR / "form.html").read_text()
LOGIN_TPL = (BASE_DIR / "login.html").read_text()
ADMIN_TPL = (BASE_DIR / "admin.html").read_text()


# ─── Database ─────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reports ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  nivel TEXT NOT NULL DEFAULT '',"
        "  aula TEXT NOT NULL,"
        "  nombre TEXT NOT NULL DEFAULT '',"
        "  apellido_paterno TEXT NOT NULL DEFAULT '',"
        "  apellido_materno TEXT NOT NULL DEFAULT '',"
        "  problema TEXT NOT NULL,"
        "  timestamp TEXT NOT NULL"
        ")"
    )
    conn.commit()
    conn.close()


init_db()


# ─── Auth helpers ─────────────────────────────────────────────────
def sign_token(data: str) -> str:
    sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}:{sig}"


def verify_token(token: str) -> bool:
    if not token or ":" not in token:
        return False
    parts = token.rsplit(":", 1)
    if len(parts) != 2:
        return False
    data, sig = parts
    expected = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("session")
    return verify_token(token) if token else False


# ─── WhatsApp notification ────────────────────────────────────────
async def send_whatsapp(nivel: str, aula: str, nombre_completo: str, problema: str, timestamp: str):
    if not CALLMEBOT_PHONE or not CALLMEBOT_APIKEY:
        print("[WARN] CallMeBot not configured, skipping WhatsApp notification")
        return
    msg = (
        "\U0001f6a8 *[" + nivel.upper() + " — AULA: " + aula + "]*\n"
        "\U0001f464 " + nombre_completo + "\n"
        "\U0001f4dd " + problema + "\n"
        "\U0001f550 " + timestamp
    )
    encoded = urllib.parse.quote_plus(msg)
    url = (
        "https://api.callmebot.com/whatsapp.php"
        "?phone=" + CALLMEBOT_PHONE +
        "&text=" + encoded +
        "&apikey=" + CALLMEBOT_APIKEY
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            print(f"[OK] WhatsApp sent (status {resp.status_code})")
    except Exception as e:
        print(f"[ERR] WhatsApp error: {e}")


# ─── Template helpers ─────────────────────────────────────────────
def render_form():
    return FORM_TPL.replace("%%LOGO_B64%%", LOGO_B64)


def render_login(error=""):
    err_html = ""
    if error:
        err_html = '<p class="error">' + html_mod.escape(error) + "</p>"
    return LOGIN_TPL.replace("%%ERROR_BLOCK%%", err_html)


def render_admin(rows):
    count = len(rows)
    if count == 0:
        row_html = '<tr><td colspan="5" class="empty">No hay reportes aún.</td></tr>'
    else:
        parts = []
        for r in rows:
            nombre_full = " ".join(
                filter(None, [r["nombre"], r["apellido_paterno"], r["apellido_materno"]])
            )
            nivel_val = r["nivel"] if "nivel" in r.keys() else ""
            nivel_cls = "nivel-sec" if nivel_val == "Secundaria" else "nivel-bach"
            nivel_tag = '<span class="nivel-tag ' + nivel_cls + '">' + html_mod.escape(nivel_val) + '</span>' if nivel_val else ""
            parts.append(
                "<tr>"
                "<td>" + html_mod.escape(r["timestamp"]) + "</td>"
                "<td>" + nivel_tag + "</td>"
                "<td><strong>" + html_mod.escape(r["aula"]) + "</strong></td>"
                "<td>" + html_mod.escape(nombre_full) + "</td>"
                "<td>" + html_mod.escape(r["problema"]) + "</td>"
                "</tr>"
            )
        row_html = "\n".join(parts)
    return ADMIN_TPL.replace("%%COUNT%%", str(count)).replace("%%ROWS%%", row_html)


# ─── Routes ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def public_form():
    return render_form()


@app.post("/api/report")
async def submit_report(
    nivel: str = Form(...),
    aula: str = Form(...),
    nombre: str = Form(...),
    apellido_paterno: str = Form(...),
    apellido_materno: str = Form(""),
    problema: str = Form(...),
):
    if nivel not in ("Secundaria", "Bachillerato"):
        raise HTTPException(400, detail="Nivel inválido.")
    if len(problema) > 420:
        raise HTTPException(400, detail="El problema excede los 420 caracteres.")

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    conn = get_db()
    conn.execute(
        "INSERT INTO reports (nivel, aula, nombre, apellido_paterno, apellido_materno, problema, timestamp)"
        " VALUES (?,?,?,?,?,?,?)",
        (nivel.strip(), aula.strip(), nombre.strip(), apellido_paterno.strip(),
         apellido_materno.strip(), problema.strip(), ts),
    )
    conn.commit()
    conn.close()

    nombre_completo = " ".join(
        filter(None, [nombre.strip(), apellido_paterno.strip(), apellido_materno.strip()])
    )
    await send_whatsapp(nivel.strip(), aula.strip(), nombre_completo, problema.strip(), ts)

    return {"ok": True, "message": "Reporte guardado exitosamente."}


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_authenticated(request):
        return render_login()
    conn = get_db()
    rows = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    conn.close()
    return render_admin(rows)


@app.post("/admin/login")
async def admin_login(email: str = Form(...), password: str = Form(...)):
    if email.strip().lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        token = sign_token(email + "|" + str(int(time.time())))
        response = RedirectResponse("/admin", status_code=303)
        response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400)
        return response
    return HTMLResponse(render_login("Credenciales incorrectas."), status_code=401)


@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/qr")
async def qr_code():
    url = BASE_URL.rstrip("/") + "/"
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="image/png",
        headers={"Content-Disposition": "inline; filename=centro-de-cargas-qr.png"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
