import docker
from app.port_manager import get_free_port

client = docker.from_env()

# Nombre fijo del contenedor (solo puede existir uno)
PMA_NOMBRE = "phpmyadmin_panel"


def _pull_imagen():
    """Descarga la imagen oficial de phpMyAdmin si no está local."""
    client.images.pull("phpmyadmin/phpmyadmin", tag="latest")


def _redes_de_stacks():
    """
    Devuelve la lista de redes Docker pertenecientes a stacks del proyecto
    (las que tienen el sufijo '_red' y pertenecen a un stack activo).
    """
    redes = []
    prefijos = ("lamp_", "lemp_", "wp_")
    for r in client.networks.list():
        if r.name.startswith(prefijos) and r.name.endswith("_red"):
            redes.append(r)
    return redes


def deploy_phpmyadmin():
    """
    Despliega el stack phpMyAdmin único.

    Crea un solo contenedor expuesto en un puerto público y lo conecta
    a TODAS las redes de stacks existentes en el VPS, de modo que pueda
    administrar la BD de cualquiera de ellos.

    Returns:
        dict: información del stack desplegado.
    """
    # Si ya existe, error
    try:
        existente = client.containers.get(PMA_NOMBRE)
        raise ValueError(
            "Ya existe un stack phpMyAdmin desplegado. "
            "Bórralo desde el panel antes de crear otro."
        )
    except docker.errors.NotFound:
        pass  # Bien, no existe, podemos crearlo

    _pull_imagen()

    # Puerto público
    puerto = get_free_port()

    # Crear el contenedor (sin red inicial; la añadiremos después)
    contenedor = client.containers.run(
        image="phpmyadmin/phpmyadmin:latest",
        name=PMA_NOMBRE,
        ports={"80/tcp": puerto},
        environment={
            # PMA_ARBITRARY=1 permite al admin escribir el host en el login,
            # en lugar de tenerlo fijo. Así puede conectar a cualquier stack.
            "PMA_ARBITRARY": "1",
            # Permite subir archivos SQL más grandes
            "UPLOAD_LIMIT": "64M",
        },
        mem_limit="256m",
        detach=True,
        labels={
            "asircloudhub.stack": "phpmyadmin",
            "asircloudhub.tipo": "phpmyadmin",
        },
    )

    # Conectar a TODAS las redes de stacks existentes
    redes = _redes_de_stacks()
    for red in redes:
        try:
            red.connect(contenedor)
        except docker.errors.APIError:
            pass  # Si ya está conectado o falla puntualmente, seguimos

    # Espera breve para arranque
    import time
    time.sleep(3)

    return {
        "stack": "phpmyadmin",
        "tipo": "phpmyadmin",
        "equipo": None,
        "puerto": puerto,
        "url": f"http://localhost:{puerto}",
        "ruta_codigo": None,
        "contenedores": [PMA_NOMBRE],
        "redes_conectadas": len(redes),
    }


def delete_phpmyadmin(nombre_stack=None):
    """
    Elimina el stack phpMyAdmin. El parámetro nombre_stack se ignora
    (siempre se borra el único existente).
    """
    try:
        c = client.containers.get(PMA_NOMBRE)
        c.stop()
        c.remove()
    except docker.errors.NotFound:
        pass

    return {"mensaje": "phpMyAdmin eliminado correctamente"}


def conectar_a_red(red_nombre):
    """
    Conecta el contenedor de phpMyAdmin (si existe) a la red dada.
    Se llama desde deploy_lamp/lemp/wordpress al crear un stack nuevo,
    para que phpMyAdmin pueda administrar la BD del nuevo stack.
    """
    try:
        contenedor = client.containers.get(PMA_NOMBRE)
    except docker.errors.NotFound:
        return  # phpMyAdmin no está desplegado, no hay nada que hacer

    try:
        red = client.networks.get(red_nombre)
        red.connect(contenedor)
    except docker.errors.APIError:
        pass  # Ya conectado o error puntual