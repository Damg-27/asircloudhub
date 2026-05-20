const btnCrear = document.getElementById("btn-crear");
const btnBorrar = document.getElementById("btn-borrar");
const lista = document.getElementById("lista-contenedores");
const mensaje = document.getElementById("mensaje");

function mostrarMensaje(texto, tipo) {
    mensaje.textContent = texto;
    mensaje.className = tipo;  // "exito" o "error"
    // Oculta el mensaje a los 3 segundos
    setTimeout(() => {
        mensaje.className = "";
        mensaje.textContent = "";
    }, 3000);
}


async function cargarContenedores() {
    try {
        const respuesta = await fetch("/api/containers");
        const contenedores = await respuesta.json();

        // Si no hay contenedores, mensaje "vacío"
        if (contenedores.length === 0) {
            lista.innerHTML = '<li class="vacio">No hay contenedores activos</li>';
            return;
        }

        // Pinta cada contenedor como un <li>
        lista.innerHTML = contenedores.map(c => `
            <li>
                <div class="contenedor-info">
                    <span class="contenedor-nombre">${c.nombre}</span>
                    <span class="contenedor-detalles">
                        ID: ${c.id} · Imagen: ${c.imagen}
                    </span>
                </div>
                <span class="estado estado-${c.estado}">${c.estado}</span>
            </li>
        `).join("");

    } catch (error) {
        mostrarMensaje("Error al cargar contenedores", "error");
        console.error(error);
    }
}

// POST /api/containers/test — crear contenedor
btnCrear.addEventListener("click", async () => {
    btnCrear.disabled = true;
    try {
        const respuesta = await fetch("/api/containers/test", {
            method: "POST",
        });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            mostrarMensaje(`Contenedor creado: ${datos.nombre}`, "exito");
            cargarContenedores();
        } else {
            mostrarMensaje(datos.error || "Error al crear el contenedor", "error");
        }
    } catch (error) {
        mostrarMensaje("Error de conexión", "error");
        console.error(error);
    } finally {
        btnCrear.disabled = false;
    }
});


// DELETE /api/containers/test — borrar contenedor

btnBorrar.addEventListener("click", async () => {
    btnBorrar.disabled = true;
    try {
        const respuesta = await fetch("/api/containers/test", {
            method: "DELETE",
        });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            mostrarMensaje(datos.mensaje || "Contenedor borrado", "exito");
            cargarContenedores();
        } else {
            mostrarMensaje(datos.error || "Error al borrar el contenedor", "error");
        }
    } catch (error) {
        mostrarMensaje("Error de conexión", "error");
        console.error(error);
    } finally {
        btnBorrar.disabled = false;
    }
});


// Al cargar la página: pintar lista inicial
cargarContenedores();