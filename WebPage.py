# Importar las librerías y módulos necesarios
import os, zipfile
from flask import Flask, jsonify, request, send_file, render_template, send_from_directory
import instaloader
from flask_cors import CORS
import requests
from datetime import datetime

# Crear una instancia de la aplicación Flask
app = Flask(__name__)
CORS(app)  # Permitir solicitudes de origen cruzado (Cross-Origin Resource Sharing)

# Definir una clase personalizada que hereda del controlador de velocidad de Instaloader
class MyRateController(instaloader.RateController):
    def sleep(self, secs):
        # Esperar 2 segundos entre cada solicitud para evitar límites de rate limiting
        time.sleep(2)

# Función para verificar si un post contiene más de dos imágenes
def has_multiple_images(post):
    """
    Verifica si un post contiene más de dos imágenes.

    Args:
        post (instaloader.Post): El objeto Post de Instaloader.

    Returns:
        bool: True si el post tiene más de dos imágenes, False en caso contrario.
    """
    if post.typename == 'GraphSidecar':
        # Convertir el generador a lista y obtener su longitud para contar el número de imágenes en el post
        sidecar_nodes = list(post.get_sidecar_nodes())
        return len(sidecar_nodes) > 2
    else:
        return False


# Ruta para manejar la descarga de imágenes
@app.route('/download/<username>')
def download_images(username):
    try:
        # Crear una instancia de Instaloader con un controlador personalizado de velocidad
        L = instaloader.Instaloader(rate_controller=lambda ctx: MyRateController(ctx))

        # Crear el directorio 'temp' si no existe
        folder_path = 'temp'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Limpiar la carpeta 'temp' antes de descargar nuevas imágenes
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            os.remove(file_path)

        # Descargar el perfil de Instagram
        profile = instaloader.Profile.from_username(L.context, username)

        # Obtener la URL de la imagen de perfil
        profile_pic_url = profile.profile_pic_url

        # Descargar la imagen de perfil y guardarla en el directorio temporal
        profile_pic_filename = f'{username}_profile.jpg'
        with open(profile_pic_filename, 'wb') as f:
            response = requests.get(profile_pic_url)
            f.write(response.content)
        
        # Mover la imagen descargada al directorio 'temp'
        profile_pic_local = f'/temp/{profile_pic_filename}'
        os.rename(profile_pic_filename, f'temp/{profile_pic_filename}')

        # Generar las URL locales para las imágenes descargadas
        image_urls_local = []
        for post in profile.get_posts():
            image_filenames = []
            if has_multiple_images(post):
                # Si es un post con múltiples imágenes, iterar sobre las imágenes y guardarlas con un contador
                for i, node in enumerate(post.get_sidecar_nodes()):
                    image_filename = f'{post.date_utc.strftime("%Y-%m-%d_%H-%M-%S_UTC")}_{i+1}.jpg'
                    image_url = node.display_url  # Obtener la URL de la imagen
                    image_path = f'temp/{image_filename}'
                    with open(image_path, 'wb') as f:
                        response = requests.get(image_url)
                        f.write(response.content)
                    image_url_local = f'/temp/{image_filename}'
                    image_urls_local.append({'url': image_url_local})
            else:
                # Si es un post con una sola imagen, guardarla usando el nombre base
                image_filename = f'{post.date_utc.strftime("%Y-%m-%d_%H-%M-%S_UTC")}.jpg'
                image_url = post.url
                image_path = f'temp/{image_filename}'
                with open(image_path, 'wb') as f:
                    response = requests.get(image_url)
                    f.write(response.content)
                image_url_local = f'/temp/{image_filename}'
                image_urls_local.append({'url': image_url_local})
                
        # Devolver las URL locales al frontend en formato JSON
        return jsonify({
            "profile_pic": profile_pic_local,
            "posts": image_urls_local
        })
    
    except instaloader.ProfileNotExistsException as e:
        # Manejar el caso en que el perfil no exista
        return jsonify({
            "error": "El perfil no existe en Instagram."
        }), 404  # Devolvemos un código 404 para indicar que no se encontró el perfil

    except Exception as e:
        # Manejar otros errores y devolver un mensaje de error genérico
        return jsonify({
            "error": "Se produjo un error al descargar las imágenes."
        }), 500  # Devolvemos un código 500 para indicar un error interno del servidor

# Ruta para servir las imágenes descargadas desde el directorio 'temp'
@app.route('/temp/<path:filename>')
def serve_image(filename):
    return send_from_directory('temp', filename)

# Ruta para manejar la descarga de una imagen individual
@app.route('/download-image')
def download_image():
    # Obtenemos la URL de la imagen desde los parámetros de la solicitud
    image_url = request.args.get('url')
    print("image_url: ", image_url)

    try:
        # Obtener el nombre del archivo desde la URL
        filename = os.path.basename(image_url)
        
        # Construir la ruta completa al archivo en el directorio 'temp'
        image_path = os.path.join('temp', filename)

        # Realizar la descarga de la imagen y la devolvemos al frontend
        return send_file(image_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 404

# Ruta para servir una imagen logo-gramsaver.png local desde el directorio 'templates'
@app.route('/image')
def serve_image_logo():
    # Ruta local de la imagen que deseas servir
    image_path = 'templates\logo-gramsaver.png'

    try:
        # Usamos send_file para enviar la imagen al cliente
        return send_file(image_path, mimetype='image/png')

    except Exception as e:
        # Manejo de errores si la imagen no se encuentra o hay algún problema
        return str(e), 404

# Ruta principal para mostrar el archivo HTML del frontend en la ruta '/'
@app.route('/')
def index():
    # Aquí renderizamos y mostramos el archivo HTML en la ruta /
    return render_template('index.html')

# Iniciar la aplicación Flask en modo de depuración y en el puerto 8000
if __name__ == "__main__":
    app.run(debug=True, port=8000)


