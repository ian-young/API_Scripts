"""
Author: Ian Young
Purpose: Host a Flask webserver to print a graph on localhost.
"""

from flask import Flask, app, send_file
from update_graph import image_path as image

# Initialize Flask
app = Flask(__name__)


@app.route("/")
def index():
    """Sends the file to the webserver to create the webpage."""
    return send_file(image, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # Run on local host
