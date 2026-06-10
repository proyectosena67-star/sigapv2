# sigap_backend/auth.py
from functools import wraps
from flask import session, redirect, url_for, abort

def requiere_rol(*roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('usuario_id'):
                return redirect(url_for('login'))
            
            # Limpiamos espacios extras y convertimos a minúsculas
            rol_usuario = str(session.get('rol_nombre') or '').strip().lower()
            
            # Limpiamos los roles permitidos también para que la comparación sea idéntica
            roles_permitidos_min = [str(r).strip().lower() for r in roles_permitidos]
            
            # IMPRESIÓN DE DEPURACIÓN (Mírala en tu terminal para ver qué texto exacto llega)
            print(f"DEBUG SIGAP - Rol en Sesión: '{rol_usuario}' | Permitidos: {roles_permitidos_min}")
            
            if rol_usuario not in roles_permitidos_min:
                abort(403) # Lanza el Forbidden si no coincide exactamente
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator