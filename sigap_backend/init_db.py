# sigap_backend/init_db.py
import sqlite3
import os

def crear_base_de_datos():
    # Nos aseguramos de crearla en la misma carpeta que este script
    db_path = os.path.join(os.path.dirname(__file__), 'sigap.db')
    
    # ⚠️ ELIMINAR BASE DE DATOS ANTERIOR SI EXISTE PARA EVITAR CONFLICTOS DE ESTRUCTURA
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Habilitar el soporte estricto de llaves foráneas en SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    print("Creando tablas del modelo relacional S.I.G.A.P... ")

    # 1. TABLA ROLES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ROLES (
        id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    ''')

    # 2. TABLA USUARIOS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS USUARIOS (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT NOT NULL UNIQUE,
        correo TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        activo INTEGER DEFAULT 1, -- 1 para activo, 0 para inactivo (Auditoría)
        id_rol INTEGER NOT NULL,
        FOREIGN KEY (id_rol) REFERENCES ROLES (id_rol) ON DELETE RESTRICT
    )
    ''')

    # 3. TABLA PACIENTES (Tu estructura exacta original)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PACIENTES (
        id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT NOT NULL UNIQUE,
        codigo_unico TEXT NOT NULL UNIQUE,
        genero TEXT,
        estado TEXT NOT NULL,
        id_usuario INTEGER, -- Usuario (médico/psiquiatra) que lo atiende
        FOREIGN KEY (id_usuario) REFERENCES USUARIOS (id_usuario) ON DELETE SET NULL
    )
    ''')

    # 4. TABLA HISTORIAL CLINICO
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS HISTORIAL_CLINICO (
        id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        id_paciente INTEGER NOT NULL UNIQUE, -- Relación 1 a 1 con Pacientes
        FOREIGN KEY (id_paciente) REFERENCES PACIENTES (id_paciente) ON DELETE CASCADE
    )
    ''')

    # 5. TABLA DIAGNOSTICOS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DIAGNOSTICOS (
        id_diagnostico INTEGER PRIMARY KEY AUTOINCREMENT,
        descripcion TEXT NOT NULL,
        fecha TEXT NOT NULL,
        id_historial INTEGER NOT NULL,
        FOREIGN KEY (id_historial) REFERENCES HISTORIAL_CLINICO (id_historial) ON DELETE CASCADE
    )
    ''')

    # 6. TABLA NOTAS CLINICAS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS NOTAS_CLINICAS (
        id_nota INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL, -- Psiquiatría, Psicología, Nutrición, etc.
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        id_historial INTEGER NOT NULL,
        FOREIGN KEY (id_historial) REFERENCES HISTORIAL_CLINICO (id_historial) ON DELETE CASCADE
    )
    ''')

    # 7. TABLA FAMILIARES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS FAMILIARES (
        id_familiar INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT,
        parentesco TEXT NOT NULL,
        id_paciente INTEGER NOT NULL,
        FOREIGN KEY (id_paciente) REFERENCES PACIENTES (id_paciente) ON DELETE CASCADE
    )
    ''')

    # 8. TABLA VISITAS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS VISITAS (
        id_visitante INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL,
        id_familiar INTEGER NOT NULL,
        FOREIGN KEY (id_familiar) REFERENCES FAMILIARES (id_familiar) ON DELETE CASCADE
    )
    ''')

    # 9. TABLA INCIDENTES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS INCIDENTES (
        id_incidente INTEGER PRIMARY KEY AUTOINCREMENT,
        gravedad TEXT NOT NULL,
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        id_paciente INTEGER NOT NULL,
        FOREIGN KEY (id_paciente) REFERENCES PACIENTES (id_paciente) ON DELETE CASCADE
    )
    ''')

    # 10. TABLA MEDICAMENTOS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MEDICAMENTOS (
        id_medicamento INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    ''')

    # 11. TABLA INVENTARIO
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS INVENTARIO (
        id_inventario INTEGER PRIMARY KEY AUTOINCREMENT,
        cantidad INTEGER NOT NULL DEFAULT 0,
        id_medicamento INTEGER NOT NULL UNIQUE, -- Relación 1 a 1 con Medicamentos
        FOREIGN KEY (id_medicamento) REFERENCES MEDICAMENTOS (id_medicamento) ON DELETE CASCADE
    )
    ''')

    # 12. TABLA HABITACIONES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS HABITACIONES (
        id_habitacion INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL UNIQUE,
        capacidad INTEGER NOT NULL
    )
    ''')

    # 13. TABLA OBSERVACIONES AUXILIARES (Enfermería / Cuidadores)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS OBSERVACIONES_AUXILIARES (
        id_observacion INTEGER PRIMARY KEY AUTOINCREMENT,
        comportamiento TEXT,
        higiene TEXT,
        fecha TEXT NOT NULL,
        id_habitacion INTEGER NOT NULL,
        FOREIGN KEY (id_habitacion) REFERENCES HABITACIONES (id_habitacion) ON DELETE CASCADE
    )
    ''')

    # 14. TABLA ASIGNACIONES HABITACION
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ASIGNACIONES_HABITACION (
        id_asignacion INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_entrada TEXT NOT NULL,
        fecha_salida TEXT,
        activa INTEGER DEFAULT 1,
        id_paciente INTEGER NOT NULL,
        id_habitacion INTEGER NOT NULL,
        FOREIGN KEY (id_paciente) REFERENCES PACIENTES (id_paciente) ON DELETE CASCADE,
        FOREIGN KEY (id_habitacion) REFERENCES HABITACIONES (id_habitacion) ON DELETE CASCADE
    )
    ''')

    # 15. TABLA PRESCRIPCIONES (Recetas médicas)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PRESCRIPCIONES (
        id_prescripcion INTEGER PRIMARY KEY AUTOINCREMENT,
        frecuencia TEXT NOT NULL,
        dosis TEXT NOT NULL,
        estado TEXT NOT NULL,
        fecha_inicio TEXT NOT NULL,
        id_paciente INTEGER NOT NULL,
        id_medicamento INTEGER NOT NULL,
        FOREIGN KEY (id_paciente) REFERENCES PACIENTES (id_paciente) ON DELETE CASCADE,
        FOREIGN KEY (id_medicamento) REFERENCES MEDICAMENTOS (id_medicamento) ON DELETE CASCADE
    )
    ''')

    # 16. TABLA ADMINISTRACION MEDICAMENTOS (Kardex / Registro diario de toma)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ADMINISTRACION_MEDICAMENTOS (
        id_administracion INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        observacion TEXT,
        id_asignacion INTEGER NOT NULL,
        FOREIGN KEY (id_asignacion) REFERENCES ASIGNACIONES_HABITACION (id_asignacion) ON DELETE CASCADE
    )
    ''')

    # --- INSERCIÓN DE DATOS DE PRUEBA OBLIGATORIOS ---
    print("Insertando roles y usuarios semilla...")
    
    # Insertar Roles
    roles = ['administrador', 'psiquiatra', 'medico', 'nutricionista']
    for r in roles:
        cursor.execute("INSERT OR IGNORE INTO ROLES (nombre) VALUES (?)", (r,))
        
    # Insertar Usuarios Institucionales Reales
    usuarios = [
        ('Laura Londoño', '23456789', 'llondoño@sigap.com', 'admin123', 1),
        ('Carlos Martínez', '12345678', 'cmartinez@sigap.com', 'dr12234', 2),
        ('Juan Arboleda', '34567890', 'jarboleda@sigap.com', 'medico123', 3),
        ('Ana Santos', '45678901', 'asantos@sigap.com', 'nutri123', 4)
    ]

    for nombre, doc, correo, password, rol_id in usuarios:
        cursor.execute('''
        INSERT OR IGNORE INTO USUARIOS (nombre, documento, correo, password, id_rol, activo)
        VALUES (?, ?, ?, ?, ?, 1)
        ''', (nombre, doc, correo, password, rol_id))

    # CORRECCIÓN DE LA LISTA DE PACIENTES: Mapeada exactamente a tus campos reales
    # (nombre, documento, codigo_unico, genero, estado, id_usuario)
    pacientes = [
        ('Laura Martínez González', '1020456789', 'P-102045', 'Femenino', 'Hospitalizado', 2),
        ('Andrés Felipe Córdoba', '1032456112', 'P-103245', 'Masculino', 'Alta Médica', 2),
        ('Ana María Restrepo', '1017234567', 'P-101723', 'Femenino', 'Hospitalizado', 3),
        ('Carlos Eduardo Gómez', '79845123', 'P-798451', 'Masculino', 'Hospitalizado', 3),
        ('Diana Carolina Hoyos', '1037654321', 'P-103765', 'Femenino', 'Alta Médica', 4),
        ('Santiago Cruz Morales', '1022345987', 'P-102234', 'Masculino', 'Hospitalizado', 2),
        ('María Camila Osorio', '1152439876', 'P-115243', 'Femenino', 'Hospitalizado', 2),
        ('Juan Fernando Quintero', '71234567', 'P-712345', 'Masculino', 'Alta Médica', 3),
        ('Sandra Milena Patiño', '43210987', 'P-432109', 'Femenino', 'Hospitalizado', 2),
        ('Alejandro Tobón Ruiz', '1015432765', 'P-101543', 'Masculino', 'Alta Médica', 3),
        ('Beatriz Elena Cano', '32456123', 'P-324561', 'Femenino', 'Hospitalizado', 2),
        ('Ricardo Antonio Marín', '9876543', 'P-987654', 'Masculino', 'Hospitalizado', 3),
        ('Valentina Villa Bedoya', '1039485761', 'P-103948', 'Femenino', 'Hospitalizado', 4),
        ('Mateo Aristizábal', '1026417283', 'P-102641', 'Masculino', 'Alta Médica', 3),
        ('Olga Lucía Henao', '21654987', 'P-216549', 'Femenino', 'Alta Médica', 3),
        ('Daniel Estiven Plaza', '1045231987', 'P-104523', 'Masculino', 'Hospitalizado', 2),
        ('Paola Andrea Murillo', '1010203040', 'P-101020', 'Femenino', 'Hospitalizado', 2),
        ('Jorge Eliecer Tascón', '16785432', 'P-167854', 'Masculino', 'Alta Médica', 3),
        ('Clara Inés Saldarriaga', '42156874', 'P-421568', 'Femenino', 'Hospitalizado', 2),
        ('Gabriel Jaime Ochoa', '70543219', 'P-705432', 'Masculino', 'Hospitalizado', 3),
        ('Natalia Sofía Vargas', '1128456123', 'P-112845', 'Femenino', 'Alta Médica', 4),
        ('Fabián Humberto Rojas', '80123456', 'P-801234', 'Masculino', 'Hospitalizado', 2),
        ('Gloria Amparo Benítez', '24356781', 'P-243567', 'Femenino', 'Hospitalizado', 2),
        ('Sebastián Muñoz Loaiza', '1036452198', 'P-103645', 'Masculino', 'Alta Médica', 3),
        ('Juliana Marcela Ortiz', '1018345672', 'P-101834', 'Femenino', 'Hospitalizado', 2),
        ('Héctor Fabio Gutiérrez', '94512384', 'P-945123', 'Masculino', 'Alta Médica', 3),
        ('Liliana María Zuluaga', '43876543', 'P-438765', 'Femenino', 'Hospitalizado', 2),
        ('Mauricio de J. Franco', '75124365', 'P-751243', 'Masculino', 'Hospitalizado', 3),
        ('Manuela Gómez Herrera', '1035429811', 'P-103542', 'Femenino', 'Alta Médica', 4),
        ('Alfonso Reyes Suárez', '19432567', 'P-194325', 'Masculino', 'Hospitalizado', 2)
    ]

    print("Insertando registros de pacientes...")
    cursor.executemany("""
    INSERT INTO PACIENTES (nombre, documento, codigo_unico, genero, estado, id_usuario) 
    VALUES (?, ?, ?, ?, ?, ?)
    """, pacientes)
    
    conn.commit()
    conn.close()
    print("¡Felicidades! Toda la estructura y datos de prueba han sido creados con éxito en 'sigap.db'.")

if __name__ == '__main__':
    crear_base_de_datos()