from flask import Blueprint, jsonify, render_template, request, redirect, url_for
import docker

from app.auth import (
    credenciales_validas,
    esta_logeado,
    login_admin,
    logout_admin,
    requiere_login,
)

# Crea el blueprint principal de la aplicación
bp = Blueprint("main", __name__)

# Equipos válidos para asignar a un stack
EQUIPOS_VALIDOS = ["webdev", "backend", "marketing"]


# Autenticación

@bp.route("/login", methods=["GET", "POST"])
def login():
    """Página de login del admin."""
    if esta_logeado():
        return redirect(url_for("main.home"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        if credenciales_validas(usuario, password):
            login_admin()
            return redirect(url_for("main.home"))
        else:
            return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    """Cierra la sesión del admin."""
    logout_admin()
    return redirect(url_for("main.login"))


# Página principal (protegida)

@bp.route("/")
@requiere_login
def home():
    """Página principal del panel."""
    return render_template("index.html")

# API de stacks (toda protegida)

@bp.route("/api/stacks", methods=["GET"])
@requiere_login
def list_stacks():
    """Devuelve la lista de todos los stacks desplegados."""
    from app.docker_manager import list_all_stacks
    try:
        stacks = list_all_stacks()
        return jsonify(stacks)
    except Exception as e:
        return jsonify({"error": f"No se pudo obtener la lista de stacks: {str(e)}"}), 500


@bp.route("/api/stacks/lamp", methods=["POST"])
@requiere_login
def deploy_lamp_stack():
    """Despliega un stack LAMP asignado a un equipo."""
    from app.stacks.lamp import deploy_lamp
    return _desplegar_stack(deploy_lamp)


@bp.route("/api/stacks/lemp", methods=["POST"])
@requiere_login
def deploy_lemp_stack():
    """Despliega un stack LEMP asignado a un equipo."""
    from app.stacks.lemp import deploy_lemp
    return _desplegar_stack(deploy_lemp)


@bp.route("/api/stacks/wordpress", methods=["POST"])
@requiere_login
def deploy_wordpress_stack():
    """Despliega un stack WordPress asignado a un equipo."""
    from app.stacks.wordpress import deploy_wordpress
    return _desplegar_stack(deploy_wordpress)

@bp.route("/api/stacks/phpmyadmin", methods=["POST"])
@requiere_login
def deploy_phpmyadmin_stack():
    """Despliega el stack único de phpMyAdmin."""
    from app.stacks.phpmyadmin import deploy_phpmyadmin
    try:
        resultado = deploy_phpmyadmin()
        return jsonify(resultado), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except docker.errors.APIError as e:
        return jsonify({"error": f"Error de Docker: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"No se pudo desplegar phpMyAdmin: {str(e)}"}), 500

@bp.route("/api/stacks/<nombre_stack>", methods=["DELETE"])
@requiere_login
def delete_stack(nombre_stack):
    """Elimina un stack completo por su nombre."""
    try:
        if nombre_stack.startswith("lamp_"):
            from app.stacks.lamp import delete_lamp
            resultado = delete_lamp(nombre_stack)
        elif nombre_stack.startswith("lemp_"):
            from app.stacks.lemp import delete_lemp
            resultado = delete_lemp(nombre_stack)
        elif nombre_stack.startswith("wp_"):
            from app.stacks.wordpress import delete_wordpress
            resultado = delete_wordpress(nombre_stack)
        elif nombre_stack == "phpmyadmin":
            from app.stacks.phpmyadmin import delete_phpmyadmin
            resultado = delete_phpmyadmin(nombre_stack)
        else:
            return jsonify({
                "error": f"Tipo de stack no reconocido: {nombre_stack}"
            }), 400

        return jsonify(resultado)

    except docker.errors.APIError as e:
        return jsonify({"error": f"Error de Docker: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"No se pudo borrar el stack: {str(e)}"}), 500


# API de limpieza (protegida)

@bp.route("/api/limpiar", methods=["POST"])
@requiere_login
def limpiar_huerfanos_endpoint():
    """Limpia volúmenes, redes y carpetas huérfanas del proyecto."""
    from app.docker_manager import limpiar_huerfanos
    try:
        informe = limpiar_huerfanos()
        return jsonify(informe)
    except Exception as e:
        return jsonify({"error": f"No se pudo completar la limpieza: {str(e)}"}), 500



# Función auxiliar para los endpoints de despliegue

def _desplegar_stack(funcion_deploy):
    """Valida el equipo, ejecuta la función de despliegue y captura errores."""
    datos = request.get_json(silent=True) or {}
    equipo = datos.get("equipo")

    if equipo not in EQUIPOS_VALIDOS:
        return jsonify({
            "error": f"Equipo no válido. Debe ser uno de: {', '.join(EQUIPOS_VALIDOS)}"
        }), 400

    try:
        resultado = funcion_deploy(equipo)
        return jsonify(resultado), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except docker.errors.APIError as e:
        return jsonify({"error": f"Error de Docker: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"No se pudo desplegar el stack: {str(e)}"}), 500