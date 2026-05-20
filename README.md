# ASIR CloudHub

Plataforma web para el despliegue automatizado de stacks Docker (LAMP, LEMP, WordPress, phpMyAdmin) desde un panel de control.

Proyecto desarrollado como Trabajo de Fin de Grado del ciclo formativo de **Administración de Sistemas Informáticos en Red (ASIR)**.

---

## Descripción

ASIR CloudHub permite a un administrador desplegar entornos de desarrollo o producción completos en cuestión de segundos, sin necesidad de escribir comandos Docker manualmente. Cada stack se despliega en una red Docker aislada con puertos dinámicos y volúmenes persistentes.

El usuario final recibe únicamente la URL del stack desplegado, sin acceso al panel de administración.

## Arquitectura
Administrador → Nginx (HTTPS) → Flask (API REST) → Docker Engine → Contenedores

- **Backend:** Python 3 + Flask + Docker SDK
- **Frontend:** HTML + CSS + JavaScript (sin frameworks)
- **Infraestructura:** VPS Ubuntu 24.04 LTS + Docker Engine
- **Reverse proxy:** Nginx + Let's Encrypt (HTTPS)

## Stacks soportados

| Stack | Componentes |
|-------|-------------|
| LAMP | Apache + PHP-FPM + MySQL |
| LEMP | Nginx + PHP-FPM + MySQL |
| WordPress | Nginx + WordPress + MariaDB + WP-CLI |
| phpMyAdmin | phpMyAdmin (gestión de BD) |

## Estructura del proyecto
dockerpanel/
├── app/
│   ├── init.py          # Application factory
│   ├── routes.py            # Endpoints de la API REST
│   ├── docker_manager.py    # Lógica de gestión Docker
│   ├── templates/
│   │   └── index.html       # Panel de control
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── requirements.txt
└── run.py                   # Punto de entrada

## Instalación

```bash
# Clonar el repositorio
git clone git@github.com:Damg-27/asircloudhub.git
cd asircloudhub

# Crear entorno virtual e instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Arrancar la aplicación
python run.py
```

El panel quedará accesible en `http://localhost:5000`.

## Estado del proyecto

Proyecto en desarrollo activo. Funcionalidades completadas:

- [x] Infraestructura base (VPS + Docker + Flask)
- [x] API REST para gestión de contenedores
- [x] Panel de control web
- [ ] Despliegue de stack LAMP
- [ ] Despliegue de stacks LEMP, WordPress, phpMyAdmin
- [ ] Reverse proxy con HTTPS
- [ ] Validaciones y manejo de errores

## Autor

**Damg-27** — TFG ASIR