import os
import traceback
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

# Cargar variables del fichero .env
load_dotenv()


def create_app():
    """Construye y devuelve la instancia de Flask."""
    app = Flask(__name__)

    # Clave para firmar cookies de sesión (debe estar en .env)
    app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

    # Mantener acentos en respuestas JSON
    app.json.ensure_ascii = False

    # Registra las rutas (endpoints)
    from app.routes import bp
    app.register_blueprint(bp)

    # Registra los manejadores globales de errores
    _registrar_manejadores_errores(app)

    return app


def _registrar_manejadores_errores(app):
    """
    Captura cualquier excepción que escape de un endpoint y la convierte
    en una respuesta JSON limpia con código HTTP apropiado.
    """

    @app.errorhandler(HTTPException)
    def manejar_http_exception(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def manejar_excepcion_generica(e):
        app.logger.error(f"Excepción no controlada: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "error": "Error interno del servidor. Consulta los logs del backend."
        }), 500