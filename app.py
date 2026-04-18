from flask import Flask, render_template, request, redirect, flash
import os
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

with app.app_context():
    init_db()
    
# conexión a PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

print("DEBUG DATABASE_URL:", DATABASE_URL)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# crear tabla si no existe
def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            fecha TEXT,
            hora TEXT,
            telefono TEXT
        )
    ''')

    conn.commit()
    conn.close()

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

    # verificar duplicado
    c.execute(
        "SELECT * FROM turnos WHERE fecha = %s AND hora = %s",
        (fecha, hora)
    )
    existe = c.fetchone()

    if existe:
        conn.close()
        flash("Ya existe un turno en ese horario", 'danger')
        return redirect('/')

    # insertar turno
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
