from flask import Flask, render_template, request, redirect, flash, session, jsonify
import psycopg2
import os
import urllib.parse
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
NUMERO_BARBERO = os.environ.get("NUMERO_BARBERO", "5492604693013")
NOMBRE_BARBERO = os.environ.get("NOMBRE_BARBERO", "La Barbería")

# ─── Horarios disponibles ───────────────────────────────────────────────
HORARIOS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"
]

# ─── DB ─────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    # 1) Crear tabla base
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            telefono TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # 2) Agregar columnas faltantes (cada una en su propia conexión)
    columnas_extra = [
        ("servicio",   "TEXT DEFAULT 'Corte'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    for col, tipo in columnas_extra:
        conn2 = get_connection()
        c2 = conn2.cursor()
        c2.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='turnos' AND column_name=%s
        """, (col,))
        existe = c2.fetchone()
        if not existe:
            c2.execute(f"ALTER TABLE turnos ADD COLUMN {col} {tipo}")
            conn2.commit()
        conn2.close()

    # 3) Constraint unique en su propia conexión
    conn3 = get_connection()
    c3 = conn3.cursor()
    try:
        c3.execute("ALTER TABLE turnos ADD CONSTRAINT unique_turno UNIQUE (fecha, hora)")
        conn3.commit()
    except Exception:
        conn3.rollback()
    conn3.close()

with app.app_context():
    init_db()

# ─── Helpers ─────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            flash("Acceso denegado. Iniciá sesión como admin.", "danger")
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def get_turnos_ocupados(fecha):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT hora FROM turnos WHERE fecha = %s", (fecha,))
    ocupados = [row[0] for row in c.fetchall()]
    conn.close()
    return ocupados

# ─── Rutas principales ────────────────────────────────────────────────────
@app.route('/')
def index():
    conn = get_connection()
    c = conn.cursor()
    hoy = date.today().isoformat()

    # Solo turnos de hoy en adelante para el público
    c.execute("""
        SELECT id, nombre, fecha, hora, telefono, COALESCE(servicio, 'Corte') as servicio
        FROM turnos
        WHERE fecha >= %s
        ORDER BY fecha, hora
    """, (hoy,))
    turnos = c.fetchall()
    conn.close()

    # Calcular disponibilidad para los próximos 14 días
    disponibilidad = {}
    for i in range(14):
        dia = (date.today() + timedelta(days=i)).isoformat()
        ocupados = get_turnos_ocupados(dia)
        disponibilidad[dia] = len(HORARIOS) - len(ocupados)

    return render_template('index.html',
        turnos=turnos,
        horarios=HORARIOS,
        disponibilidad=disponibilidad,
        nombre_barbero=NOMBRE_BARBERO,
        hoy=hoy,
        is_admin=session.get('admin', False)
    )

@app.route('/disponibilidad/<fecha>')
def disponibilidad_fecha(fecha):
    """API para obtener horarios disponibles de una fecha."""
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Fecha inválida"}), 400

    if fecha_obj < date.today():
        return jsonify({"error": "Fecha pasada"}), 400

    ocupados = get_turnos_ocupados(fecha)
    horarios_estado = [
        {"hora": h, "disponible": h not in ocupados}
        for h in HORARIOS
    ]
    return jsonify(horarios_estado)

@app.route('/agregar', methods=['POST'])
def agregar():
    nombre   = request.form.get('nombre', '').strip()
    fecha    = request.form.get('fecha', '').strip()
    hora     = request.form.get('hora', '').strip()
    telefono = request.form.get('telefono', '').strip()
    servicio = request.form.get('servicio', 'Corte').strip()

    # ── Validaciones ──
    if not all([nombre, fecha, hora, telefono]):
        flash("Completá todos los campos.", 'warning')
        return redirect('/')

    if not telefono.isdigit() or len(telefono) < 8:
        flash("El teléfono debe tener solo números (mínimo 8 dígitos).", 'warning')
        return redirect('/')

    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        flash("Fecha inválida.", 'warning')
        return redirect('/')

    if fecha_obj < date.today():
        flash("No podés reservar en una fecha pasada.", 'warning')
        return redirect('/')

    if hora not in HORARIOS:
        flash("Horario inválido.", 'warning')
        return redirect('/')

    # Validar que no sea hoy + hora pasada
    if fecha_obj == date.today():
        hora_actual = datetime.now().strftime("%H:%M")
        if hora <= hora_actual:
            flash("Ese horario ya pasó para hoy.", 'warning')
            return redirect('/')

    # ── Guardar ──
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM turnos WHERE fecha = %s AND hora = %s", (fecha, hora))
    if c.fetchone():
        conn.close()
        flash("Ese horario ya está ocupado. Elegí otro.", 'danger')
        return redirect('/')

    try:
        c.execute(
            "INSERT INTO turnos (nombre, fecha, hora, telefono, servicio) VALUES (%s, %s, %s, %s, %s)",
            (nombre, fecha, hora, telefono, servicio)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        flash("Ese horario ya está ocupado.", 'danger')
        return redirect('/')
    conn.close()

    # ── WhatsApp ──
    dia_semana = fecha_obj.strftime("%A").capitalize()
    fecha_formato = fecha_obj.strftime("%d/%m/%Y")
    mensaje = (
        f"¡Hola! Quiero confirmar mi turno en {NOMBRE_BARBERO} 💈\n\n"
        f"👤 Nombre: {nombre}\n"
        f"✂️ Servicio: {servicio}\n"
        f"📅 Fecha: {dia_semana} {fecha_formato}\n"
        f"⏰ Hora: {hora}\n"
        f"📱 Tel: {telefono}\n\n"
        f"¡Muchas gracias!"
    )
    url = f"https://wa.me/{NUMERO_BARBERO}?text={urllib.parse.quote(mensaje)}"
    return redirect(url)

# ─── Admin ────────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['POST'])
def admin_login():
    pwd = request.form.get('password', '')
    if pwd == ADMIN_PASSWORD:
        session['admin'] = True
        flash("Sesión admin iniciada.", 'success')
    else:
        flash("Contraseña incorrecta.", 'danger')
    return redirect('/')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("Sesión cerrada.", 'info')
    return redirect('/')

@app.route('/admin/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM turnos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash("Turno eliminado.", 'success')
    return redirect('/')

@app.route('/admin/todos')
@admin_required
def admin_todos():
    """Admin ve TODOS los turnos incluyendo pasados."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, nombre, fecha, hora, telefono, COALESCE(servicio, 'Corte') as servicio, created_at
        FROM turnos ORDER BY fecha DESC, hora DESC
    """)
    turnos = c.fetchall()
    conn.close()
    return render_template('admin.html',
        turnos=turnos,
        nombre_barbero=NOMBRE_BARBERO
    )

if __name__ == '__main__':
    app.run(debug=True)
