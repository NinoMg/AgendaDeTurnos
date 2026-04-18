from flask import Flask, render_template, request, redirect, flash
import psycopg2
import os
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

DATABASE_URL = os.environ.get("DATABASE_URL")


# 🔌 conexión a PostgreSQL
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# 🧱 crear tabla si no existe
def init_db():
    conn = get_connection()
    c = conn.cursor()

    # crear tabla si no existe
    c.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            fecha TEXT,
            hora TEXT,
            telefono TEXT
        )
    """)

    # intentar agregar restricción única (si no existe)
    try:
        c.execute("""
            ALTER TABLE turnos
            ADD CONSTRAINT unique_turno UNIQUE (fecha, hora)
        """)
    except:
        pass  # ya existe → no rompe

    conn.commit()
    conn.close()

# 🚀 ejecutar al iniciar (IMPORTANTE en Render)
with app.app_context():
    init_db()


@app.route('/')
def index():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    turnos = c.fetchall()
    conn.close()
    return render_template('index.html', turnos=turnos)


@app.route('/agregar', methods=['POST'])
def agregar():
    nombre = request.form.get('nombre', '').strip()
    fecha = request.form.get('fecha', '').strip()
    hora = request.form.get('hora', '').strip()
    telefono = request.form.get('telefono', '').strip()

    # ✅ validación
    if not nombre or not fecha or not hora or not telefono:
        flash("Completá todos los campos", 'warning')
        return redirect('/')

    if not telefono.isdigit():
        flash("El teléfono debe tener solo números", 'warning')
        return redirect('/')

    conn = get_connection()
    c = conn.cursor()

    # 🔒 evitar duplicados
    c.execute(
        "SELECT * FROM turnos WHERE fecha = %s AND hora = %s",
        (fecha, hora)
    )
    existe = c.fetchone()

    if existe:
        conn.close()
        flash("Ese horario ya está ocupado", 'danger')
        return redirect('/')

    # 💾 guardar turno (protegido)
    try:
        c.execute(
            "INSERT INTO turnos (nombre, fecha, hora, telefono) VALUES (%s, %s, %s, %s)",
            (nombre, fecha, hora, telefono)
        )
        conn.commit()
    except:
        conn.close()
        flash("Ese horario ya está ocupado", 'danger')
        return redirect('/')
    
    conn.close()

    # 📲 mensaje para WhatsApp
    mensaje = f"""
Hola! Quiero confirmar mi turno:

👤 Nombre: {nombre}
📅 Fecha: {fecha}
⏰ Hora: {hora}
📱 Tel: {telefono}
"""

    mensaje = urllib.parse.quote(mensaje)

    # 🔥 CAMBIAR ESTE NÚMERO POR EL DEL BARBERO
    numero_barbero = "5492604693013"

    url = f"https://wa.me/{numero_barbero}?text={mensaje}"

    # 👉 redirige directo a WhatsApp
    return redirect(url)


# ❌ eliminamos endpoint público (seguridad)
# @app.route('/eliminar/<int:id>')
# def eliminar(id):
#     pass


if __name__ == '__main__':
    app.run(debug=True)
