[![](https://github.com/qwc-services/qwc-map-viewer/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-map-viewer/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-map-viewer-demo?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-map-viewer-demo)

QWC Map Viewer
==============

Provide a [QWC2 Web Client](https://github.com/qgis/qwc2-demo-app) application using QWC services.

**Note:** Requires a QWC OGC service or QGIS server running on `ogc_service_url`. Additional QWC Services are optional.


Setup
-----

Copy your QWC2 files from a production build (see [QWC2 Quick start](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#quick-start)):

    SRCDIR=path/to/qwc2-app/prod/ DSTDIR=$PWD
    mkdir $DSTDIR/qwc2 && mkdir $DSTDIR/qwc2/dist
    cd $SRCDIR && \
    cp -r assets $DSTDIR/qwc2 && \
    cp -r translations $DSTDIR/qwc2/translations && \
    cp dist/QWC2App.js $DSTDIR/qwc2/dist/ && \
    cp index.html $DSTDIR/qwc2/ && \
    cp config.json $DSTDIR/qwc2/config.json && \
    cd -


Configuration
-------------

The static config and permission files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

**Note:**: Custom viewers have been replaced by tenants in v2.

### Map Viewer config

* [JSON schema](schemas/qwc-map-viewer.json)
* File location: `$CONFIG_PATH/<tenant>/mapViewerConfig.json`

Example:
```jsonc
{
  "$schema": "https://raw.githubusercontent.com/qwc-services/qwc-map-viewer/v2/schemas/qwc-map-viewer.json",
  "service": "map-viewer",
  "config": {
    // path to QWC2 files
    "qwc2_path": "qwc2/",
    // QWC OGC service (required)
    "ogc_service_url": "http://localhost:5013/",
    // some optional QWC services
    "auth_service_url": "http://localhost:5017/",
    "data_service_url": "http://localhost:5012/"
  },
  "resources": {
    "qwc2_config": {
      // restricted menu items
      "restricted_viewer_tasks": ["RasterExport"],

      "config": {
        // contents from QWC2 config.json
        "assetsPath": "/assets",
        // ...
      }
    },
    "qwc2_themes": {
      // contents from QWC2 themes.json
      "themes": {
        "items": [
          {
            "name": "qwc_demo",
            "title": "Demo",
            "url": "/ows/qwc_demo",
            // ...
            "sublayers": [
              // ...
            ]
          }
        ],
        "backgroundLayers": [
          // ...
        ],
        // ...
      }
    }
  }
}
```

All `config` options may be overridden by setting corresponding upper-case environment variables, e.g. `OGC_SERVICE_URL` for `ogc_service_url`.

Main optional QWC services:
 * `auth_service_url`: QWC Auth Service URL
 * `data_service_url`: QWC Data Service URL
 * `elevation_service_url`: QWC Elevation Service URL
 * `info_service_url`: QWC FeatureInfo Service URL
 * `legend_service_url`: QWC Legend Service URL
 * `permalink_service_url`: QWC Permalink Service URL
 * `print_service_url`: QWC Print Service URL
 * `proxy_service_url`: Proxy Service URL
 * `search_service_url`: QWC Search Service URL
 * `search_data_service_url`: QWC Search Result Service URL

Additional user info fields may be read from the JWT identity by setting `user_info_fields`:
```json
"config": {
  "user_info_fields": ["surname", "first_name"]
}
```
These will be added as `user_infos` in the `config.json` response if present in the current identity.

`qwc2_config` contains the QWC2 application configuration, with `config` corresponding to the contents of your standalone `config.json` file (see [Documentation](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#application-configuration-the-configjson-and-jsappconfigjs-files)).

`qwc2_themes` contains the full themes configuration, corresponding to the contents of your standalone `themes.json` collected from `themesConfig.json`.

Add new themes to your `themesConfig.json` (see [Documentation](https://github.com/qgis/qwc2-demo-app/blob/master/doc/QWC2_Documentation.md#theme-configuration-qgis-projects-and-the-themesconfigjson-file)) and put any theme thumbnails into `$QWC2_PATH/assets/img/mapthumbs/`.
The `themesConfig.json` file is used to collect the full themes configuration using GetProjectSettings.


### Permissions

* File location: `$CONFIG_PATH/<tenant>/permissions.json`

Example:
```json
{
  "users": [
    {
      "name": "demo",
      "groups": ["demo"],
      "roles": []
    }
  ],
  "groups": [
    {
      "name": "demo",
      "roles": ["demo"]
    }
  ],
  "roles": [
    {
      "role": "public",
      "permissions": {
        "viewer_tasks": [],
        "wms_services": [
          {
            "name": "qwc_demo",
            "layers": [
              {
                "name": "qwc_demo"
              },
              {
                "name": "edit_demo"
              },
              {
                "name": "edit_points"
              },
              {
                "name": "edit_lines"
              },
              {
                "name": "edit_polygons"
              },
              {
                "name": "geographic_lines"
              },
              {
                "name": "country_names"
              },
              {
                "name": "states_provinces"
              },
              {
                "name": "countries"
              },
              {
                "name": "bluemarble_bg"
              },
              {
                "name": "osm_bg"
              }
            ],
            "print_templates": ["A4 Landscape"]
          }
        ],
        "background_layers": ["bluemarble", "mapnik"],
        "data_datasets": [
          {
            "name": "qwc_demo.edit_points",
            "attributes": [
              "id", "name", "description", "num", "value", "type", "amount", "validated", "datetime"
            ]
          }
        ]
      }
    },
    {
      "role": "demo",
      "permissions": {
        "viewer_tasks": ["RasterExport"]
      }
    }
  ]
}
```

* `viewer_tasks`: permitted menu items if any are restricted
* `wms_services`: permitted WMS services, layers and print templates
* `background_layers`: permitted background layers
* `data_datasets`: permitted datasets for editing

In this example, the _Raster Export_ map tool will only be visible for users with the role `demo`.


Usage
-----

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

Base URL:

    http://localhost:5030/

Sample requests:

    curl 'http://localhost:5030/config.json'
    curl 'http://localhost:5030/themes.json'


Docker images
-------------

The following Docker images are available:
* `sourcepole/qwc-map-viewer-base`: Map viewer service
* `sourcepole/qwc-map-viewer-demo`: Map viewer service with qwc-demo-app viewer

Dependencies:

        git repos                Docker images

     ┌───────────────┐
     │     qwc2      │
     └───────┬───────┘
             │submodule
     ┌───────▼───────┐
     │ qwc-demo-app  ├────────────┐
     │    config.json│ CI Build   │
     └───────────────┘      ┌─────▼───────────────┐
                         ┌──► qwc-map-viewer-demo │
     ┌───────────────┐   │  └─────────────────────┘
     │ qwc-map-viewer├───┤
     └───────────────┘   │  ┌─────────────────────┐
                         └──► qwc-map-viewer-base │
                            └─────────────────────┘

### Run docker image

To run this docker image you will need the following three additional services:

* qwc-postgis
* qwc-qgis-server
* qwc-ogc-service
* qwc-data-service

Those services can be found under https://github.com/qwc-services/. The following steps explain how to download those services and how to run the `qwc-map-viewer` with `docker-compose`.

**Step 1: Clone qwc-docker**

    git clone https://github.com/qwc-services/qwc-docker
    cd qwc-docker

**Step 2: Create docker-compose.yml file**

    cp docker-compose-example.yml docker-compose.yml

**Step 3: Choose between a version of the qwc-map-viewer**

#### qwc-map-viewer-demo

This is the demo version used in the `docker-compose-example.yml` file. With this version, the docker image comes with a preinstalled version of the latest qwc2-demo-app build and the python application for the viewer. Use this docker image, if you don't have your own build of the QWC2 app.

#### qwc-map-viewer-base

If you want to use your own QWC2 build then this is the docker image that you want to use. This docker image comes with only the python application installed on. Here is an example, on how you can add you own QWC2 build to the docker image:

```
qwc-map-viewer:
    image: sourcepole/qwc-map-viewer-base
    ports:
        - "127.0.0.1:5030:9090"
    # Here you mount your own QWC2 build
    volumes:
        - /PATH_TO_QWC2_BUILD/:/qwc2:ro
        - /PATH_TO_CONFIG:/srv/qwc_service/config:ro
```
**Step 4: Start docker containers**

    docker-compose up qwc-map-viewer

For more information please visit: https://github.com/qwc-services/qwc-docker


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

    CONFIG_PATH=/PATH/TO/CONFIGS/ python server.py
