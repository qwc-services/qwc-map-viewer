[![](https://github.com/qwc-services/qwc-map-viewer/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-map-viewer/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-map-viewer?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-map-viewer)

QWC Map Viewer
==============

Provide a [QWC2 Web Client](https://github.com/qgis/qwc2) application using QWC services.

**Note:** Requires a QWC OGC service or QGIS server running on `ogc_service_url`. Additional QWC Services are optional.


Setup
--------------------------

Copy your QWC2 files from a production build:

    SRCDIR=path/to/qwc2/prod/ DSTDIR=$PWD
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

`qwc2_config` contains the QWC2 application configuration, with `config` corresponding to the contents of your standalone `config.json` file (see [Documentation](https://qwc-services.github.io/master/configuration/ViewerConfiguration/#load-time-configuration-configjson)).

`qwc2_themes` contains the full themes configuration, corresponding to the contents of your standalone `themes.json` collected from `themesConfig.json`.

Add new themes to your `themesConfig.json` (see [Documentation](https://qwc-services.github.io/master/configuration/ThemesConfiguration/)) and put any theme thumbnails into `$QWC2_PATH/assets/img/mapthumbs/`.
The `themesConfig.json` file is used to collect the full themes configuration using GetProjectSettings.

Optional settings for restricted themes:
```json
"config": {
  "show_restricted_themes": false,
  "show_restricted_themes_whitelist": [],
  "redirect_restricted_themes_to_auth": false,
  "internal_permalink_service_url": "http://qwc-permalink-service:9090"
}
```
* `show_restricted_themes` (optional): Whether to insert placeholder items for restricted themes in themes.json (default: `false`)
* `show_restricted_themes_whitelist` (optional): Whitelist of restricted theme names to include in themes.json. If empty, all restricted themes are shown. (default: `[]`)
* `redirect_restricted_themes_to_auth` (optional): Whether to redirect to login on auth service if requesting a restricted theme in URL params, if not currently signed in (default: `false`)
* `internal_permalink_service_url` (optional): Internal Permalink service URL for getting the theme from a resolved permalink for redirecting to login (default: `http://qwc-permalink-service:9090`). This is used only if `redirect_restricted_themes_to_auth` is enabled and `permalink_service_url` is set.


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
* `background_layers`: permitted background layers (use the wildcard string "*" to allow all background layers)
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
* `sourcepole/qwc-map-viewer`: Map viewer service with stock qwc2 application
* `sourcepole/qwc-map-viewer-base`: Map viewer service to use with a custom qwc2 application

Dependencies:

        git repos                Docker images

     ┌───────────────┐
     │     qwc2      ├────────────┐
     │  config.json  │ CI Build   │
     └───────────────┘      ┌─────▼───────────────┐
                         ┌──► qwc-map-viewer      │
     ┌───────────────┐   │  └─────────────────────┘
     │ qwc-map-viewer├───┤
     └───────────────┘   │  ┌─────────────────────┐
                         └──► qwc-map-viewer-base │
                            └─────────────────────┘

#### qwc-map-viewer

This is the stock version used in the `docker-compose-example.yml` file. With this version, the docker image comes with a preinstalled version of the latest qwc2 stock application build and the python application for the viewer. Use this docker image, if you don't have your own build of the QWC2 app.

#### qwc-map-viewer-base

If you want to use your own QWC2 build then this is the docker image that you want to use. This docker image comes with only the python application installed on. Here is an example, on how you can add you own QWC2 build to the docker image.


See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).


Development
-----------

Install dependencies and run service:

    uv run src/server.py

With config path:

    CONFIG_PATH=/PATH/TO/CONFIGS/ uv run src/server.py
