from flask import Flask, app, send_file
from updateGraph import image_path as image

# Initialize Flask
app = Flask(__name__)


@app.route('/')
def index():
    return send_file(image, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
