[![](https://github.com/qwc-services/qwc-map-viewer/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-map-viewer/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-map-viewer?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-map-viewer)

QWC Map Viewer
==============

Serve a [QGIS Web Client](https://github.com/qgis/qwc2) application with filtered themes and configuration.

Configuration
-------------

The static config and permission files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.


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

`qwc2_config` contains the QWC2 application configuration, with `config` corresponding to the contents of your standalone `config.json` file (see [Documentation](https://qwc-services.github.io/master/configuration/ViewerConfiguration/#load-time-configuration-configjson)).

`qwc2_themes` contains the full themes configuration, corresponding to the contents of your standalone `themes.json` collected from `themesConfig.json`.

Add new themes to your `themesConfig.json` (see [Documentation](https://qwc-services.github.io/master/configuration/ThemesConfiguration/)) and put any theme thumbnails into `$QWC2_PATH/assets/img/mapthumbs/`.

### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.

### Permissions

* [JSON schema](https://github.com/qwc-services/qwc-services-core/blob/master/schemas/qwc-services-permissions.json)
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

### User info fields

Additional user info fields may be read from the `user_infos` table of the QWC Config DB by setting `user_info_fields`:
```json
"config": {
  "db_url": "postgresql:///?service=qwc_configdb",
  "user_info_fields": ["surname", "first_name"]
}
```
These will be added as `user_infos` in the `config.json` response if present in the current identity.

### Options for handling restricted themes

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


Run locally
-----------

Install dependencies and run:

    export CONFIG_PATH=<CONFIG_PATH>
    uv run src/server.py

To use configs from a `qwc-docker` setup, set `CONFIG_PATH=<...>/qwc-docker/volumes/config`.

Set `FLASK_DEBUG=1` for additional debug output.

Set `FLASK_RUN_PORT=<port>` to change the default port (default: `5000`).

API documentation:

    http://localhost:$FLASK_RUN_PORT/api/

Docker usage
------------

The Docker image is published on Dockerhub. The following Docker images are available:
* [`qwc-map-viewer`](https://hub.docker.com/r/sourcepole/qwc-map-viewer): Map viewer service with stock QWC application preinstalled. Mount your custom viwer assets (logo, mapthumbs, etc) to `/qwc2/assets` inside the container.
* [`qwc-map-viewer-base`](https://hub.docker.com/r/sourcepole/qwc-map-viewer-base): Map viewer service to use with a custom qwc2 application. Mount your custom QWC build to `/qwc2` inside the container.

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).
