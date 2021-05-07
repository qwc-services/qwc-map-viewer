import logging
import os
import requests

from flask import json, Flask, request, jsonify, redirect
from flask_jwt_extended import jwt_optional, get_jwt_identity

from qwc_services_core.jwt import jwt_manager
from qwc_services_core.tenant_handler import TenantHandler, TenantPrefixMiddleware, TenantSessionInterface
from qwc2_viewer import QWC2Viewer

AUTH_PATH = os.environ.get('AUTH_PATH', '/auth')
AUTH_REQUIRED = os.environ.get('AUTH_REQUIRED', False)

# Flask application
app = Flask(__name__)
# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app)

# create tenant handler
tenant_handler = TenantHandler(app.logger)


def qwc2_viewer_handler():
    """Get or create a QWC2Viewer instance for a tenant."""
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler('mapViewer', 'qwc', tenant)
    if handler is None:
        handler = tenant_handler.register_handler(
            'qwc', tenant, QWC2Viewer(tenant, app.logger))
    return handler


def with_no_cache_headers(response):
    """Add cache-disabling headers to response.

    :param obj response: Response
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.wsgi_app = TenantPrefixMiddleware(app.wsgi_app)
app.session_interface = TenantSessionInterface(os.environ)

def auth_path_prefix():
    return app.session_interface.tenant_path_prefix().rstrip("/") + "/" + AUTH_PATH.lstrip("/")

@app.before_request
@jwt_optional
def assert_user_is_logged():
    if AUTH_REQUIRED:
        identity = get_jwt_identity()
        if identity is None:
            app.logger.info("Access denied, authentication required")
            prefix = auth_path_prefix()
            return redirect(prefix + '/login?url=%s' % request.url)

# routes
@app.route('/')
def index():
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_index(get_jwt_identity())


@app.route('/config.json')
@jwt_optional
def qwc2_config():
    qwc2_viewer = qwc2_viewer_handler()
    return with_no_cache_headers(qwc2_viewer.qwc2_config(get_jwt_identity(), request.args))


@app.route('/themes.json')
@jwt_optional
def qwc2_themes():
    qwc2_viewer = qwc2_viewer_handler()
    return with_no_cache_headers(qwc2_viewer.qwc2_themes(get_jwt_identity()))


@app.route('/assets/<path:path>')
def qwc2_assets(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_assets(path)


@app.route('/dist/<path:path>')
def qwc2_js(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_js(path)


@app.route('/translations/<path:path>')
def qwc2_translations(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_translations(path)


@app.route('/favicon.ico')
def favicon():
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_favicon()


""" readyness probe endpoint """
@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """
@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == '__main__':
    print("Starting Map viewer...")
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=5030, debug=True)
