import os
import grp
import uuid
import subprocess
import docker
from app.port_manager import get_free_port

client = docker.from_env()

STACKS_DATA_DIR = "/home/damg/stacks_data"


def _pull_imagenes():
    """Descarga las imágenes necesarias si no están en local."""
    client.images.pull("nginx", tag="alpine")
    client.images.pull("php", tag="8.2-fpm")
    client.images.pull("mysql", tag="8.0")


def _crear_index_bienvenida(ruta_www, mysql_host):
    """Crea un index.php de bienvenida en la carpeta del stack."""
    contenido = """<?php
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Stack LEMP listo</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               max-width: 700px; margin: 3rem auto; padding: 1rem; line-height: 1.6;
               background: #f5f7fa; color: #1a1a1a; }
        h1 { color: #1fb57f; }
        .card { background: white; padding: 1.5rem; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1rem; }
        code { background: #f0f0f0; padding: 0.15rem 0.4rem; border-radius: 3px;
               font-size: 0.95em; }
        .ok { color: #1fb57f; font-weight: bold; }
        .warn { color: #e55934; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Stack LEMP desplegado correctamente</h1>
    <div class="card">
        <p><strong>Versión PHP:</strong> <?php echo phpversion(); ?></p>
        <p><strong>Servidor:</strong> <?php echo $_SERVER['SERVER_SOFTWARE']; ?></p>
        <p><strong>Estado MySQL:</strong>
        <?php
        $conn = @mysqli_connect("__MYSQL_HOST__", "appuser", "apppass", "appdb");
        if ($conn) {
            echo '<span class="ok">conectado correctamente</span>';
            mysqli_close($conn);
        } else {
            echo '<span class="warn">inicializando, espera...</span>';
            echo '<script>setTimeout(function(){ location.reload(); }, 3000);</script>';
        }
        ?>
        </p>
    </div>
    <div class="card">
        <h3>¿Cómo subir tu código?</h3>
        <p>Reemplaza este fichero (<code>index.php</code>) por el código de tu aplicación en la carpeta compartida del stack.</p>
        <p>Cualquier fichero <code>.php</code>, <code>.html</code>, CSS o JS que coloques ahí será servido automáticamente.</p>
    </div>
</body>
</html>
"""
    contenido = contenido.replace("__MYSQL_HOST__", mysql_host)
    with open(os.path.join(ruta_www, "index.php"), "w", encoding="utf-8") as f:
        f.write(contenido)


def _crear_nginx_conf(ruta_stack, php_fpm_host):
    """Genera el fichero default.conf de Nginx que delega los .php a PHP-FPM."""
    config = """server {
    listen 80 default_server;
    server_name _;
    root /var/www/html;
    index index.php index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \\.php$ {
        fastcgi_pass __PHP_FPM_HOST__:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\\.ht {
        deny all;
    }
}
"""
    config = config.replace("__PHP_FPM_HOST__", php_fpm_host)
    ruta_conf = os.path.join(ruta_stack, "nginx.conf")
    with open(ruta_conf, "w", encoding="utf-8") as f:
        f.write(config)
    return ruta_conf


def _aplicar_permisos_equipo(ruta, equipo):
    """
    Aplica permisos a la carpeta del stack para que solo el grupo
    del equipo asignado pueda acceder, más una ACL para que el usuario
    www-data del contenedor (UID 33) pueda leer los ficheros.
    """
    grupo_linux = f"team_{equipo}"

    try:
        grp.getgrnam(grupo_linux)
    except KeyError:
        raise ValueError(f"El grupo {grupo_linux} no existe en el sistema")

    subprocess.run(["sudo", "chown", "-R", f"root:{grupo_linux}", ruta], check=True)
    subprocess.run(["sudo", "chmod", "-R", "u=rwX,g=rwX,o=", ruta], check=True)
    # ACL para www-data (PHP-FPM, UID 33)
    subprocess.run(["sudo", "setfacl", "-R", "-m", "u:33:rX", ruta], check=True)
    subprocess.run(["sudo", "setfacl", "-R", "-d", "-m", "u:33:rX", ruta], check=True)
    # ACL para nginx (UID 101 en alpine)
    subprocess.run(["sudo", "setfacl", "-R", "-m", "u:101:rX", ruta], check=True)
    subprocess.run(["sudo", "setfacl", "-R", "-d", "-m", "u:101:rX", ruta], check=True)

def deploy_lemp(equipo):
    """
    Despliega un stack LEMP: Nginx + PHP-FPM + MySQL.

    Crea una red aislada, un volumen para MySQL, una carpeta compartida
    entre Nginx y PHP-FPM (para que el developer suba código) y los
    tres contenedores con un nombre único.

    Returns:
        dict: información del stack desplegado.
    """
    _pull_imagenes()

    sufijo = uuid.uuid4().hex[:6]
    nombre_stack = f"lemp_{sufijo}"

    red_nombre = f"{nombre_stack}_red"
    volumen_db = f"{nombre_stack}_db"
    mysql_nombre = f"{nombre_stack}_mysql"
    php_nombre = f"{nombre_stack}_php"
    nginx_nombre = f"{nombre_stack}_nginx"

    # Carpeta del stack: contendrá www/ y nginx.conf
    ruta_stack = os.path.join(STACKS_DATA_DIR, nombre_stack)
    ruta_www = os.path.join(ruta_stack, "www")
    os.makedirs(ruta_www, exist_ok=True)

    # index.php de bienvenida
    _crear_index_bienvenida(ruta_www, mysql_nombre)

    # Config de Nginx con el nombre del contenedor PHP-FPM
    ruta_nginx_conf = _crear_nginx_conf(ruta_stack, php_nombre)

    # Permisos del equipo (sobre toda la carpeta del stack)
    _aplicar_permisos_equipo(ruta_stack, equipo)

    # Red aislada
    client.networks.create(red_nombre, driver="bridge")

    # Volumen MySQL
    client.volumes.create(volumen_db)

    # Contenedor MySQL
    client.containers.run(
        image="mysql:8.0",
        name=mysql_nombre,
        network=red_nombre,
        volumes={volumen_db: {"bind": "/var/lib/mysql", "mode": "rw"}},
        environment={
            "MYSQL_ROOT_PASSWORD": "rootpass",
            "MYSQL_DATABASE": "appdb",
            "MYSQL_USER": "appuser",
            "MYSQL_PASSWORD": "apppass",
        },
        mem_limit="512m",
        detach=True,
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "lemp",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Contenedor PHP-FPM con mysqli pre-instalado
    client.containers.run(
        image="php:8.2-fpm",
        name=php_nombre,
        network=red_nombre,
        volumes={ruta_www: {"bind": "/var/www/html", "mode": "rw"}},
        mem_limit="256m",
        detach=True,
        command=[
            "bash", "-c",
            "docker-php-ext-install mysqli && php-fpm"
        ],
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "lemp",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Puerto público para Nginx
    puerto_web = get_free_port()

    # Contenedor Nginx (sirve estáticos y delega PHP a PHP-FPM)
    client.containers.run(
        image="nginx:alpine",
        name=nginx_nombre,
        network=red_nombre,
        ports={"80/tcp": puerto_web},
        volumes={
            ruta_www: {"bind": "/var/www/html", "mode": "ro"},
            ruta_nginx_conf: {"bind": "/etc/nginx/conf.d/default.conf", "mode": "ro"},
        },
        mem_limit="128m",
        detach=True,
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "lemp",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Esperar a que PHP-FPM instale mysqli y arranque
    import time
    time.sleep(8)

    return {
        "stack": nombre_stack,
        "tipo": "lemp",
        "equipo": equipo,
        "puerto": puerto_web,
        "url": f"http://localhost:{puerto_web}",
        "ruta_codigo": ruta_www,
        "contenedores": [mysql_nombre, php_nombre, nginx_nombre],
    }


def delete_lemp(nombre_stack):
    """
    Elimina un stack LEMP completo: contenedores, red, volumen
    y carpeta de código del developer.
    """
    red_nombre = f"{nombre_stack}_red"
    volumen_db = f"{nombre_stack}_db"
    mysql_nombre = f"{nombre_stack}_mysql"
    php_nombre = f"{nombre_stack}_php"
    nginx_nombre = f"{nombre_stack}_nginx"

    for nombre in [nginx_nombre, php_nombre, mysql_nombre]:
        try:
            c = client.containers.get(nombre)
            c.stop()
            c.remove()
        except docker.errors.NotFound:
            pass

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