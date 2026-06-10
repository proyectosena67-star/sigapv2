# sigap_backend/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from auth import requiere_rol 

# --- CONFIGURACIÓN DE RUTAS ABSOLUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'sigap_frontend'))

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, 'templates'),
    static_folder=os.path.join(FRONTEND_DIR, 'static')
)

app.secret_key = 'clave_secreta_sigap_2026'

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_PERMANENT'] = True


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


# --- FUNCIÓN AUXILIAR: DATOS DE SESIÓN ---
def obtener_datos_usuario():
    """Retorna un diccionario con el nombre y rol procesado del usuario en sesión."""
    usuario_nombre = session.get('nombre', 'Usuario Staff')
    rol_id = session.get('rol_id')
    
    if rol_id == 1:
        usuario_rol = "Administrador"
    elif rol_id == 2:
        usuario_rol = "Psiquiatra"
    elif rol_id == 3:
        usuario_rol = "Médico General"
    else:
        usuario_rol = "Personal Médico"
        
    return {"usuario_nombre": usuario_nombre, "usuario_rol": usuario_rol}


# --- RUTA LOGIN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo_ingresado = request.form.get('correo', '').strip()
        password_ingresada = request.form.get('password', '').strip()
        
        db_path = os.path.join(os.path.dirname(__file__), 'sigap.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Hacemos un INNER JOIN con la tabla ROLES para traernos el nombre de texto de inmediato
        cursor.execute('''
            SELECT u.*, r.nombre AS rol_nombre 
            FROM USUARIOS u
            INNER JOIN ROLES r ON u.id_rol = r.id_rol
            WHERE u.correo = ?
        ''', (correo_ingresado,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        # 1. Validación: ¿El usuario existe?
        if usuario is None:
            flash("El correo institucional no se encuentra registrado.", "danger")
            return redirect(url_for('login'))
            
        # 2. Validación: ¿El usuario está activo? (Control de seguridad)
        elif usuario['activo'] == 0:
            flash("Este usuario se encuentra inactivo. Contacta al administrador.", "danger")
            return redirect(url_for('login'))
            
        # 3. Validación: ¿La contraseña es correcta?
        elif usuario['password'] != password_ingresada:
            flash("La contraseña ingresada es incorrecta.", "danger")
            return redirect(url_for('login'))
            
        # 4. CASO DE ÉXITO: El usuario es válido, está activo y la contraseña coincide
        else:
            # Guardamos las variables requeridas tanto por layout como por auth.py
            session['usuario_id'] = usuario['id_usuario']
            session['nombre'] = usuario['nombre']
            session['rol_id'] = usuario['id_rol']
            
            # CLAVE EXCLUSIVA PARA EL DECORADOR: Guardamos el texto (ej: "Psiquiatra")
            session['rol_nombre'] = usuario['rol_nombre']
            
            return redirect(url_for('pacientes'))
            
    return render_template('login.html')

# --- RUTA PACIENTES ---
@app.route('/pacientes')
def pacientes():
    search_query = request.args.get('q', '').strip()
    
    db_path = os.path.join(os.path.dirname(__file__), 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # === CONSULTAS ESTADÍSTICAS AUTOMÁTICAS ===
    cursor.execute("SELECT COUNT(*) AS total FROM PACIENTES")
    total_registrados = cursor.fetchone()['total'] or 0

    cursor.execute("SELECT COUNT(*) AS activos FROM PACIENTES WHERE estado = 'Hospitalizado'")
    total_hospitalizados = cursor.fetchone()['activos'] or 0

    cursor.execute("SELECT nombre FROM PACIENTES ORDER BY id_paciente DESC LIMIT 1")
    ultimo_registro = cursor.fetchone()
    ultimo_ingreso = ultimo_registro['nombre'] if ultimo_registro else "Ninguno"
    
    # === CONSULTA DE BÚSQUEDA Y FILTRADO ===
    base_sql = """
        SELECT 
            p.id_paciente,
            p.nombre,
            p.documento,
            p.codigo_unico,
            p.genero,
            p.estado,
            ((p.id_paciente * 2) % 40 + 22) AS edad,
            COALESCE(d.descripcion, 'Sin Diagnóstico Principal') AS diagnostico
        FROM PACIENTES p
        LEFT JOIN HISTORIAL_CLINICO h ON p.id_paciente = h.id_paciente
        LEFT JOIN DIAGNOSTICOS d ON h.id_historial = d.id_historial
    """
    
    if search_query:
        sql = base_sql + " WHERE p.nombre LIKE ? OR p.documento LIKE ? OR p.codigo_unico LIKE ?"
        cursor.execute(sql, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute(base_sql)
        
    lista_pacientes = cursor.fetchall()
    conn.close()
    
    datos_user = obtener_datos_usuario()
    
    return render_template(
        'pacientes.html', 
        pacientes=lista_pacientes, 
        search_query=search_query,
        total_registrados=total_registrados,
        total_hospitalizados=total_hospitalizados,
        ultimo_ingreso=ultimo_ingreso,
        usuario_nombre=datos_user["usuario_nombre"],
        usuario_rol=datos_user["usuario_rol"]
    )


# --- RUTA HISTORIAL ---
@app.route('/historial')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def historial():
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    historiales = conn.execute('''
        SELECT h.id_historial, h.fecha, p.nombre, p.documento 
        FROM HISTORIAL_CLINICO h
        INNER JOIN PACIENTES p ON h.id_paciente = p.id_paciente
    ''').fetchall()
    conn.close()
    
    datos_user = obtener_datos_usuario()
    return render_template(
        'historial.html', 
        historiales=historiales,
        usuario_nombre=datos_user["usuario_nombre"],
        usuario_rol=datos_user["usuario_rol"]
    )


# --- RUTA EVALUACIONES ---
@app.route('/evaluaciones')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def evaluaciones():
    datos_user = obtener_datos_usuario()
    return render_template('evaluaciones.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA INTERNAMIENTOS ---
@app.route('/internamientos')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def internamientos():
    datos_user = obtener_datos_usuario()
    return render_template('internamientos.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA MEDICAMENTOS ---
@app.route('/medicamentos', methods=['GET', 'POST'])
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def medicamentos():
    db_path = os.path.join(BASE_DIR, 'sigap.db')
    
    if request.method == 'POST':
        nombre_med = request.form.get('nombre_medicamento', '').strip()
        cantidad_med = request.form.get('cantidad', '').strip()
        
        if not nombre_med or not cantidad_med:
            flash("Todos los campos son obligatorios.")
        else:
            try:
                cantidad_int = int(cantidad_med)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 1. Verificar si el medicamento ya existe en la tabla MEDICAMENTOS
                cursor.execute('SELECT id_medicamento FROM MEDICAMENTOS WHERE LOWER(nombre) = LOWER(?)', (nombre_med,))
                existe_med = cursor.fetchone()
                
                if existe_med:
                    id_med = existe_med[0]
                else:
                    # Si no existe, lo insertamos
                    cursor.execute('INSERT INTO MEDICAMENTOS (nombre) VALUES (?)', (nombre_med,))
                    id_med = cursor.lastrowid
                
                # 2. Verificar si ya tiene un registro en la tabla INVENTARIO
                cursor.execute('SELECT id_inventario, cantidad FROM INVENTARIO WHERE id_medicamento = ?', (id_med,))
                existe_inv = cursor.fetchone()
                
                if existe_inv:
                    # Si ya existe en inventario, sumamos la nueva cantidad al stock actual
                    nueva_cantidad = existe_inv[1] + cantidad_int
                    cursor.execute('UPDATE INVENTARIO SET cantidad = ? WHERE id_medicamento = ?', (nueva_cantidad, id_med))
                else:
                    # Si es nuevo en el inventario, lo insertamos directo
                    cursor.execute('INSERT INTO INVENTARIO (id_medicamento, cantidad) VALUES (?, ?)', (id_med, cantidad_int))
                
                conn.commit()
                conn.close()
                flash(f"Stock de {nombre_med} actualizado correctamente.")
                return redirect(url_for('medicamentos'))
                
            except ValueError:
                flash("La cantidad debe ser un número entero válido.")
            except Exception as e:
                flash(f"Error en la base de datos: {str(e)}")

    # LÓGICA GET: Renderizar la tabla con los datos actuales
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    meds = conn.execute('''
        SELECT m.nombre, COALESCE(i.cantidad, 0) as cantidad 
        FROM MEDICAMENTOS m
        LEFT JOIN INVENTARIO i ON m.id_medicamento = i.id_medicamento
        ORDER BY m.nombre ASC
    ''').fetchall()
    conn.close()
    
    datos_user = obtener_datos_usuario()
    return render_template(
        'medicamentos.html', 
        medicamentos=meds,
        usuario_nombre=datos_user["usuario_nombre"],
        usuario_rol=datos_user["usuario_rol"]
)


# --- RUTA VISITAS ---
@app.route('/visitas')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def visitas():
    datos_user = obtener_datos_usuario()
    return render_template('visitas.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA PERMISOS ---
@app.route('/permisos')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def permisos():
    datos_user = obtener_datos_usuario()
    return render_template('permisos.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA USUARIOS ---
@app.route('/usuarios')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def usuarios():
    datos_user = obtener_datos_usuario()
    return render_template('usuarios.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA AUDITORÍA ---
@app.route('/auditoria')
@requiere_rol('administrador', 'psiquiatra', 'médico general', 'nutricionista')
def auditoria():
    datos_user = obtener_datos_usuario()
    return render_template('auditoria.html', usuario_nombre=datos_user["usuario_nombre"], usuario_rol=datos_user["usuario_rol"])


# --- RUTA LOGOUT ---
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)