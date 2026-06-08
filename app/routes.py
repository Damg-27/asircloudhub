from flask import Blueprint, jsonify, render_template, request
# Crea el blueprint principal de la aplicación
bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    """Página principal del panel."""
    return render_template("index.html")

# API de stacks
@bp.route("/api/stacks", methods=["GET"])
def list_stacks():
    """Devuelve la lista de todos los stacks desplegados."""
    from app.docker_manager import list_all_stacks
    stacks = list_all_stacks()
    return jsonify(stacks)


EQUIPOS_VALIDOS = ["webdev", "backend", "marketing"]


@bp.route("/api/stacks/lamp", methods=["POST"])
def deploy_lamp_stack():
    """Despliega un stack LAMP asignado a un equipo."""
    from app.stacks.lamp import deploy_lamp

    datos = request.get_json(silent=True) or {}
    equipo = datos.get("equipo")

    if equipo not in EQUIPOS_VALIDOS:
        return jsonify({
            "error": f"Equipo no válido. Debe ser uno de: {', '.join(EQUIPOS_VALIDOS)}"
        }), 400

    resultado = deploy_lamp(equipo)
    return jsonify(resultado), 201


@bp.route("/api/stacks/lemp", methods=["POST"])
def deploy_lemp_stack():
    """Despliega un stack LEMP asignado a un equipo."""
    from app.stacks.lemp import deploy_lemp

    datos = request.get_json(silent=True) or {}
    equipo = datos.get("equipo")

    if equipo not in EQUIPOS_VALIDOS:
        return jsonify({
            "error": f"Equipo no válido. Debe ser uno de: {', '.join(EQUIPOS_VALIDOS)}"
        }), 400

    resultado = deploy_lemp(equipo)
    return jsonify(resultado), 201


@bp.route("/api/stacks/wordpress", methods=["POST"])
def deploy_wordpress_stack():
    """Despliega un stack WordPress asignado a un equipo."""
    from app.stacks.wordpress import deploy_wordpress

    datos = request.get_json(silent=True) or {}
    equipo = datos.get("equipo")

    if equipo not in EQUIPOS_VALIDOS:
        return jsonify({
            "error": f"Equipo no válido. Debe ser uno de: {', '.join(EQUIPOS_VALIDOS)}"
        }), 400

    resultado = deploy_wordpress(equipo)
    return jsonify(resultado), 201

@bp.route("/api/stacks/<nombre_stack>", methods=["DELETE"])
def delete_stack(nombre_stack):
    """Elimina un stack completo por su nombre."""
    if nombre_stack.startswith("lamp_"):
        from app.stacks.lamp import delete_lamp
        resultado = delete_lamp(nombre_stack)
    elif nombre_stack.startswith("lemp_"):
        from app.stacks.lemp import delete_lemp
        resultado = delete_lemp(nombre_stack)
    elif nombre_stack.startswith("wp_"):
        from app.stacks.wordpress import delete_wordpress
        resultado = delete_wordpress(nombre_stack)
    else:
        return jsonify({"error": f"Tipo de stack no reconocido: {nombre_stack}"}), 400

    return jsonify(resultado)

@bp.route("/api/limpiar", methods=["POST"])
def limpiar_huerfanos_endpoint():
    """Limpia volúmenes, redes y carpetas huérfanas del proyecto."""
    from app.docker_manager import limpiar_huerfanos
    informe = limpiar_huerfanos()
    return jsonify(informe)