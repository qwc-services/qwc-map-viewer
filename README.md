QWC Map Viewer
==============

Provide a [QWC2 Web Client](https://github.com/qgis/qwc2-demo-app) application using QWC services.

**Note:** requires a QWC OGC service or QGIS server running on `$OGC_SERVICE_URL`, a 
QWC Config service running on `$CONFIG_SERVICE_URL` and a QWC Data service running on 
`$DATA_SERVICE_URL`


Setup
-----

Copy your QWC2 files from a production build (see [QWC2 Quick start](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#quick-start)):

    SRCDIR=path/to/qwc2-app/prod/ DSTDIR=$PWD
    mkdir $DSTDIR/qwc2 && mkdir $DSTDIR/qwc2/dist
    cd $SRCDIR && \
    cp -r assets $DSTDIR/qwc2 && \
    cp -r translations $DSTDIR/qwc2 && \
    cp dist/QWC2App.js $DSTDIR/qwc2/dist/ && \
    cp index.html $DSTDIR/qwc2/ && \
    cp config.json $DSTDIR/qwc2/config.json && \
    cd -

Copy your QWC2 themes config file:

    cp themesConfig.json $DSTDIR/qwc2/


Configuration
-------------

Configure the QWC2 application using your `config.json` file (see [Documentation](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#application-configuration-the-configjson-and-jsappconfigjs-files)).

Add new themes to your `themesConfig.json` (see [Documentation](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#theme-configuration-qgis-projects-and-the-themesconfigjson-file)) and put any theme thumbnails into `$QWC2_PATH/assets/img/mapthumbs/`.
The `themesConfig.json` file is used by the Config service to collect the full themes configuration using GetProjectSettings.


### Custom viewer configurations

Additional viewer configurations can be added by placing a `<viewer>.json` and/or `<viewer>.html` for each custom viewer into the `$QWC2_VIEWERS_PATH` directory. The custom viewers can be opened by appending the viewer name to the base URL: `http://localhost:5030/<viewer>/`.

A custom `<viewer>.json` could e.g. contain a different set of menu items and tools.
A custom `<viewer>.html` could e.g. show a different title and use a custom CSS.

If a `<viewer>.json` or `<viewer>.html` is missing, the default `config.json` and `index.html` is used instead.


### Sign in based on request origin

The `AUTH_SERVICE_URL` is used by default for sign in and sign out.

To differentiate e.g between intranet and internet, identity groups based on request origin and different auth service URLs can be configured:

* `ORIGIN_CONFIG`: JSON with rules configuration
    ```json
    {
        "host": {
            "<group name>": "<RegEx pattern for host from request>",
            "_intern_": "^127.0.0.1(:\\\\d+)?$"
        }
    }
    ```
* `AUTH_SERVICES_CONFIG`: JSON with lookup of auth service URLs for groups (with fallback to `AUTH_SERVICE_URL`)
    ```json
    {
        "<group name>": "<auth service route or URL>",
        "_intern_": "http://127.0.0.1:5017/"
    }
    ```


Usage
-----

Set the `OGC_SERVICE_URL` environment variable to the QWC OGC service URL (or QGIS server URL)
when starting this service. (default: `http://localhost:5013/` on
qwc-ogc-service container)

Set the `CONFIG_SERVICE_URL` environment variable to the QWC Config service URL
when starting this service. (default: `http://localhost:5010/` on
qwc-config-service container)

Set the `DATA_SERVICE_URL` environment variable to the QWC Data service URL
when starting this service. (default: `http://localhost:5012/` on
qwc-data-service container)

Set the `QWC2_PATH` environment variable to your QWC2 files path.

Optionally:

 * Set the `QWC2_CONFIG` environment variable to your QWC2 `config.json` path if it is not located in `$QWC2_PATH`.
 * Set the `QWC2_VIEWERS_PATH` environment variable to your QWC2 custom viewers path (default: `$QWC2_PATH/viewers/`).
 * Set the `PERMALINK_SERVICE_URL` environment variable to the QWC permalink service URL.
 * Set the `ELEVATION_SERVICE_URL` environment variable to the QWC elevation service URL.
 * Set the `MAPINFO_SERVICE_URL` environment variable to the QWC map info service URL.
 * Set the `DOCUMENT_SERVICE_URL` environment variable to the QWC document service URL.
 * Set the `SEARCH_SERVICE_URL` environment variable to the QWC search service URL.
 * Set the `AUTH_SERVICE_URL` environment variable to the default QWC auth service URL.
 * Set the `INFO_SERVICE_URL` environment variable to the QWC feature info proxy service URL.
 * Set the `LEGEND_SERVICE_URL` environment variable to the QWC legend graphics proxy service URL.
 * Set the `PRINT_SERVICE_URL` environment variable to the QWC print proxy service URL.
 * Set the `ORIGIN_CONFIG` environment variable to your origin detection rules.
 * Set the `AUTH_SERVICES_CONFIG` environment variable to your auth service lookups.


Base URL:

    http://localhost:5030/

Custom viewer URL:

    http://localhost:5030/<viewer>/

Sample requests:

    curl 'http://localhost:5030/config.json'
    curl 'http://localhost:5030/themes.json'


Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 --system-site-packages .venv

Without system packages:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt

Start local service:

    OGC_SERVICE_URL=http://localhost:5013/ CONFIG_SERVICE_URL=http://localhost:5010/ DATA_SERVICE_URL=http://localhost:5012/ QWC2_PATH=qwc2/ python server.py

Start local service with local auth service config:

    OGC_SERVICE_URL=http://localhost:5013/ CONFIG_SERVICE_URL=http://localhost:5010/ DATA_SERVICE_URL=http://localhost:5012/ QWC2_PATH=qwc2/ AUTH_SERVICES_CONFIG='{"_intern_": "http://127.0.0.1:5017/"}' AUTH_SERVICE_URL=http://localhost:5017/ python server.py
