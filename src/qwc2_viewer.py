import base64
import os
import requests
import tempfile
from urllib.parse import urlparse, urlunparse, urlencode, urljoin, parse_qsl
from xml.etree import ElementTree
from sqlalchemy.sql import text as sql_text

from flask import abort, json, jsonify, redirect, send_from_directory, Response
from flask_jwt_extended import get_jwt

from qwc_services_core.database import DatabaseEngine
from qwc_services_core.permissions_reader import PermissionsReader
from qwc_services_core.runtime_config import RuntimeConfig


db_engine = DatabaseEngine()


class QWC2Viewer:
    """QWC2Viewer class

    Provide configurations for QWC2 map viewer.
    """

    # prefix for marking extracted Base64 encoded images in assets URL
    # e.g. '/assets/img/base64/mapthumbs/qwc_demo.png'
    BASE64_IMAGE_ROUTE_PREFIX = 'img/base64/'

    DEFAULT_THUMBNAIL_IMAGE = 'img/mapthumbs/default.jpg'

    def __init__(self, tenant, tenant_handler, logger):
        """Constructor

        :param str tenant: Tenant ID
        :param TenantHandler tenant_handler: tenant handler
        :param Logger logger: Application logger
        """
        self.tenant = tenant
        self.tenant_handler = tenant_handler
        self.logger = logger

        config_handler = RuntimeConfig("mapViewer", logger)
        config = config_handler.tenant_config(tenant)

        # path to QWC2 files
        self.qwc2_path = config.get('qwc2_path', 'qwc2/')

        # QWC service URLs for config.json
        self.auth_service_url = self.__sanitize_url(
            config.get('auth_service_url'))
        self.ccc_config_service_url = self.__sanitize_url(
            config.get('ccc_config_service_url'))
        self.data_service_url = self.__sanitize_url(
            config.get('data_service_url'))
        self.dataproduct_service_url = self.__sanitize_url(
            config.get('dataproduct_service_url'))
        self.document_service_url = self.__sanitize_url(
            config.get('document_service_url',
                       config.get('feature_report_service_url')))
        self.elevation_service_url = self.__sanitize_url(
            config.get('elevation_service_url'))
        self.landreg_service_url = self.__sanitize_url(
            config.get('landreg_service_url'))
        self.mapinfo_service_url = self.__sanitize_url(
            config.get('mapinfo_service_url'))
        self.permalink_service_url = self.__sanitize_url(
            config.get('permalink_service_url'))
        self.plotinfo_service_url = self.__sanitize_url(
            config.get('plotinfo_service_url'))
        self.proxy_service_url = self.__sanitize_url(
            config.get('proxy_service_url'))
        self.search_service_url = self.__sanitize_url(
            config.get('search_service_url'))
        self.search_data_service_url = self.__sanitize_url(
            config.get('search_data_service_url'))
        # QWC service URLs for themes.json
        self.ogc_service_url = self.__sanitize_url(
            config.get('ogc_service_url', 'http://localhost:5013/'))
        self.info_service_url = self.__sanitize_url(
            config.get('info_service_url', self.ogc_service_url))
        self.legend_service_url = self.__sanitize_url(
            config.get('legend_service_url', self.ogc_service_url))
        self.print_service_url = self.__sanitize_url(
            config.get('print_service_url', self.ogc_service_url))
        # internal QWC service URLs for internal usage
        if self.permalink_service_url:
            # set default if permalink service present
            default_url = 'http://qwc-permalink-service:9090'
        else:
            default_url = None
        self.internal_permalink_service_url = self.__sanitize_url(
            config.get('internal_permalink_service_url', default_url))

        self.db_url = config.get('db_url', 'postgresql:///?service=qwc_configdb')
        self.qwc_config_schema = config.get('qwc_config_schema', 'qwc_config')

        self.show_restricted_themes = config.get('show_restricted_themes', False)
        self.show_restricted_themes_whitelist = config.get('show_restricted_themes_whitelist', "")
        self.redirect_restricted_themes_to_auth = config.get(
            'redirect_restricted_themes_to_auth', False
        )
        self.redirect_to_auth_if_no_permitted_themes = config.get(
            'redirect_to_auth_if_no_permitted_themes', False
        )

        self.user_info_fields = config.get('user_info_fields', [])
        self.display_user_info_field = config.get('display_user_info_field')

        # get config dir for tenant
        self.config_dir = os.path.dirname(
            RuntimeConfig.config_file_path('mapViewer', tenant)
        )

        # temporary target dir for any Base64 encoded thumbnail images
        # NOTE: this dir will be cleaned up automatically on reload
        self.images_temp_dir = None

        self.resources = self.load_resources(config)
        self.permissions_handler = PermissionsReader(tenant, logger)

    def qwc2_index(self, identity, params, request_url):
        """Return QWC2 index.html for user.

        :param obj identity: User identity
        :param ImmutableMultiDict params: Request URL parameters
        :param str request_url: Full request URL
        """

        # if params are empty, check if there are default params
        # configured in user_info_fields, and redirect if that is the case
        if not params.get('t') and not params.get('k') and not params.get('bk') \
            and isinstance(identity, dict) and self.db_url \
        :
            db = db_engine.db_engine(self.db_url)
            with db.connect() as conn:
                sql = sql_text("""
                    SELECT *
                    FROM {schema}.user_infos ui
                    JOIN {schema}.users u ON u.id=ui.user_id
                    WHERE u.name=:user;
                """.format(schema=self.qwc_config_schema))
                result = conn.execute(sql, {"user": identity.get("username")})

                row = result.first()
                fields = row._asdict() if row else {}
            if fields.get("default_url_params", ""):
                default_params = dict(parse_qsl(fields["default_url_params"]))
                default_params.update(params)
                urlparts = urlparse(request_url)
                urlparts = urlparts._replace(query=urlencode(default_params))
                return redirect(urlunparse(urlparts))

        # check whether requested theme is restricted
        if self.redirect_restricted_themes_to_auth:
            theme = self.__theme_from_params(identity, params)
            if self.__theme_restricted(identity, theme):
                if self.auth_service_url:
                    # redirect to login on auth service
                    login_params = urlencode({
                        'url': request_url
                    })
                    redirect_url = urljoin(
                        self.auth_service_url, "login?%s" % login_params
                    )
                    self.logger.debug(
                        "Restricted theme '%s' requested, "
                        "redirecting to auth service" % theme
                    )
                    return redirect(redirect_url)

        # If there are no permitted themes, redirect to auth
        if self.redirect_to_auth_if_no_permitted_themes:
            permitted_theme_ids = []
            themes = self.permitted_themes(identity, None, permitted_theme_ids)
            if len(permitted_theme_ids) == 0:
                if self.auth_service_url:
                    # redirect to login on auth service
                    login_params = urlencode({
                        'url': request_url
                    })
                    redirect_url = urljoin(
                        self.auth_service_url, "login?%s" % login_params
                    )
                    self.logger.debug(
                        "No permitted themes, redirecting to auth service"
                    )
                    return redirect(redirect_url)

        # check if index file is present
        viewer_index_file = os.path.join(self.config_dir, 'index.html')
        try:
            with open(viewer_index_file) as fh:
                viewer_index = fh.read()
        except:
            # show FileNotFoundError error
            raise Exception(
                "[Errno 2] No such file or directory: '%s'" %
                viewer_index_file
            )
        self.logger.debug("Using index '%s'" % viewer_index_file)

        # Inject CSRF token
        token = (get_jwt() or {}).get("csrf")
        if token:
            viewer_index = viewer_index.replace('</head>', '<meta name="csrf-token" content="%s" />\n</head>' % token)

        return viewer_index

    def qwc2_config(self, identity, params):
        """Return QWC2 config.json for user.

        :param obj identity: User identity
        """
        self.logger.debug('Generating config.json for identity: %s', identity)

        # deep copy config from qwc2_config
        config = json.loads(json.dumps(
            self.resources['qwc2_config']['config']
        ))

        # set QWC service URLs
        if self.auth_service_url:
            config['authServiceUrl'] = self.auth_service_url
        if self.ccc_config_service_url:
            config['cccConfigService'] = self.ccc_config_service_url
        if self.data_service_url:
            config['editServiceUrl'] = self.data_service_url
        if self.dataproduct_service_url:
            config['dataproductServiceUrl'] = self.dataproduct_service_url
        if self.document_service_url:
            config['documentServiceUrl'] = self.document_service_url
        if self.elevation_service_url:
            config['elevationServiceUrl'] = self.elevation_service_url
        if self.landreg_service_url:
            config['landRegisterService'] = self.landreg_service_url
        if self.mapinfo_service_url:
            config['mapInfoService'] = self.mapinfo_service_url
        if self.permalink_service_url:
            config['permalinkServiceUrl'] = self.permalink_service_url
        if self.plotinfo_service_url:
            config['plotInfoService'] = self.plotinfo_service_url
        if self.proxy_service_url:
            config['proxyServiceUrl'] = self.proxy_service_url
        if self.search_service_url:
            config['searchServiceUrl'] = self.search_service_url
        if self.search_data_service_url:
            config['searchDataServiceUrl'] = self.search_data_service_url

        config['wmsDpi'] = os.environ.get(
            'WMS_DPI', config.get('wmsDpi', '96'))

        username = None
        display_username = None
        autologin = None
        user_infos = {}
        if identity:
            if isinstance(identity, dict):
                username = identity.get('username')
                # NOTE: ignore group from identity
                autologin = identity.get('autologin')

                if self.db_url:
                    # add custom user info fields
                    db = db_engine.db_engine(self.db_url)
                    with db.connect() as conn:
                        sql = sql_text("""
                            SELECT *
                            FROM {schema}.user_infos ui
                            JOIN {schema}.users u ON u.id=ui.user_id
                            WHERE u.name=:user;
                        """.format(schema=self.qwc_config_schema))
                        result = conn.execute(sql, {"user": identity.get("username")})

                        row = result.first()
                        entries = row._asdict() if row else {}

                        if self.display_user_info_field:
                            display_username = entries[self.display_user_info_field]

                        for field in self.user_info_fields:
                            if field in entries:
                                user_infos[field] = entries[field]
                            else:
                                self.logger.warning(
                                    "Could not read user info field '%s' "
                                    "from identity" % field
                                )
                        user_infos["default_url_params"] = entries.get("default_url_params", "")

                if isinstance(identity.get('user_infos'), dict):
                    user_infos.update(identity.get('user_infos'))
            else:
                # identity is username
                username = identity

        # Look for any Login item, and change it to logout if user is signed in
        signed_in = username is not None
        hide_login = (autologin is not None) or (
            params.get("autologin") is not None)
        if 'common' in config['plugins']:
            self.__replace_login__helper_plugins(
                config['plugins']['common'], signed_in, username, hide_login)
        self.__replace_login__helper_plugins(
            config['plugins']['mobile'], signed_in, username, hide_login)
        self.__replace_login__helper_plugins(
            config['plugins']['desktop'], signed_in, username, hide_login)

        # filter any restricted viewer task items
        viewer_task_permissions = self.viewer_task_permissions(identity)
        if 'common' in config['plugins']:
            self.__filter_restricted_viewer_tasks(
                config['plugins']['common'], viewer_task_permissions
            )
        self.__filter_restricted_viewer_tasks(
            config['plugins']['mobile'], viewer_task_permissions
        )
        self.__filter_restricted_viewer_tasks(
            config['plugins']['desktop'], viewer_task_permissions
        )

        config['username'] = display_username or username
        config['tenant'] = self.tenant
        if user_infos:
            config['user_infos'] = user_infos

        return jsonify(config)


    def set_user_info(self, params, identity):
        """Stores the user info fields passed as query params in the user_infos table.
        """

        if not params:
            return jsonify({
                "success": False,
                "error": "Empty query"
            })

        if not isinstance(identity, dict):
            return jsonify({
                "success": False,
                "error": "Missing identity"
            })

        if not self.db_url:
            return jsonify({
                "success": False,
                "error": "Server configuration does not support setting user info"
            })

        # Disallow any parameters not set in self.user_info_fields and not "default_url_params"
        allowed_params = self.user_info_fields + ["default_url_params"]
        disallowed_params = [key for key in params if key not in allowed_params]

        if disallowed_params:
            return jsonify({
                "success": False,
                "error": "Disallowed fields: " + ",".join(disallowed_params)
            })

        columns = []
        values_sql = []
        values = {}
        for idx, entry in enumerate(params.items()):
            key, value = entry
            placeholder = "__val%d" % idx
            columns.append(key)
            values_sql.append(":%s" % placeholder)
            values[placeholder] = value

        values["username"] = identity.get("username")

        db = db_engine.db_engine(self.db_url)
        with db.begin() as conn:
            sql = sql_text("""
                WITH "user" AS (
                    SELECT id FROM "{schema}"."users" WHERE name=:username
                )
                INSERT INTO "{schema}"."user_infos" ("user_id", {columns})
                SELECT id, {values_sql} FROM "user"
                ON CONFLICT ("user_id") DO
                UPDATE SET ({columns}) = ROW({values_sql})
                RETURNING ({columns})
            """.format(
                columns = ",".join(columns),
                values_sql = ",".join(values_sql),
                schema=self.qwc_config_schema
            ))
            result = conn.execute(sql, values)
            row = result.one_or_none()
            return_values = row._asdict() if row else None

        return jsonify({
            "success": return_values is not None,
            "fields": return_values,
            "error": "Query failed" if not return_values else None
        })

    def __sanitize_url(self, url):
        """Ensure URL ends with a slash, if not empty
        """
        return (url.rstrip('/') + '/') if url else ""

    def __theme_from_params(self, identity, params):
        """Get requested theme from URL params.

        NOTE: only resolve permalinks if redirect to login is enabled

        :param obj identity: User identity
        :param ImmutableMultiDict params: Request URL parameters
        """
        theme = params.get('t')

        if 'k' not in params:
            # no permalink param present
            return theme
        if not self.redirect_restricted_themes_to_auth:
            # redirect is not enabled
            return theme
        if (
            not self.permalink_service_url
            or not self.internal_permalink_service_url
        ):
            # no permalink service present
            return theme
        if not self.auth_service_url:
            # no auth service present
            return False
        if identity:
            # skip if already signed in
            return theme

        # resolve permalink and extract theme
        try:
            # resolve permalink
            url = urljoin(self.internal_permalink_service_url, 'resolvepermalink')
            params = {
                'key': params.get('k')
            }
            self.logger.debug(
                "Resolving permalink at %s?%s" % (url, urlencode(params))
            )
            headers = {}
            if self.tenant_handler.tenant_header:
                # forward tenant header
                headers[self.tenant_handler.tenant_header] = self.tenant
                self.logger.debug("Forwarding tenant header: %s" % headers)
            response = requests.get(url, params=params, headers=headers)

            # extract theme
            permalink = json.loads(response.text)
            permalink_theme = permalink.get('query', {}).get('t')
            if permalink_theme:
                self.logger.debug(
                    "Permalink contains theme '%s'" % permalink_theme
                )
                theme = permalink_theme
        except Exception as e:
            self.logger.error("Could not resolve permalink:\n%s" % e)

        return theme

    def __theme_restricted(self, identity, theme):
        """Check whether requested theme is restricted.

        :param obj identity: User identity
        :param str theme: Theme ID
        """
        if not self.redirect_restricted_themes_to_auth:
            # redirect is not enabled
            return False
        if not theme:
            # no theme requested or blank
            return False
        if not self.auth_service_url:
            # no auth service present
            return False
        if identity:
            # skip if already signed in
            return False

        # check whether theme exists
        available_theme_ids = self.__collect_theme_ids(self.resources['qwc2_themes'])
        if theme not in available_theme_ids:
            # unknown theme ID
            return False

        # check whether theme is not public
        public_theme_ids = self.__collect_theme_ids(self.permitted_themes(None, None))
        return theme not in public_theme_ids

    def __collect_theme_ids(self, theme_group):
        """Recursively collect theme IDs from config or permissions.

        :param obj theme_group: Theme group from config or permissions
        """
        theme_ids = []

        # collect theme items
        for item in theme_group.get('items', []):
            theme_ids.append(item['id'])

        # collect sub groups
        for subgroup in theme_group.get('subdirs', []):
            theme_ids += self.__collect_theme_ids(subgroup)

        return theme_ids

    def __replace_login__helper_plugins(self, plugins, signed_in, username, hide):
        """Search plugins configurations and call
           self.__replace_login__helper_items on menuItems and toolbarItems

        :param list(obj) plugins: Plugins configurations
        :param bool signed_in: Whether user is signed in
        """
        for plugin in plugins:
            if 'cfg' not in plugin:
                # skip plugin without cfg
                continue
            if "menuItems" in plugin["cfg"]:
                self.__replace_login__helper_items(
                    plugin["cfg"]["menuItems"], signed_in, username, hide)
            if "toolbarItems" in plugin["cfg"]:
                self.__replace_login__helper_items(
                    plugin["cfg"]["toolbarItems"], signed_in, username, hide)

    def __replace_login__helper_items(self, items, signed_in, username, hide):
        """Replace Login with Logout if identity is not None on Login items in
           menuItems and toolbarItems.

        :param list(obj) items: Menu or toolbar items
        :param bool signed_in: Whether user is signed in
        """
        removeIndex = None
        for (idx, item) in enumerate(items):
            # Convert legacy name
            if item.get("key") == "Login":
                item["key"] = "Authentication"
                item["mode"] = "Login"
            if item.get("key") == "Authentication" and signed_in:
                if hide:
                    removeIndex = idx
                    break
                else:
                    item["mode"] = "Logout"
                    item["icon"] = "logout"
                    item["trargs"] = [username]
            elif "subitems" in item:
                self.__replace_login__helper_items(
                    item["subitems"], signed_in, username, hide)
        if removeIndex is not None:
            del items[removeIndex]

    def __filter_restricted_viewer_tasks(self, plugins,
                                         viewer_task_permissions):
        """Remove restricted viewer task items from menu and toolbar.

        :param list(obj) plugins: Plugins configurations
        :param obj viewer_task_permissions: Viewer task permissions as
                                            {<item key>: <permitted>}
        """
        for key in viewer_task_permissions:
            if not viewer_task_permissions[key]:
                plugins_to_remove = []
                for plugin in plugins:
                    if plugin.get("name") == key:
                        plugins_to_remove.append(plugin)
                    elif plugin.get("name") == "TaskButton" and \
                        plugin.get("cfg", {}).get("task", "") + plugin.get("cfg").get('mode', "") == key:
                        plugins_to_remove.append(plugin)

                    if 'menuItems' in plugin.get('cfg', {}):
                        self.__filter_config_items(
                            plugin['cfg']['menuItems'], key
                        )
                    if 'toolbarItems' in plugin.get('cfg', {}):
                        self.__filter_config_items(
                            plugin['cfg']['toolbarItems'], key
                        )
                for plugin in plugins_to_remove:
                    plugins.remove(plugin)

    def __filter_config_items(self, items, key):
        """Remove items with key from menuItems and toolbarItems.

        :param list(obj) items: Menu or toolbar items
        :param str key: Item key
        """
        items_to_remove = []
        for item in items:
            if item['key'] + item.get('mode', '') == key:
                # collect items to remove
                items_to_remove.append(item)
            elif 'subitems' in item:
                self.__filter_config_items(item['subitems'], key)

        for item in items_to_remove:
            items.remove(item)

    def qwc2_themes(self, identity, lang):
        """Return QWC2 themes.json for user.

        :param obj identity: User identity
        : param str lang: Viewer language
        """
        self.logger.debug('Getting themes.json for identity: %s', identity)

        # filter by permissions
        themes = self.permitted_themes(identity, lang)

        self.__update_service_urls(themes)

        return jsonify({"themes": themes})

    def __update_service_urls(self, themes):
        for item in themes.get('items', []):
            if not item.get('wms_name'):
                continue
            wms_name = item['wms_name']
            item.update({
                'url': "%s%s" % (self.ogc_service_url, wms_name),
                'featureInfoUrl': "%s%s" % (self.info_service_url, wms_name),
                'legendUrl': "%s%s?" % (self.legend_service_url, wms_name) + (
                    item["extraLegendParameters"]
                    if "extraLegendParameters" in item else "")
            })
            if item.get('print'):
                # add print URL only if print templates available
                item['printUrl'] = "%s%s" % (self.print_service_url, wms_name)

        for subdir in themes.get('subdirs', []):
            self.__update_service_urls(subdir)

    def qwc2_assets(self, path, identity, lang):
        """Return QWC2 asset from assets/ or temporary image dir.

        :param str path: Asset path
        :param str lang: Asset language
        """
        restricted_viewer_assets = self.resources['qwc2_config'].get(
            'restricted_viewer_assets', []
        )

        # get permitted viewer tasks
        permitted_viewer_assets = self.permissions_handler.resource_permissions(
            'viewer_assets', identity
        )

        if path in restricted_viewer_assets and not path in permitted_viewer_assets:
            self.logger.debug("Asset %s is not permitted, returning 404" % path)
            return abort(404)

        if not path.startswith(self.BASE64_IMAGE_ROUTE_PREFIX):

            # Special case for ui files: return translated UI
            if path.lower().endswith('.ui'):
                return self.translate_designer_form(path, lang)

            # Check if localized asset exists
            if lang:
                full_dir = os.path.dirname(os.path.join(self.qwc2_path, 'assets', path))
                basename, ext = os.path.splitext(os.path.basename(path))
                localized_file = os.path.join(basename + "_{lang}" + ext)
                if os.path.isfile(os.path.join(full_dir, localized_file.format(lang=lang))):
                    # Full locale (i.e. en-US)
                    path = os.path.join(os.path.dirname(path), localized_file.format(lang=lang))
                elif os.path.isfile(os.path.join(full_dir, localized_file.format(lang=lang[0:2]))):
                    # Lang only (i.e. en)
                    path = os.path.join(os.path.dirname(path), localized_file.format(lang=lang[0:2]))

            # send file from assets/
            return send_from_directory(
                os.path.join(self.qwc2_path, 'assets'), path
            )
        else:
            if self.images_temp_dir is not None:
                # send extracted Base64 encoded image (remove prefix)
                return send_from_directory(
                    self.images_temp_dir.name,
                    path[len(self.BASE64_IMAGE_ROUTE_PREFIX):]
                )
            else:
                # temp dir not present
                return abort(404)

    def qwc2_data(self, path):
        """Return data from data/.

        :param str path: Data path
        """
        return send_from_directory(os.path.join(self.qwc2_path, 'data'), path)

    def qwc2_js(self, path):
        """Return QWC2 Javascript from dist/.

        :param str path: Asset path
        """
        return send_from_directory(os.path.join(self.qwc2_path, 'dist'), path)

    def qwc2_translations(self, path):
        """Return QWC2 translation file from translations/.

        :param str path: Asset path
        """
        return send_from_directory(
            os.path.join(self.qwc2_path, 'translations'), path
        )

    def qwc2_favicon(self):
        """Return default favicon."""
        return send_from_directory(self.qwc2_path, 'favicon.ico')

    def load_resources(self, config):
        """Load service resources from config.

        :param RuntimeConfig config: Config handler
        """
        # load QWC2 application config
        qwc2_config = config.resources().get('qwc2_config', {})

        # load themes config
        qwc2_themes = config.resources().get('qwc2_themes', {})
        # use contents of 'themes'
        qwc2_themes = qwc2_themes.get('themes', {})

        # extract Base64 encoded thumbnail images
        self.extract_base64_theme_item_thumbnail_images(qwc2_themes)
        self.extract_base64_background_layer_thumbnail_images(qwc2_themes)

        return {
            'qwc2_config': qwc2_config,
            'qwc2_themes': qwc2_themes
        }

    def extract_base64_theme_item_thumbnail_images(self, theme_group):
        """Recursively extract any Base64 encoded theme item thumbnail images
        to files.

        :param obj theme_group: Theme group
        """
        for item in theme_group.get('items', []):
            if 'thumbnail' not in item:
                image_path = None
                if 'thumbnail_base64' in item:
                    image_path = self.extract_base64_thumbnail_image(
                        item['name'], item['thumbnail_base64']
                    )
                    # remove thumbnail_base64
                    del item['thumbnail_base64']
                if image_path is None:
                    # set default if missing or error on extract
                    image_path = self.DEFAULT_THUMBNAIL_IMAGE

                # update thumbnail path
                item['thumbnail'] = image_path

        if 'subdirs' in theme_group:
            for subgroup in theme_group['subdirs']:
                self.extract_base64_theme_item_thumbnail_images(subgroup)

    def extract_base64_background_layer_thumbnail_images(self, themes):
        """Extract any Base64 encoded background layer thumbnail images
        to files.

        :param obj themes: qwc2_themes
        """
        for layer in themes.get('backgroundLayers', []):
            if 'thumbnail' not in layer:
                image_path = None
                if 'thumbnail_base64' in layer:
                    image_path = self.extract_base64_thumbnail_image(
                        "bg_%s" % layer['name'], layer['thumbnail_base64']
                    )
                    # remove thumbnail_base64
                    del layer['thumbnail_base64']
                if image_path is None:
                    # set default if missing or error on extract
                    image_path = self.DEFAULT_THUMBNAIL_IMAGE

                # update thumbnail path
                layer['thumbnail'] = image_path

    def extract_base64_thumbnail_image(self, name, thumbnail_base64):
        """Extract Base64 encoded thumbnail image to file and return
        its assets path.

        :param str name: Image name
        :param str thumbnail_base64: Base64 encoded image
        """
        image_path = None

        try:
            if self.images_temp_dir is None:
                # create temporary target dir
                self.images_temp_dir = tempfile.TemporaryDirectory(
                    prefix='qwc-map-viewer-'
                )
                os.makedirs(
                    os.path.join(self.images_temp_dir.name, 'mapthumbs')
                )

            # NOTE: do not add a random suffix so it may be cached in clients
            filename = "%s.png" % name

            # decode and save as image file
            file_path = os.path.join(
                self.images_temp_dir.name, 'mapthumbs', filename
            )
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(thumbnail_base64))

            # mark as extracted image for assets URL
            image_path = os.path.join(
                self.BASE64_IMAGE_ROUTE_PREFIX, 'mapthumbs', filename
            )
        except Exception as e:
            image_path = None
            self.logger.error(
                "Could not extract Base64 encoded thumbnail image for '%s':"
                "\n%s" % (name, e)
            )

        return image_path

    def translate_designer_form(self, path, lang):
        """Return translated qt designed form, if possible.

        :param str path: Designed form path
        :param str lang: Desired language
        """
        # Attempt to read form
        full_path = os.path.join(self.qwc2_path, 'assets', path)
        try:
            with open(full_path, 'r') as fh:
                form = fh.read()
        except:
            return abort(404)

        if not lang:
            return Response(form, mimetype='text/xml')

        # Look for translation file
        basename = os.path.splitext(os.path.basename(path))[0]
        translation_path = os.path.join(os.path.dirname(full_path), basename + "_{lang}.ts")
        if os.path.isfile(translation_path.format(lang=lang)):
            # Full locale (i.e. en-US)
            translation_path = translation_path.format(lang=lang)
        elif os.path.isfile(translation_path.format(lang=lang[0:2])):
            # Lang only (i.e. en)
            translation_path = translation_path.format(lang=lang[0:2])
        else:
            return Response(form, mimetype='text/xml')

        # Attempt to load translation file
        try:
            with open(full_path, 'r', encoding='utf-8') as fh:
                translation = fh.read()
        except:
            return Response(form, mimetype='text/xml')

        try:
            form_document = ElementTree.fromstring(form)
            ts_document = ElementTree.fromstring(translation)
        except:
            return Response(form, mimetype='text/xml')

        # Build translation string lookup
        translations = {}
        for message in ts_document.findall(".//message"):
            source = message.find('./source')
            translation = message.find('./translation')
            if source is not None and translation is not None and translation.get('type', '') != "unfinished":
                translations[source.text] = translation.text

        for string in form_document.findall(".//string"):
            if string.get("notr", "") == "true":
                continue

            if string.text in translations:
                string.text = translations[string.text]

        form =  ElementTree.tostring(form_document, encoding='utf8', method='xml')
        return Response(form, mimetype='text/xml')

    def viewer_task_permissions(self, identity):
        """Return permissions for viewer tasks.

        :param obj identity: User identity
        """
        # get restricted viewer tasks
        restricted_viewer_tasks = self.resources['qwc2_config']. \
            get('restricted_viewer_tasks', [])

        # get permitted viewer tasks
        permitted_viewer_tasks = self.permissions_handler.resource_permissions(
            'viewer_tasks', identity
        )
        # unique set
        permitted_viewer_tasks = set(permitted_viewer_tasks)

        # set permissions
        viewer_tasks = {}
        for viewer_task in restricted_viewer_tasks:
            viewer_tasks[viewer_task] = viewer_task in permitted_viewer_tasks

        return viewer_tasks

    def permitted_themes(self, identity, lang, permitted_theme_ids=[]):
        """Return qwc2_themes filtered by permissions.

        :param obj identity: User identity
        :param list permitted_theme_ids: List of permitted theme ids
        """
        # deep copy qwc2_themes
        themes = json.loads(json.dumps(self.resources['qwc2_themes']))

        # filter theme items by permissions
        items = []
        for item in themes['items']:
            permitted_item = self.permitted_theme_item(item, identity, lang)
            if permitted_item:
                permitted_theme_ids.append(permitted_item['id'])
                items.append(permitted_item)
            else:
                self.add_restricted_item(items, item)

        themes['items'] = items

        # filter theme groups by permissions
        groups = []
        for group in themes['subdirs']:
            permitted_group = self.permitted_theme_group(group, identity, lang, permitted_theme_ids)
            if permitted_group:
                groups.append(permitted_group)

        # filter background layers by permissions
        self.filter_background_layers(themes, identity)

        # filter unused external layers
        self.filter_external_layers(themes)

        # filter unused theme info links
        self.filter_theme_info_links(themes)

        # filter unused plugin data
        self.filter_plugin_data(themes)

        return themes

    def permitted_theme_group(self, theme_group, identity, lang, permitted_theme_ids):
        """Return theme group filtered by permissions.

        :param obj theme_group: Theme group
        :param obj identity: User identity
        :param str lang: The viewer language
        :param list permitted_theme_ids: List of permitted theme ids
        """
        # collect theme items
        items = []
        for item in theme_group['items']:
            permitted_item = self.permitted_theme_item(item, identity, lang)
            if permitted_item:
                permitted_theme_ids.append(permitted_item['id'])
                items.append(permitted_item)
            else:
                self.add_restricted_item(items, item)

        theme_group['items'] = items

        # collect sub groups
        subgroups = []
        for subgroup in theme_group['subdirs']:
            # recursively filter sub group
            permitted_subgroup = self.permitted_theme_group(subgroup, identity, lang, permitted_theme_ids)
            if permitted_subgroup:
                subgroups.append(permitted_subgroup)

        theme_group['subdirs'] = subgroups

        if not items and not subgroups:
            # remove empty theme group
            return None

        return theme_group

    def add_restricted_item(self, items, item):
        """Add restricted theme item placeholders if enabled by configuration

        :param obj items: Items list to which to add the placeholder to
        :param obj item: The item for which to add the placeholder
        """
        if not self.show_restricted_themes:
            return
        if self.show_restricted_themes_whitelist and not item["name"] in self.show_restricted_themes_whitelist:
            return

        items.append({
            "id": item["id"],
            "name": item["name"],
            "title": item["title"],
            "thumbnail": item["thumbnail"],
            "restricted": True
        })

    def permitted_theme_item(self, item, identity, lang):
        """Return theme item filtered by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        :param str lang: The viewer language
        """
        # get permissions for WMS
        wms_permissions = self.permissions_handler.resource_permissions(
            'wms_services', identity, item['wms_name']
        )
        if not wms_permissions:
            # WMS not permitted
            return None

        # combine permissions
        permitted_layers = set()
        permitted_print_templates = set()
        permitted_3d_tilesets = set()
        for permission in wms_permissions:
            # collect permitted layers
            permitted_layers.update([
                layer['name'] for layer in permission['layers']
            ])
            # collect permitted print templates
            permitted_print_templates.update(
                permission.get('print_templates', [])
            )

        # filter by permissions
        self.filter_restricted_layers(item, permitted_layers)
        self.filter_print_templates(item, permitted_print_templates)
        self.filter_edit_config(item, identity)
        self.filter_item_background_layers(item, identity)
        self.filter_item_search_providers(item, identity)
        self.filter_item_external_layers(item, permitted_layers)
        self.filter_item_theme_info_links(item, identity)
        self.filter_item_plugin_data(item, identity)
        self.filter_item_snapping_config(item, identity, permitted_layers)
        self.filter_item_3d_tilesets(item, identity)
        if lang in item['translations']:
            item['translations'] = item['translations'][lang]
        else:
            item['translations'] = {}

        return item

    def filter_restricted_layers(self, layer, permitted_layers):
        """Recursively filter layers by permissions.

        :param obj layer: Layer or group layer
        :param set permitted_layers: List of permitted layers
        """
        if layer.get('sublayers'):
            # group layer
            # collect permitted sub layers
            sublayers = []
            for sublayer in layer['sublayers']:
                # check permissions
                if sublayer['name'] in permitted_layers:
                    # recursively filter sub layer
                    self.filter_restricted_layers(sublayer, permitted_layers)
                    sublayers.append(sublayer)

            layer['sublayers'] = sublayers

    def filter_print_templates(self, item, permitted_print_templates):
        """Filter print templates by permissions.

        :param obj item: Theme item
        :param set permitted_print_templates: List of permitted print templates
        """
        print_templates = [
            template for template in item.get('print', [])
            if template['name'] in permitted_print_templates
        ]

        if print_templates:
            item['print'] = print_templates
        else:
            # no print templates permitted
            # remove print configs
            item.pop('print', None)
            item.pop('printUrl', None)
            item.pop('printScales', None)
            item.pop('printResolutions', None)
            item.pop('printGrid', None)
            item.pop('printLabelConfig', None)
            item.pop('printLabelForSearchResult', None)

            for bg in item.get('backgroundLayers', []):
                bg.pop('printLayer', None)

    def filter_edit_config(self, item, identity):
        """Filter edit config by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if not item.get('editConfig'):
            # no edit config or blank
            return

        # collect permitted edit datasets
        edit_config = {}
        for name, config in item.get('editConfig').items():
            # dataset name from editDataset or WMS and name
            dataset = "%s.%s" % (item['wms_name'], name)
            dataset = config.get('editDataset', dataset)

            permitted_dataset = self.permitted_dataset(
                dataset, config, identity
            )
            if permitted_dataset:
                edit_config[name] = permitted_dataset

        if edit_config:
            item['editConfig'] = edit_config
        else:
            # no permitted datasets
            item['editConfig'] = {}

    def permitted_dataset(self, dataset, config, identity):
        """Return edit dataset filtered by permissions.

        :param str dataset: Dataset ID
        :param obj config: Edit dataset config
        :param obj identity: User identity
        """
        # get permissions for edit dataset
        dataset_permissions = self.permissions_handler.resource_permissions(
            'data_datasets', identity, dataset
        )
        if not dataset_permissions:
            # edit dataset not permitted
            return None

        # combine permissions
        permitted_attributes = set()
        writable = False
        creatable = False
        updatable = False
        deletable = False

        for permission in dataset_permissions:
            # collect permitted attributes
            permitted_attributes.update(permission.get('attributes', []))

            # allow writable and CRUD actions if any role permits them
            writable |= permission.get('writable', False)
            creatable |= permission.get('creatable', False)
            updatable |= permission.get('updatable', False)
            deletable |= permission.get('deletable', False)

        # make writable consistent with CRUD actions
        writable |= creatable and updatable and deletable

        # make CRUD actions consistent with writable
        creatable |= writable
        updatable |= writable
        deletable |= writable

        # filter attributes by permissions
        config['fields'] = [
            field for field in config.get('fields', [])
            if field['id'] in permitted_attributes
        ]

        # set CRUD permissions
        config['permissions'] = {
            'creatable': creatable,
            'updatable': updatable,
            'deletable': deletable
        }

        return config

    def filter_background_layers(self, themes, identity):
        """Filter available background layers by permissions.

        :param obj themes: qwc2_themes
        :param obj identity: User identity
        """
        # get permissions for background layers
        permitted_bg_layers = self.permissions_handler.resource_permissions(
            'background_layers', identity
        )
        all_bg_permitted = '*' in permitted_bg_layers

        # filter background layers by permissions
        themes['backgroundLayers'] = [
            layer for layer in themes['backgroundLayers']
            if layer['name'] in permitted_bg_layers or all_bg_permitted
        ]

    def filter_item_background_layers(self, item, identity):
        """Filter theme item background layers by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if not item.get('backgroundLayers'):
            # no background layers
            return

        # get permissions for background layers
        permitted_bg_layers = self.permissions_handler.resource_permissions(
            'background_layers', identity
        )
        all_bg_permitted = '*' in permitted_bg_layers

        # filter background layers by permissions
        item['backgroundLayers'] = [
            layer for layer in item['backgroundLayers']
            if layer['name'] in permitted_bg_layers or all_bg_permitted
        ]

    def filter_item_search_providers(self, item, identity):
        """Filter theme item search providers by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if 'searchProviders' in item:
            # get permissions for Solr facets
            permitted_solr_facets = \
                self.permissions_handler.resource_permissions(
                    'solr_facets', identity
                )
            all_facets_permitted = '*' in permitted_solr_facets

            for search_provider in item['searchProviders']:
                if (
                    'provider' in search_provider
                    and (
                        search_provider['provider'] == 'solr' or
                        search_provider['provider'] == 'fulltext'
                    )
                ):
                    # filter fulltext search facets by permissions
                    # NOTE: adapt from old syntax solr -> fulltext, move 'default' and 'layers' below 'params'
                    search_provider['provider'] = 'fulltext'
                    search_provider['params'] = search_provider.get('params', {})
                    default_facets = search_provider['params'].get('default', search_provider.get('default', []))
                    layer_facets = search_provider['params'].get('layers', search_provider.get('layers', {}))

                    search_provider['params']['default'] = [
                        facet for facet in default_facets
                        if facet in permitted_solr_facets or all_facets_permitted
                    ]
                    if 'default' in search_provider:
                        del search_provider['default']

                    layers = {}
                    for layer, facet in layer_facets.items():
                        if facet in permitted_solr_facets or all_facets_permitted:
                            layers[layer] = facet
                    search_provider['params']['layers'] = layers
                    if 'layers' in search_provider:
                        del search_provider['layers']

                    # filter layer searchterms
                    self.filter_layer_searchterms(item, permitted_solr_facets)

    def filter_layer_searchterms(self, layer, permitted_solr_facets):
        """Recursively filter layer searchterms by permissions.

        :param obj layer: Layer or group layer
        :param set permitted_solr_facets: List of permitted Solr facets
        """
        if layer.get('sublayers'):
            # group layer
            for sublayer in layer['sublayers']:
                # recursively filter sub layer
                self.filter_layer_searchterms(sublayer, permitted_solr_facets)
        else:
            # data layer
            if 'searchterms' in layer:
                # filter searchterms by permissions
                searchterms = [
                    facet for facet in layer['searchterms']
                    if facet in permitted_solr_facets
                ]
                if searchterms:
                    layer['searchterms'] = searchterms
                else:
                    # remove if no layer search permitted
                    del layer['searchterms']

    def filter_external_layers(self, themes):
        """Filter unused external layers.

        :param obj themes: qwc2_themes
        """
        if 'externalLayers' in themes:
            # collect used external layer names
            external_layers = self.collect_external_layers(themes)

            # filter unused external layers
            themes["externalLayers"] = [
                layer for layer in themes["externalLayers"]
                if layer['name'] in external_layers
            ]

    def collect_external_layers(self, theme_group):
        """Recursively collect used external layer names.

        :param obj theme_group: Theme group
        """
        external_layers = set()
        for item in theme_group['items']:
            for layer in item.get('externalLayers', []):
                external_layers.add(layer.get('name'))

        if 'subdirs' in theme_group:
            for subgroup in theme_group['subdirs']:
                external_layers.update(self.collect_external_layers(subgroup))

        return external_layers

    def filter_item_external_layers(self, item, permitted_layers):
        """Filter theme item external layers by permissions.

        :param obj item: Theme item
        :param set permitted_layers: List of permitted layers
        """
        if 'externalLayers' in item:
            # filter external layers by permissions
            item['externalLayers'] = [
                layer for layer in item['externalLayers']
                if layer.get('internalLayer') in permitted_layers
            ]

    def filter_theme_info_links(self, themes):
        """Filter unused theme info links.

        :param obj themes: qwc2_themes
        """
        if 'themeInfoLinks' in themes:
            # collect used theme info links
            theme_info_links = self.collect_theme_info_links(themes)

            # filter unused theme info links
            themes["themeInfoLinks"] = [
                theme_info_link for theme_info_link in themes["themeInfoLinks"]
                if theme_info_link.get('name') in theme_info_links
            ]

    def collect_theme_info_links(self, theme_group):
        """Recursively collect used theme info link entries.

        :param obj theme_group: Theme group
        """
        theme_info_links = set()
        for item in theme_group['items']:
            for entry in item.get('themeInfoLinks', {}).get('entries', []):
                theme_info_links.add(entry)

        if 'subdirs' in theme_group:
            for subgroup in theme_group['subdirs']:
                theme_info_links.update(
                    self.collect_theme_info_links(subgroup)
                )

        return theme_info_links

    def filter_item_theme_info_links(self, item, identity):
        """Filter theme item theme info links by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if 'themeInfoLinks' in item:
            # get permissions for theme info links
            permitted_theme_info_links = \
                self.permissions_handler.resource_permissions(
                    'theme_info_links', identity
                )

            # filter theme info links by permissions
            entries = [
                entry for entry in item['themeInfoLinks'].get('entries', [])
                if entry in permitted_theme_info_links
            ]
            if entries:
                item['themeInfoLinks']['entries'] = entries
            else:
                # remove if no entries permitted
                del item['themeInfoLinks']

    def filter_plugin_data(self, themes):
        """Filter unused plugin data.

        :param obj themes: qwc2_themes
        """
        if 'pluginData' in themes:
            # collect used plugin data
            plugin_data = self.collect_plugin_data(themes)

            # filter unused plugin data
            themes_plugin_data = {}
            for plugin, resources in themes["pluginData"].items():
                if plugin in plugin_data:
                    # filter plugin specific resources
                    resources = [
                        resource for resource in resources
                        if resource.get('name') in plugin_data[plugin]
                    ]
                    if resources:
                        themes_plugin_data[plugin] = resources

            themes["pluginData"] = themes_plugin_data

    def collect_plugin_data(self, theme_group):
        """Recursively collect used plugin data names.

        :param obj theme_group: Theme group
        """
        plugin_data = {}
        for item in theme_group['items']:
            for plugin, resources in item.get('pluginData', {}).items():
                if plugin not in plugin_data:
                    plugin_data[plugin] = set()
                plugin_data[plugin].update(resources)

        if 'subdirs' in theme_group:
            for subgroup in theme_group['subdirs']:
                sub_plugin_data = self.collect_plugin_data(subgroup)
                for plugin, resources in sub_plugin_data.items():
                    if plugin not in plugin_data:
                        plugin_data[plugin] = set()
                    plugin_data[plugin].update(resources)

        return plugin_data

    def filter_item_plugin_data(self, item, identity):
        """Filter theme item plugin data by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if 'pluginData' in item:
            # get permissions for theme plugin data
            permitted_plugin_data = \
                self.permissions_handler.resource_permissions(
                    'plugin_data', identity
                )

            # lookup for combined permissions by plugin
            plugin_permissions = {}
            for permission in permitted_plugin_data:
                # collect permitted plugin resources
                plugin = permission.get('name')
                if plugin not in plugin_permissions:
                    plugin_permissions[plugin] = set()
                plugin_permissions[plugin].update(
                    permission.get('resources', [])
                )

            # filter plugin data by permissions
            plugin_data = {}
            for plugin, resources in item['pluginData'].items():
                if plugin in plugin_permissions:
                    # filter plugin specific resources
                    resources = [
                        resource for resource in resources
                        if resource in plugin_permissions[plugin]
                    ]
                    if resources:
                        plugin_data[plugin] = resources

            if plugin_data:
                item['pluginData'] = plugin_data
            else:
                # remove if no plugin data permitted
                del item['pluginData']

    def filter_item_snapping_config(self, item, identity, permitted_layers):
        """Filter theme item snapping config by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        :param set permitted_layers: List of permitted layers
        """
        if 'snapping' in item:
            item['snapping']['snaplayers'] = list(
                filter(lambda entry: entry['name'] in permitted_layers, item['snapping']['snaplayers'])
            )

    def filter_item_3d_tilesets(self, item, identity):
        """Filter theme item 3d tilesets by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
        """
        if 'map3d' in item:
            # get permissions for theme info links
            permitted_3d_tilesets = \
                self.permissions_handler.resource_permissions(
                    'tilesets_3d', identity
                )

            # filter theme info links by permissions
            entries = [
                entry for entry in item['map3d'].get('tiles3d', [])
                if entry['name'] in permitted_3d_tilesets
            ]
            if entries:
                item['map3d']['tiles3d'] = entries
