
// Referencias a elementos del DOM

const botonesStack = document.querySelectorAll(".btn-stack");
const equipoSelect = document.getElementById("equipo-select");
const listaStacks = document.getElementById("lista-stacks");
const mensaje = document.getElementById("mensaje");


// Función auxiliar: mostrar mensaje de feedback
function mostrarMensaje(texto, tipo) {
    mensaje.textContent = texto;
    mensaje.className = tipo;
    if (tipo !== "info") {
        setTimeout(() => {
            mensaje.className = "";
            mensaje.textContent = "";
        }, 6000);
    }
}


// Función auxiliar: copiar texto al portapapeles
async function copiarAlPortapapeles(texto, boton) {
    try {
        await navigator.clipboard.writeText(texto);
        const textoOriginal = boton.textContent;
        boton.textContent = "Copiado ✓";
        boton.classList.add("copiado");
        setTimeout(() => {
            boton.textContent = textoOriginal;
            boton.classList.remove("copiado");
        }, 1500);
    } catch (error) {
        mostrarMensaje("No se pudo copiar al portapapeles", "error");
    }
}

// GET /api/stacks — listar y pintar
async function cargarStacks() {
    try {
        const respuesta = await fetch("/api/stacks");
        const stacks = await respuesta.json();

        if (stacks.length === 0) {
            listaStacks.innerHTML = '<p class="vacio">No hay stacks desplegados</p>';
            return;
        }

        listaStacks.innerHTML = stacks.map(s => `
            <div class="stack-card">
                <div class="stack-card-header">
                    <span class="stack-card-tipo">${s.tipo || "desconocido"}</span>
                    ${s.equipo ? `<span class="stack-card-equipo">${s.equipo}</span>` : ""}
                    <span class="stack-card-nombre">${s.stack}</span>
                    <button class="stack-card-btn-borrar" data-stack="${s.stack}">Borrar</button>
                </div>

                 ${s.url ? (
                    s.edad_segundos < 20 ? `
                        <div class="copyable copyable-esperando">
                            <span class="copyable-label">URL:</span>
                            <span class="copyable-value">Esperando que el stack esté listo...</span>                        
                        </div>
                    ` : `
                        <div class="copyable">
                            <span class="copyable-label">URL:</span>
                            <span class="copyable-value">${s.url}</span>
                            <button class="copyable-btn" data-copy="${s.url}">Copiar</button>
                        </div>
                    `
                ) : ""}

                ${s.ruta_codigo ? `
                    <div class="copyable">
                        <span class="copyable-label">Ruta:</span>
                        <span class="copyable-value">${s.ruta_codigo}</span>
                        <button class="copyable-btn" data-copy="${s.ruta_codigo}">Copiar</button>
                    </div>
                ` : ""}

                <div class="stack-card-contenedores">
                    ${s.contenedores.map(c => `
                        <span class="contenedor-tag ${c.estado}">${c.nombre} (${c.estado})</span>
                    `).join("")}
                </div>
            </div>
        `).join("");

        // Enganchar botones de "Borrar"
        document.querySelectorAll(".stack-card-btn-borrar").forEach(btn => {
            btn.addEventListener("click", () => borrarStack(btn.dataset.stack));
        });

        // Enganchar botones de "Copiar"
        document.querySelectorAll(".copyable-btn").forEach(btn => {
            btn.addEventListener("click", () => copiarAlPortapapeles(btn.dataset.copy, btn));
        });

    }catch (error) {
        // Fallo silencioso: la próxima recarga automática (cada 5s) lo reintentará.
        // Solo logueamos en consola para depuración.
        console.warn("Recarga de stacks fallida, se reintentará:", error);
    }
}


// POST /api/stacks/<tipo> — desplegar stack

async function desplegarStack(tipo) {
    const equipo = equipoSelect.value;

    // Deshabilitar todos los botones mientras se despliega
    botonesStack.forEach(b => b.disabled = true);
    mostrarMensaje(
        `Desplegando stack ${tipo.toUpperCase()} para el equipo ${equipo}. Esto tarda unos 15-20 segundos, espera por favor...`,
        "info"
    );

    try {
        const respuesta = await fetch(`/api/stacks/${tipo}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ equipo: equipo }),
        });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            // Refrescar la lista PRIMERO para que la tarjeta y el mensaje aparezcan juntos
            await cargarStacks();
            mostrarMensaje(
                `Stack ${datos.stack} desplegado para ${datos.equipo}. La URL estará disponible en unos segundos.`,
                "exito"
            );
        } else {
            mostrarMensaje(datos.error || "Error al desplegar el stack", "error");
        }
    } catch (error) {
        mostrarMensaje("Error de conexión", "error");
        console.error(error);
    } finally {
        // Reactivar solo los stacks implementados
        const tiposActivos = ["lamp", "lemp", "wordpress"];
        botonesStack.forEach(b => {
            b.disabled = !tiposActivos.includes(b.dataset.tipo);
        });
    }
}



// DELETE /api/stacks/<nombre> — borrar stack

async function borrarStack(nombre) {
    if (!confirm(`¿Seguro que quieres borrar el stack ${nombre}? Esta acción no se puede deshacer.`)) {
        return;
    }

    mostrarMensaje(`Borrando stack ${nombre}...`, "info");

    try {
        const respuesta = await fetch(`/api/stacks/${nombre}`, {
            method: "DELETE",
        });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            mostrarMensaje(datos.mensaje || "Stack eliminado", "exito");
            cargarStacks();
        } else {
            mostrarMensaje(datos.error || "Error al borrar el stack", "error");
        }
    } catch (error) {
        mostrarMensaje("Error de conexión", "error");
        console.error(error);
    }
}


// Enganchar botones de stack

botonesStack.forEach(boton => {
    boton.addEventListener("click", () => {
        const tipo = boton.dataset.tipo;
        desplegarStack(tipo);
    });
});


// Limpiar recursos huérfanos

const btnLimpiar = document.getElementById("btn-limpiar");
btnLimpiar.addEventListener("click", async () => {
    if (!confirm("¿Limpiar volúmenes, redes y carpetas huérfanas del proyecto?")) {
        return;
    }

    btnLimpiar.disabled = true;
    mostrarMensaje("Limpiando recursos huérfanos...", "info");

    try {
        const respuesta = await fetch("/api/limpiar", { method: "POST" });
        const informe = await respuesta.json();

        const total = informe.volumenes_borrados.length
                    + informe.redes_borradas.length
                    + informe.carpetas_borradas.length;

        if (total === 0) {
            mostrarMensaje("No había recursos huérfanos. Todo limpio.", "exito");
        } else {
            const partes = [];
            if (informe.volumenes_borrados.length) {
                partes.push(`${informe.volumenes_borrados.length} volumen(es)`);
            }
            if (informe.redes_borradas.length) {
                partes.push(`${informe.redes_borradas.length} red(es)`);
            }
            if (informe.carpetas_borradas.length) {
                partes.push(`${informe.carpetas_borradas.length} carpeta(s)`);
            }
            mostrarMensaje(`Borrado: ${partes.join(", ")}.`, "exito");
        }
    } catch (error) {
        mostrarMensaje("Error al limpiar recursos", "error");
        console.error(error);
    } finally {
        btnLimpiar.disabled = false;
    }
});
// Carga inicial + refresco automático cada 5 segundos

cargarStacks();
setInterval(cargarStacks, 5000);