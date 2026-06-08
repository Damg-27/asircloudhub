import docker

# Cliente único de Docker, conecta al socket /var/run/docker.sock del host
client = docker.from_env()


def list_all_stacks():
    """
    Devuelve la lista de stacks desplegados, agrupando contenedores
    por su etiqueta 'asircloudhub.stack'.
    """
    contenedores = client.containers.list(all=True)
    stacks = {}

    for c in contenedores:
        labels = c.labels or {}
        nombre_stack = labels.get("asircloudhub.stack")
        tipo = labels.get("asircloudhub.tipo")

        # Saltar contenedores que no son de un stack nuestro
        if not nombre_stack:
            continue

        
        # Inicializar el stack si es la primera vez que lo vemos
        if nombre_stack not in stacks:
            # Edad del stack: segundos desde la creación del contenedor más antiguo
            from datetime import datetime, timezone
            try:
                creado_str = c.attrs["Created"]
                # Recortar a microsegundos (Docker devuelve nanosegundos)
                creado_str = creado_str[:26] + "+00:00" if "." in creado_str else creado_str
                creado = datetime.fromisoformat(creado_str.replace("Z", "+00:00"))
                edad_segundos = int((datetime.now(timezone.utc) - creado).total_seconds())
            except Exception:
                edad_segundos = 999

            stacks[nombre_stack] = {
                "stack": nombre_stack,
                "tipo": tipo,
                "equipo": labels.get("asircloudhub.equipo"),
                "contenedores": [],
                "puerto": None,
                "url": None,
                "ruta_codigo": labels.get("asircloudhub.ruta_codigo"),
                "edad_segundos": edad_segundos,
            }


        # Añadir info del contenedor al stack
        stacks[nombre_stack]["contenedores"].append({
            "nombre": c.name,
            "estado": c.status,
        })

        # Si este contenedor expone puerto, guardarlo como puerto público del stack
        if c.ports:
            for puerto_interno, mapeos in c.ports.items():
                if mapeos:
                    puerto_externo = mapeos[0]["HostPort"]
                    stacks[nombre_stack]["puerto"] = int(puerto_externo)
                    stacks[nombre_stack]["url"] = f"http://localhost:{puerto_externo}"

    return list(stacks.values())


def limpiar_huerfanos():
    """
    Detecta y elimina recursos huérfanos del proyecto:
    - Volúmenes Docker que pertenecían a stacks ya borrados.
    - Redes Docker huérfanas.
    - Carpetas de stacks que ya no tienen contenedores.

    Returns:
        dict: informe con lo que se borró.
    """
    import os
    import subprocess

    STACKS_DATA_DIR = "/home/damg/stacks_data"

    # Stacks activos según labels de contenedores
    stacks_activos = set()
    for c in client.containers.list(all=True):
        labels = c.labels or {}
        nombre_stack = labels.get("asircloudhub.stack")
        if nombre_stack:
            stacks_activos.add(nombre_stack)

    informe = {
        "volumenes_borrados": [],
        "redes_borradas": [],
        "carpetas_borradas": [],
    }

    # Volúmenes huérfanos: nombres con prefijos del proyecto pero sin stack activo
    prefijos = ("lamp_", "lemp_", "wp_")
    for vol in client.volumes.list():
        nombre = vol.name
        if not nombre.startswith(prefijos):
            continue
        # Extraer el "stack" del nombre del volumen: lamp_abc123_db -> lamp_abc123
        partes = nombre.rsplit("_", 1)
        if len(partes) == 2:
            posible_stack = partes[0]
            if posible_stack not in stacks_activos:
                try:
                    vol.remove()
                    informe["volumenes_borrados"].append(nombre)
                except Exception:
                    pass

    # Redes huérfanas
    for red in client.networks.list():
        nombre = red.name
        if not nombre.startswith(prefijos):
            continue
        partes = nombre.rsplit("_", 1)
        if len(partes) == 2 and partes[1] == "red":
            posible_stack = partes[0]
            if posible_stack not in stacks_activos:
                try:
                    red.remove()
                    informe["redes_borradas"].append(nombre)
                except Exception:
                    pass

    # Carpetas huérfanas en stacks_data/
    if os.path.isdir(STACKS_DATA_DIR):
        try:
            for nombre in os.listdir(STACKS_DATA_DIR):
                if not nombre.startswith(prefijos):
                    continue
                if nombre not in stacks_activos:
                    ruta = os.path.join(STACKS_DATA_DIR, nombre)
                    try:
                        subprocess.run(["sudo", "rm", "-rf", ruta], check=True)
                        informe["carpetas_borradas"].append(nombre)
                    except Exception:
                        pass
        except PermissionError:
            pass

    return informe