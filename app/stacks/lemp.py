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
    client.images.pull("nginx", tag="alpine")
    client.images.pull("php", tag="8.2-fpm")
    client.images.pull("mysql", tag="8.0")


def _crear_index_bienvenida(ruta_www, mysql_host):
    """Crea un index.php de bienvenida con guía completa para el developer."""
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
               max-width: 800px; margin: 2rem auto; padding: 1rem; line-height: 1.6;
               background: #f5f7fa; color: #1a1a1a; }
        h1 { color: #1fb57f; }
        h3 { color: #475569; margin-top: 1.5rem; }
        .card { background: white; padding: 1.5rem; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1rem; }
        code { background: #f0f0f0; padding: 0.15rem 0.4rem; border-radius: 3px;
               font-size: 0.95em; color: #c41e3a; }
        pre { background: #1a1f2e; color: #e0e6ed; padding: 1rem; border-radius: 6px;
              overflow-x: auto; font-size: 0.9em; }
        pre code { background: transparent; color: #7fe5bf; padding: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
        td { padding: 0.5rem; border-bottom: 1px solid #e2e8f0; }
        td:first-child { font-weight: 600; color: #475569; width: 35%; }
        .ok { color: #1fb57f; font-weight: bold; }
        .warn { color: #e55934; font-weight: bold; }
        .badge { display: inline-block; background: #5b7fff; color: white;
                 padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8em;
                 font-weight: 600; }
    </style>
</head>
<body>
    <h1>Stack LEMP listo para usar</h1>

    <div class="card">
        <h3>Estado del entorno</h3>
        <table>
            <tr><td>Versión PHP</td><td><?php echo phpversion(); ?></td></tr>
            <tr><td>Servidor</td><td><?php echo $_SERVER['SERVER_SOFTWARE']; ?></td></tr>
            <tr><td>Estado MySQL</td><td>
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
            </td></tr>
        </table>
    </div>

    <div class="card">
        <h3>Conexión a la base de datos</h3>
        <p>Tu aplicación PHP debe usar estos datos para conectar con MySQL:</p>
        <table>
            <tr><td>Host</td><td><code>__MYSQL_HOST__</code></td></tr>
            <tr><td>Usuario</td><td><code>appuser</code></td></tr>
            <tr><td>Contraseña</td><td><code>apppass</code></td></tr>
            <tr><td>Base de datos</td><td><code>appdb</code></td></tr>
            <tr><td>Puerto</td><td><code>3306</code> (interno, no necesitas especificarlo)</td></tr>
        </table>

        <p style="margin-top: 1rem;"><strong>Ejemplo en PHP:</strong></p>
        <pre><code>$conn = mysqli_connect("__MYSQL_HOST__", "appuser", "apppass", "appdb");
if (!$conn) {
    die("Error: " . mysqli_connect_error());
}</code></pre>
    </div>

    <div class="card">
        <h3>Cómo subir tu código</h3>
        <p>Sustituye este fichero (<code>index.php</code>) y sube los ficheros de tu aplicación a la carpeta compartida del stack mediante SFTP.</p>

        <p><strong>Importante:</strong></p>
        <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
            <li>El punto de entrada debe llamarse <code>index.php</code> (o <code>index.html</code>) para que se cargue al abrir la URL del stack.</li>
            <li>Puedes subir cualquier estructura de carpetas: subdirectorios, assets, includes, etc.</li>
            <li>Los cambios se reflejan inmediatamente, sin necesidad de reiniciar nada.</li>
            <li>Los datos guardados en MySQL persisten aunque el contenedor se reinicie.</li>
        </ul>

        <p style="margin-top: 1rem;"><strong>Conexión SFTP:</strong></p>
        <table>
            <tr><td>Servidor</td><td>la IP o dominio del VPS</td></tr>
            <tr><td>Puerto</td><td><code>22</code></td></tr>
            <tr><td>Usuario</td><td>el de tu equipo (lo proporciona el admin)</td></tr>
            <tr><td>Carpeta destino</td><td>la indicada por el admin en el ticket</td></tr>
        </table>
    </div>

    <p style="text-align: center; color: #94a3b8; font-size: 0.85rem;">
        ASIR CloudHub — Plataforma de entornos de desarrollo
    </p>
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
        restart_policy={"Name": "unless-stopped"},
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
        restart_policy={"Name": "unless-stopped"},
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
        restart_policy={"Name": "unless-stopped"},
        detach=True,
        labels={
            "asircloudhub.stack": nombre_stack,
            "asircloudhub.tipo": "lemp",
            "asircloudhub.ruta_codigo": ruta_www,
            "asircloudhub.equipo": equipo,
        },
    )

    # Esperar a que PHP-FPM instale mysqli y arranque
    time.sleep(8)

# Si phpMyAdmin está desplegado, conectarlo a la red de este stack
    from app.stacks.phpmyadmin import conectar_a_red
    conectar_a_red(red_nombre)

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