from flask import Flask, render_template, request, redirect, flash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

DATABASE_URL = os.environ.get("DATABASE_URL")


# 🔌 conexión
def get_connection():
    return psycopg2.connect(DATABASE_URL)


# 🧱 crear tabla
def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            fecha TEXT,
            hora TEXT,
            telefono TEXT
        )
    """)

    conn.commit()
    conn.close()


# 🚀 ACA VA (después de definir la función)
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

    if not nombre or not fecha or not hora or not telefono:
        flash("Complete todos los campos", 'warning')
        return redirect('/')

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM turnos WHERE fecha = %s AND hora = %s", (fecha, hora))
    existe = c.fetchone()

    if existe:
        conn.close()
        flash("Ya existe un turno en ese horario", 'danger')
        return redirect('/')

    c.execute(
        "INSERT INTO turnos (nombre, fecha, hora, telefono) VALUES (%s, %s, %s, %s)",
        (nombre, fecha, hora, telefono)
    )

    conn.commit()
    conn.close()

    flash("Turno agregado correctamente", 'success')
    return redirect('/')


@app.route('/eliminar/<int:id>')
def eliminar(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM turnos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    flash("Turno eliminado", 'info')
    return redirect('/')
