import docker
from app.port_manager import get_free_port

client = docker.from_env()

def _pull_imagenes():
    """Descarga las imágenes necesarias si no están en local."""
    client.images.pull("mysql", tag="8.0")
    client.images.pull("php", tag="8.2-apache")

def _generar_index_php(mysql_host):
    """Genera el contenido de un index.php de prueba para el stack."""
    php = """<?php
header('Content-Type: text/html; charset=utf-8');
echo "<h1>ASIR CloudHub - Stack LAMP</h1>";
echo "<p>Servidor Apache + PHP funcionando correctamente.</p>";
echo "<p>Version de PHP: " . phpversion() . "</p>";

// Prueba de conexion a MySQL
$conn = @mysqli_connect("__MYSQL_HOST__", "appuser", "apppass", "appdb");
if ($conn) {
    echo "<p style='color:green'><b>Conexion a MySQL: OK</b></p>";
    mysqli_close($conn);
} else {
    echo "<p style='color:orange'><b>MySQL aun no esta listo</b> (espera unos segundos y recarga)</p>";
}
?>"""
    return php.replace("__MYSQL_HOST__", mysql_host)

def deploy_lamp(nombre_stack="lamp1"):

    # 1. Nombres únicos basados en el nombre del stack
    _pull_imagenes()
    red_nombre = f"{nombre_stack}_red"
    volumen_nombre = f"{nombre_stack}_db_data"
    mysql_nombre = f"{nombre_stack}_mysql"
    web_nombre = f"{nombre_stack}_web"

    # 2. Crear la red aislada (bridge)
    red = client.networks.create(red_nombre, driver="bridge")

    # 3. Crear el volumen persistente para MySQL
    client.volumes.create(volumen_nombre)

    # 4. Contenedor MySQL
    client.containers.run(
        image="mysql:8.0",
        name=mysql_nombre,
        network=red_nombre,
        volumes={volumen_nombre: {"bind": "/var/lib/mysql", "mode": "rw"}},
        environment={
            "MYSQL_ROOT_PASSWORD": "rootpass",
            "MYSQL_DATABASE": "appdb",
            "MYSQL_USER": "appuser",
            "MYSQL_PASSWORD": "apppass",
        },
        detach=True,
    )
    # 5. Buscar un puerto libre para el servidor web
    puerto_web = get_free_port()

    # 6. Contenedor Apache + PHP
    client.containers.run(
        image="php:8.2-apache",
        name=web_nombre,
        network=red_nombre,
        ports={"80/tcp": puerto_web},
        detach=True,
    )
     # 7. Inyectar un index.php de prueba en el contenedor web
    import tarfile
    import io

    contenido = _generar_index_php(mysql_nombre)

    # Crear un archivo tar en memoria con el index.php
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        datos = contenido.encode("utf-8")
        info = tarfile.TarInfo(name="index.php")
        info.size = len(datos)
        tar.addfile(info, io.BytesIO(datos))
    tar_stream.seek(0)

    # Copiar el tar dentro del contenedor web
    web = client.containers.get(web_nombre)
    web.put_archive("/var/www/html", tar_stream)
    # 8. Instalar la extension mysqli en el contenedor web y recargar Apache
    web.exec_run("docker-php-ext-install mysqli", detach=False)
    web.restart()

    return {
        "stack": nombre_stack,
        "puerto": puerto_web,
        "url": f"http://localhost:{puerto_web}",
        "contenedores": [mysql_nombre, web_nombre],
    }