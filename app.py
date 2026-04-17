from flask import Flask, render_template, request, redirect, flash
import sqlite3
import os

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev")

# Inicializar base de datos
def agregar_columna_si_no_existe():
    conn = sqlite3.connect('turnos.db')
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE turnos ADD COLUMN telefono TEXT")
    except:
        pass  # si ya existe, no hace nada

    conn.commit()
    conn.close()
    
def init_db():
    conn = sqlite3.connect('turnos.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            fecha TEXT,
            hora TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('turnos.db')
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
    
    # Validación
    if not nombre or not fecha or not hora:
        flash("Complete todos los campos", 'warning')
        return redirect('/')

    if not nombre or not fecha or not hora or not telefono:
        flash("Complete todos los campos", 'warning')
        return redirect('/')
        
    conn = sqlite3.connect('turnos.db')
    c = conn.cursor()

    # Verificar duplicado
    c.execute("SELECT * FROM turnos WHERE fecha = ? AND hora = ?", (fecha, hora))
    existe = c.fetchone()

    if existe:
        conn.close()
        flash("Ya existe un turno en ese horario", 'danger')
        return redirect('/')

    # Insertar turno
    c.execute(
        "INSERT INTO turnos (nombre, fecha, hora, telefono) VALUES (?, ?, ?, ?)",
        (nombre, fecha, hora, telefono)
    )
    conn.commit()
    conn.close()

    flash("Turno agregado correctamente", 'success')
    return redirect('/')

@app.route('/eliminar/<int:id>')
def eliminar(id):
    conn = sqlite3.connect('turnos.db')
    c = conn.cursor()
    c.execute("DELETE FROM turnos WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Turno eliminado", 'info')
    return redirect('/')

if __name__ == '__main__':
        init_db()
        agregar_columna_si_no_existe()
        app.run(debug=True)
