from flask import Blueprint, jsonify, render_template
# Crea el blueprint principal de la aplicación
bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    """Página principal del panel."""
    return render_template("index.html")


@bp.route("/api/containers")
def list_containers():
    """Devuelve la lista de contenedores en formato JSON."""
    from app.docker_manager import list_all_containers
    contenedores = list_all_containers()
    return jsonify(contenedores)


@bp.route("/api/containers/test", methods=["POST"])
def create_test():
    """Crea el contenedor de prueba."""
    from app.docker_manager import create_test_container
    resultado = create_test_container()
    return jsonify(resultado), 201


@bp.route("/api/containers/test", methods=["DELETE"])
def delete_test():
    """Borra el contenedor de prueba."""
    from app.docker_manager import delete_test_container
    resultado = delete_test_container()
    return jsonify(resultado)


@bp.route("/api/stacks/lamp", methods=["POST"])
def deploy_lamp_stack():
    """Despliega un stack LAMP."""
    from app.stacks.lamp import deploy_lamp
    resultado = deploy_lamp()
    return jsonify(resultado), 201