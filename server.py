import os
import requests

from flask import Flask, request, Response, render_template, \
    abort, send_from_directory, stream_with_context
from flask_jwt_extended import jwt_optional, get_jwt_identity

from qwc_services_core.jwt import jwt_manager
from qwc2_viewer import QWC2Viewer


# Flask application
app = Flask(__name__)
# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app)

# create QWC service
qwc2_viewer = QWC2Viewer(app.logger)

# path to QWC2 files and config
qwc2_path = os.environ.get("QWC2_PATH", "qwc2/")


# routes
@app.route('/')
def index():
    return send_from_directory(qwc2_path, 'index.html')


@app.route('/config.json')
@jwt_optional
def qwc2_config():
    return qwc2_viewer.qwc2_config(get_jwt_identity())


@app.route('/themes.json')
@jwt_optional
def qwc2_themes():
    return qwc2_viewer.qwc2_themes(get_jwt_identity())


@app.route('/assets/<path:path>')
def qwc2_assets(path):
    return send_from_directory(os.path.join(qwc2_path, 'assets'), path)


@app.route('/dist/<path:path>')
def qwc2_js(path):
    return send_from_directory(os.path.join(qwc2_path, 'dist'), path)


@app.route('/translations/<path:path>')
def qwc2_translations(path):
    return send_from_directory(os.path.join(qwc2_path, 'translations'), path)


@app.route("/proxy", methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy():
    """Proxy
    proxy?url=<url>&filename=<filename>
    url: the url to proxy
    filename: optional, if set it sets a content-disposition header with the
              specified filename
    """
    if not app.debug:  # Allow only in debug mode
        abort(403)
    url = request.args.get('url')
    filename = request.args.get('filename')
    if request.method == 'POST':
        headers = {'content-type': request.headers['content-type']}
        res = requests.post(url, stream=True, timeout=30,
                            data=request.get_data(), headers=headers)
    elif request.method == 'PUT':
        headers = {'content-type': request.headers['content-type']}
        res = requests.put(url, stream=True, timeout=30,
                           data=request.get_data(), headers=headers)
    elif request.method == 'DELETE':
        res = requests.delete(url, stream=True, timeout=10)
    elif request.method == 'GET':
        res = requests.get(url, stream=True, timeout=10)
    else:
        raise "Invalid operation"
    response = Response(stream_with_context(res.iter_content(chunk_size=1024)),
                        status=res.status_code)
    if filename:
        response.headers['content-disposition'] = 'filename=' + filename
    response.headers['content-type'] = res.headers['content-type']
    return response


# local webserver
if __name__ == '__main__':
    print("Starting QWC2 service...")
    app.run(host='localhost', port=5030, debug=True)
