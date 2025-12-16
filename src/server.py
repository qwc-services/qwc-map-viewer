import logging
import os
import requests
import urllib.parse

from flask import json, Flask, request, jsonify, redirect

from qwc_services_core.auth import auth_manager, optional_auth, get_identity
from qwc_services_core.tenant_handler import TenantHandler, TenantPrefixMiddleware, TenantSessionInterface
from qwc_services_core.runtime_config import RuntimeConfig
from qwc2_viewer import QWC2Viewer

# Flask application
app = Flask(__name__)
# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = auth_manager(app)

# create tenant handler
tenant_handler = TenantHandler(app.logger)
app.wsgi_app = TenantPrefixMiddleware(app.wsgi_app)
app.session_interface = TenantSessionInterface()


def qwc2_viewer_handler():
    """Get or create a QWC2Viewer instance for a tenant."""
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler('mapViewer', 'qwc', tenant)
    if handler is None:
        handler = tenant_handler.register_handler(
            'qwc', tenant, QWC2Viewer(tenant, tenant_handler, app.logger))
    return handler


def with_no_cache_headers(response):
    """Add cache-disabling headers to response.

    :param obj response: Response
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def auth_path_prefix():
    tenant = tenant_handler.tenant()
    config_handler = RuntimeConfig("mapViewer", app.logger)
    config = config_handler.tenant_config(tenant)
    auth_path = config.get('auth_service_url', '/auth/')
    return app.session_interface.tenant_path_prefix().rstrip("/") + "/" + auth_path.lstrip("/")


@app.before_request
@optional_auth
def assert_user_is_logged():
    public_endpoints = ['healthz', 'ready']
    if request.endpoint in public_endpoints:
        return

    tenant = tenant_handler.tenant()
    config_handler = RuntimeConfig("mapViewer", app.logger)
    config = config_handler.tenant_config(tenant)
    public_paths = config.get("public_paths", [])
    if request.path in public_paths:
        return

    if config.get("auth_required", False):
        identity = get_identity()
        if identity is None:
            app.logger.info("Access denied, authentication required")
            prefix = auth_path_prefix().rstrip('/')
            return redirect(prefix + '/login?url=%s' % urllib.parse.quote(request.url))


# routes
@app.route('/')
@optional_auth
def index():
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_index(get_identity(), request.args, request.url)


@app.route('/config.json')
@optional_auth
def qwc2_config():
    qwc2_viewer = qwc2_viewer_handler()
    return with_no_cache_headers(qwc2_viewer.qwc2_config(get_identity(), request.args))


@app.route('/themes.json')
@optional_auth
# lang: Optional, asset language, i.e. en-US
def qwc2_themes():
    qwc2_viewer = qwc2_viewer_handler()
    lang = request.args.get('lang', None)
    return with_no_cache_headers(qwc2_viewer.qwc2_themes(get_identity(), lang))

@app.route('/editConfig.json')
@optional_auth
# map: Map id
# layer: Layer name
def edit_config():
    qwc2_viewer = qwc2_viewer_handler()
    wms_name = request.args.get('map', None)
    layers = list(filter(bool, request.args.get('layers', "").split(",")))
    return with_no_cache_headers(qwc2_viewer.edit_config(get_identity(), wms_name, layers))


@app.route('/assets/<path:path>')
@optional_auth
# lang: Optional, asset language, i.e. en-US
def qwc2_assets(path):
    qwc2_viewer = qwc2_viewer_handler()
    lang = request.args.get('lang', None)
    return qwc2_viewer.qwc2_assets(path, get_identity(), lang)

@app.route('/data/<path:path>')
def qwc2_data(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_data(path)

@app.route('/dist/<path:path>')
def qwc2_js(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_js(path)


@app.route('/translations/<path:path>')
def qwc2_translations(path):
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.qwc2_translations(path)


@app.route('/setuserinfo')
def set_user_info():
    qwc2_viewer = qwc2_viewer_handler()
    return qwc2_viewer.set_user_info(request.args, get_identity())

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
