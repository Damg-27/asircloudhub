from flask import Flask

def create_app():
    """Construye y devuelve la instancia de Flask."""
    app = Flask(__name__)

    # Registra las rutas (endpoints)
    from app.routes import bp
    app.register_blueprint(bp)

    return app


