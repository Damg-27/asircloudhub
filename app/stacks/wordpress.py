import os
import time
import grp
import uuid
import subprocess
import docker
from app.port_manager import get_free_port

client = docker.from_env()

STACKS_DATA_DIR = "/home/damg/stacks_data"


def _pull_imagenes():
    """Descarga las imágenes necesarias si no están en local."""
    client.images.pull("mariadb", tag="11")
    client.images.pull("wordpress", tag="latest")


def _aplicar_permisos_equipo(ruta, equipo):
    """
    Aplica permisos a la carpeta del stack para que solo el grupo
    del equipo asignado pueda acceder, más ACL para el usuario web
    del contenedor (UID 33 = www-data en la imagen de WordPress).
    """
    grupo_linux = f"team_{equipo}"

    try:
        grp.getgrnam(grupo_linux)
    except KeyError:
        raise ValueError(f"El grupo {grupo_linux} no existe en el sistema")

    subprocess.run(["sudo", "chown", "-R", f"root:{grupo_linux}", ruta], check=True)
    subprocess.run(["sudo", "chmod", "-R", "u=rwX,g=rwX,o=", ruta], check=True)

    # ACL para www-data (UID 33) - usuario que ejecuta WordPress/Apache
    subprocess.run(["sudo", "setfacl", "-R", "-m", "u:33:rwX", ruta], check=True)
    subprocess.run(["sudo", "setfacl", "-R", "-d", "-m", "u:33:rwX", ruta], check=True)


def deploy_wordpress(equipo):
    """
    Despliega un stack WordPress: WordPress (Apache+PHP) + MariaDB.

    A diferencia de LAMP/LEMP, no inyectamos un index.php de bienvenida:
    WordPress trae su propio asistente de instalación que se mostrará al
    abrir la URL por primera vez.

    Returns:
        dict: información del stack desplegado.
    """
    _pull_imagenes()

    sufijo = uuid.uuid4().hex[:6]
    nombre_stack = f"wp_{sufijo}"

    red_nombre = f"{nombre_stack}_red"
    volumen_db = f"{nombre_stack}_db"
    mariadb_nombre = f"{nombre_stack}_mariadb"
    wp_nombre = f"{nombre_stack}_wp"

    # Carpeta del stack
    ruta_stack = os.path.join(STACKS_DATA_DIR, nombre_stack)
    ruta_www = os.path.join(ruta_stack, "www")
    os.makedirs(ruta_www, exist_ok=True)

    # Permisos del equipo - rwX (con W) porque WordPress necesita escribir
    # (subida de medios, instalación de plugins, etc.)
    _aplicar_permisos_equipo(ruta_stack, equipo)

    # Red aislada
    client.networks.create(red_nombre, driver="bridge")

    # Volumen MariaDB
    client.volumes.create(volumen_db)

    # Contenedor MariaDB
    client.containers.run(
        image="mariadb:11",
        name=mariadb_nombre,
        network=red_nombre,
        volumes={volumen_db: {"bind": "/var/lib/mysql", "mode": "rw"}},
        environment={
            "MARIADB_ROOT_PASSWORD": "rootpass",
            "MARIADB_DATABASE": "wordpress",
            "MARIADB_USER": "wpuser",
            "MARIADB_PASSWORD": "wppass",
        },
        mem_limit="512m",
        detach=True,
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "wordpress",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Puerto público para WordPress
    puerto_web = get_free_port()

    # Contenedor WordPress (ya trae Apache + PHP + WordPress + mysqli)
    client.containers.run(
        image="wordpress:latest",
        name=wp_nombre,
        network=red_nombre,
        ports={"80/tcp": puerto_web},
        volumes={ruta_www: {"bind": "/var/www/html", "mode": "rw"}},
        environment={
            "WORDPRESS_DB_HOST": mariadb_nombre,
            "WORDPRESS_DB_NAME": "wordpress",
            "WORDPRESS_DB_USER": "wpuser",
            "WORDPRESS_DB_PASSWORD": "wppass",
        },
        mem_limit="384m",
        detach=True,
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "wordpress",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Esperar a que WordPress copie sus ficheros al volumen montado

    time.sleep(10)
# Si phpMyAdmin está desplegado, conectarlo a la red de este stack
    from app.stacks.phpmyadmin import conectar_a_red
    conectar_a_red(red_nombre)

    return {
        "stack": nombre_stack,
        "tipo": "wordpress",
        "equipo": equipo,
        "puerto": puerto_web,
        "url": f"http://localhost:{puerto_web}",
        "ruta_codigo": ruta_www,
        "contenedores": [mariadb_nombre, wp_nombre],
    }


def delete_wordpress(nombre_stack):
    """
    Elimina un stack WordPress completo: contenedores, red, volumen
    y carpeta de código.
    """
    red_nombre = f"{nombre_stack}_red"
    volumen_db = f"{nombre_stack}_db"
    mariadb_nombre = f"{nombre_stack}_mariadb"
    wp_nombre = f"{nombre_stack}_wp"

    for nombre in [wp_nombre, mariadb_nombre]:
        try:
            c = client.containers.get(nombre)
            c.stop()
            c.remove()
        except docker.errors.NotFound:
            pass
    
    from app.stacks.phpmyadmin import desconectar_de_red
    desconectar_de_red(red_nombre)
    try:
        client.networks.get(red_nombre).remove()
    except docker.errors.NotFound:
        pass

    try:
        client.volumes.get(volumen_db).remove()
    except docker.errors.NotFound:
        pass

    ruta_stack = os.path.join(STACKS_DATA_DIR, nombre_stack)
    if os.path.isdir(ruta_stack):
        subprocess.run(["sudo", "rm", "-rf", ruta_stack], check=True)

    return {"mensaje": f"Stack {nombre_stack} eliminado"}