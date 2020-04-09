import logging
import os
import requests

from flask import json, Flask, request
from flask_jwt_extended import jwt_optional, get_jwt_identity

from qwc_services_core.jwt import jwt_manager
from qwc_services_core.tenant_handler import TenantHandler
from origin_detector import OriginDetector
from qwc2_viewer import QWC2Viewer


# Flask application
app = Flask(__name__)
# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app)

# create tenant handler
tenant_handler = TenantHandler(app.logger)


def qwc2_viewer_handler(identity):
    """Get or create a QWC2Viewer instance for a tenant.

    :param str identity: User identity
    """
    tenant = tenant_handler.tenant(identity)
    handler = tenant_handler.handler('mapViewer', 'qwc', tenant)
    if handler is None:
        handler = tenant_handler.register_handler(
            'qwc', tenant, QWC2Viewer(tenant, app.logger))
    return handler


try:
    origin_config = json.loads(
        os.environ.get(
            'ORIGIN_CONFIG', '{"host": {"_intern_": "^127.0.0.1(:\\\\d+)?$"}}'
        )
    )
except Exception as e:
    app.logger.error("Could not load ORIGIN_CONFIG:\n%s" % e)
    origin_config = {}

origin_detector = OriginDetector(app.logger, origin_config)


def with_no_cache_headers(response):
    """Add cache-disabling headers to response.

    :param obj response: Response
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# routes
@app.route('/')
def index():
    identity = origin_detector.detect(get_jwt_identity(), request)
    qwc2_viewer = qwc2_viewer_handler(identity)
    return qwc2_viewer.qwc2_index(identity)


@app.route('/config.json')
@jwt_optional
def qwc2_config():
    identity = origin_detector.detect(get_jwt_identity(), request)
    qwc2_viewer = qwc2_viewer_handler(identity)
    return with_no_cache_headers(qwc2_viewer.qwc2_config(identity))


@app.route('/themes.json')
@jwt_optional
def qwc2_themes():
    identity = origin_detector.detect(get_jwt_identity(), request)
    qwc2_viewer = qwc2_viewer_handler(identity)
    return with_no_cache_headers(qwc2_viewer.qwc2_themes(identity))


@app.route('/assets/<path:path>')
def qwc2_assets(path):
    qwc2_viewer = qwc2_viewer_handler(get_jwt_identity())
    return qwc2_viewer.qwc2_assets(path)


@app.route('/dist/<path:path>')
def qwc2_js(path):
    qwc2_viewer = qwc2_viewer_handler(get_jwt_identity())
    return qwc2_viewer.qwc2_js(path)


@app.route('/translations/<path:path>')
def qwc2_translations(path):
    qwc2_viewer = qwc2_viewer_handler(get_jwt_identity())
    return qwc2_viewer.qwc2_translations(path)


@app.route('/favicon.ico')
def favicon():
    qwc2_viewer = qwc2_viewer_handler(get_jwt_identity())
    return qwc2_viewer.qwc2_favicon()


# local webserver
if __name__ == '__main__':
    print("Starting Map viewer...")
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=5030, debug=True)
