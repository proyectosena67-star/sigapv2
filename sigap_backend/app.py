# sigap_backend/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from auth import requiere_rol # Importa tu guardián de roles desde auth.py

# --- CONFIGURACIÓN DE RUTAS ABSOLUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'sigap_frontend'))

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, 'templates'),
    static_folder=os.path.join(FRONTEND_DIR, 'static')
)

app.secret_key = 'clave_secreta_sigap_2026'


# --- FUNCIÓN DE CONSULTA CON AUDITORÍA ---
def consultar_usuario(correo, password):
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    user = conn.execute('''
        SELECT u.*, r.nombre AS rol_nombre 
        FROM USUARIOS u
        INNER JOIN ROLES r ON u.id_rol = r.id_rol
        WHERE u.correo = ? AND u.password = ? AND u.activo = 1
    ''', (correo, password)).fetchone()
    conn.close()
    return user


# --- FUNCIÓN: BUSCAR PACIENTES ---
def buscar_pacientes(criterio=""):
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if criterio:
        query = "SELECT * FROM PACIENTES WHERE nombre LIKE ? OR documento LIKE ?"
        pacientes = conn.execute(query, (f"%{criterio}%", f"%{criterio}%")).fetchall()
    else:
        pacientes = conn.execute("SELECT * FROM PACIENTES LIMIT 10").fetchall()
    conn.close()
    return pacientes


# --- RUTA LOGIN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')       
        password = request.form.get('password')   
        user = consultar_usuario(correo, password)
        
        if user:
            session['logged_in'] = True
            session['username'] = user['nombre']
            session['rol'] = user['rol_nombre'] 
            
            if session['rol'] == 'administrador':
                return redirect(url_for('medicamentos'))
            return redirect(url_for('pacientes'))
        else:
            flash('Correo institucional o contraseña incorrectos, o cuenta inactiva.', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/pacientes')
def pacientes():
    search_query = request.args.get('q', '').strip()
    
    # Ruta de tu base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # === CONSULTAS ESTADÍSTICAS AUTOMÁTICAS ===
    # 1. Total de pacientes registrados
    cursor.execute("SELECT COUNT(*) AS total FROM PACIENTES")
    total_registrados = cursor.fetchone()['total'] or 0

    # 2. Total en hospitalización (activos)
    cursor.execute("SELECT COUNT(*) AS activos FROM PACIENTES WHERE estado = 'Hospitalizado'")
    total_hospitalizados = cursor.fetchone()['activos'] or 0

    # 3. Nombre del último paciente ingresado (basado en el ID más alto)
    cursor.execute("SELECT nombre FROM PACIENTES ORDER BY id_paciente DESC LIMIT 1")
    ultimo_registro = cursor.fetchone()
    ultimo_ingreso = ultimo_registro['nombre'] if ultimo_registro else "Ninguno"
    
    # === CONSULTA DE BÚSQUEDA Y FILTRADO ===
    if search_query:
        sql = """
            SELECT * FROM PACIENTES 
            WHERE nombre LIKE ? OR documento LIKE ? OR codigo_unico LIKE ?
        """
        cursor.execute(sql, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("SELECT * FROM PACIENTES")
        
    lista_pacientes = cursor.fetchall()
    conn.close()
    
    return render_template(
        'pacientes.html', 
        pacientes=lista_pacientes, 
        search_query=search_query,
        total_registrados=total_registrados,
        total_hospitalizados=total_hospitalizados,
        ultimo_ingreso=ultimo_ingreso
    )

@app.route('/historial')
@requiere_rol('administrador', 'psiquiatra', 'medico', 'nutricionista')
def historial():
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Traemos los historiales clínicos creados junto al nombre del paciente
    historiales = conn.execute('''
        SELECT h.id_historial, h.fecha, p.nombre, p.documento 
        FROM HISTORIAL_CLINICO h
        INNER JOIN PACIENTES p ON h.id_paciente = p.id_paciente
    ''').fetchall()
    conn.close()
    return render_template('historial.html', historiales=historiales)


@app.route('/medicamentos')
@requiere_rol('administrador', 'psiquiatra', 'medico')
def medicamentos():
    # Buscamos los medicamentos existentes para listarlos en el inventario
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Unimos MEDICAMENTOS con INVENTARIO usando un LEFT JOIN
    meds = conn.execute('''
        SELECT m.nombre, COALESCE(i.cantidad, 0) as cantidad 
        FROM MEDICAMENTOS m
        LEFT JOIN INVENTARIO i ON m.id_medicamento = i.id_medicamento
    ''').fetchall()
    conn.close()
    return render_template('medicamentos.html', medicamentos=meds)

# --- RUTA LOGOUT ---
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)