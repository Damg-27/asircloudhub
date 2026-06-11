import os
from functools import wraps
from flask import session, redirect, url_for, request, jsonify


def cargar_credenciales():
    """Lee usuario y contraseña del admin desde las variables de entorno."""
    return {
        "usuario": os.environ.get("ADMIN_USER", "admin"),
        "password": os.environ.get("ADMIN_PASS", "admin"),
    }


def credenciales_validas(usuario, password):
    """Verifica si las credenciales proporcionadas coinciden con las del admin."""
    creds = cargar_credenciales()
    return usuario == creds["usuario"] and password == creds["password"]


def esta_logeado():
    """Devuelve True si hay sesión de admin activa."""
    return session.get("admin_logeado") is True


def login_admin():
    """Marca la sesión como autenticada."""
    session["admin_logeado"] = True


def logout_admin():
    """Cierra la sesión del admin."""
    session.pop("admin_logeado", None)


def requiere_login(f):
    """
    Decorador que protege un endpoint exigiendo sesión de admin activa.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not esta_logeado():
            if request.path.startswith("/api/"):
                return jsonify({"error": "No autenticado"}), 401
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return wrapper