from app import create_app

# Llamamos a la fábrica desde la raíz
app = create_app()



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)