# sigap_backend/auth.py
from functools import wraps
from flask import session, redirect, url_for, abort

def requiere_rol(*roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            if session.get('rol') not in roles_permitidos:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
