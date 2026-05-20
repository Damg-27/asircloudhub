import docker

# Cliente único de Docker, conecta al socket /var/run/docker.sock del host
client = docker.from_env()


def list_all_containers():
    """Devuelve una lista de todos los contenedores (corriendo y parados)."""
    contenedores = client.containers.list(all=True)
    resultado = []
    for c in contenedores:
        resultado.append({
            "id": c.short_id,
            "nombre": c.name,
            "imagen": c.image.tags[0] if c.image.tags else "sin-tag",
            "estado": c.status,
            "puertos": c.ports,
        })
    return resultado

def create_test_container():
    """Crea un contenedor Nginx de prueba con puerto 8080."""
    contenedor = client.containers.run(
        image="nginx",
        name="test-nginx",
        ports={"80/tcp": 8080},
        detach=True,
    )
    return {
        "id": contenedor.short_id,
        "nombre": contenedor.name,
        "url": "http://localhost:8080",
    }


def delete_test_container():
    """Para y borra el contenedor de prueba."""
    contenedor = client.containers.get("test-nginx")
    contenedor.stop()
    contenedor.remove()
    return {"mensaje": "Contenedor test-nginx eliminado"}