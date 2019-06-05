import os

from flask import json, jsonify, redirect, render_template, Response, \
    safe_join, send_from_directory, url_for

from qwc_services_core.permission import PermissionClient


class QWC2Viewer:
    """QWC2Viewer class

    Provide configurations for QWC2 map viewer.
    """

    def __init__(self, logger):
        """Constructor

        :param Logger logger: Application logger
        """
        self.logger = logger

        self.permission = PermissionClient()

        try:
            self.auth_services_config = json.loads(
                os.environ.get('AUTH_SERVICES_CONFIG', '{}')
            )
        except Exception as e:
            self.logger.error("Could not load AUTH_SERVICES_CONFIG:\n%s" % e)
            self.auth_services_config = {}

    def qwc2_index(self, identity, viewer=None):
        """Return QWC2 index.html for user.

        :param obj identity: User identity
        :param str viewer: Optional custom viewer name (None for default)
        """
        qwc2_path = os.environ.get('QWC2_PATH', 'qwc2/')

        if viewer:
            # check custom viewer permissions
            permissions = self.permission.qwc_permissions(identity)
            if viewer not in permissions.get('viewers', []):
                # redirect to default viewer if not permitted
                return redirect(url_for('index'))

            viewers_path = os.environ.get(
                'QWC2_VIEWERS_PATH', os.path.join(qwc2_path, 'viewers')
            )

            # try to send custom viewer index '<viewer>.html'
            filename = '%s.html' % viewer
            viewer_index_file = safe_join(viewers_path, '%s' % filename)
            try:
                if os.path.isfile(viewer_index_file):
                    self.logger.debug(
                        "Using custom viewer index '%s'" % filename
                    )
                    return send_from_directory(viewers_path, filename)
                else:
                    # show FileNotFoundError error
                    raise Exception(
                        "[Errno 2] No such file or directory: '%s'" %
                        viewer_index_file
                    )
            except Exception as e:
                self.logger.error(
                    "Could not load custom viewer index '%s':\n%s" %
                    (filename, e)
                )
                # fallback to default index

        # send default index
        return send_from_directory(qwc2_path, 'index.html')

    def qwc2_config(self, identity, viewer=None):
        """Return QWC2 config.json for user.

        :param obj identity: User identity
        :param str viewer: Optional custom viewer name (None for default)
        """
        self.logger.debug('Generating config.json for identity: %s', identity)

        qwc2_path = os.environ.get('QWC2_PATH', 'qwc2/')

        permissions = self.permission.qwc_permissions(identity)

        config = None
        if viewer:
            # check custom viewer permissions
            if viewer not in permissions.get('viewers', []):
                # redirect to default config if not permitted
                return redirect(url_for('qwc2_config'))

            viewers_path = os.environ.get(
                'QWC2_VIEWERS_PATH', os.path.join(qwc2_path, 'viewers')
            )

            # try to load custom viewer config '<viewer>.json'
            filename = '%s.json' % viewer
            viewer_config_file = safe_join(viewers_path, '%s' % filename)
            try:
                self.logger.debug(
                    "Using custom viewer config '%s'" % filename
                )
                with open(viewer_config_file, encoding='utf-8') as fh:
                    config = json.load(fh)
            except Exception as e:
                self.logger.error(
                    "Could not load custom viewer config '%s':\n%s" %
                    (filename, e)
                )
                # fallback to default config

        if config is None:
            # load default config
            default_config_file = os.environ.get(
                'QWC2_CONFIG', os.path.join(qwc2_path, 'config.json')
            )
            try:
                with open(default_config_file, encoding='utf-8') as fh:
                    config = json.load(fh)
            except Exception as e:
                self.logger.error(
                    "Could not load default viewer config:\n%s" % e
                )
                return jsonify({"error": "Unable to read config.json"})

        config['proxyServiceUrl'] = self.__sanitize_url(os.environ.get(
            'PROXY_SERVICE_URL', config.get('proxyServiceUrl', '')))
        config['permalinkServiceUrl'] = self.__sanitize_url(os.environ.get(
            'PERMALINK_SERVICE_URL', config.get('permalinkServiceUrl', '')))
        config['elevationServiceUrl'] = self.__sanitize_url(os.environ.get(
            'ELEVATION_SERVICE_URL', config.get('elevationServiceUrl', '')))
        config['mapInfoService'] = self.__sanitize_url(os.environ.get(
            'MAPINFO_SERVICE_URL', config.get('mapInfoService', '')))
        config['featureReportService'] = self.__sanitize_url(os.environ.get(
            'DOCUMENT_SERVICE_URL', config.get('featureReportService', '')))
        config['editServiceUrl'] = self.__sanitize_url(os.environ.get(
            'DATA_SERVICE_URL', config.get('editServiceUrl', '')))
        config['searchServiceUrl'] = self.__sanitize_url(os.environ.get(
            'SEARCH_SERVICE_URL', config.get('searchServiceUrl', '')))
        config['wmsDpi'] = os.environ.get(
            'WMS_DPI', config.get('wmsDpi', '96'))

        # get auth service URL for base group from identity
        auth_service_url = self.auth_services_config.get(
            identity.get('group'),
            # fallback to AUTH_SERVICE_URL then viewer config
            os.environ.get(
                'AUTH_SERVICE_URL', config.get('authServiceUrl', '')
            )
        )
        config['authServiceUrl'] = self.__sanitize_url(auth_service_url)

        # Look for any Login item, and change it to logout if user is signed in
        signed_in = identity.get('username') is not None
        self.__replace_login__helper_plugins(
            config['plugins']['mobile'], signed_in)
        self.__replace_login__helper_plugins(
            config['plugins']['desktop'], signed_in)

        # filter any restricted viewer task items
        viewer_task_permissions = permissions.get('viewer_tasks', {})
        self.__filter_restricted_viewer_tasks(
            config['plugins']['mobile'], viewer_task_permissions
        )
        self.__filter_restricted_viewer_tasks(
            config['plugins']['desktop'], viewer_task_permissions
        )
        config['username'] = identity.get('username')

        return jsonify(config)

    def __sanitize_url(self, url):
        """Ensure URL ends with a slash, if not empty
        """
        return (url.rstrip('/') + '/') if url else ""

    def __replace_login__helper_plugins(self, plugins, signed_in):
        """Search plugins configurations and call
           self.__replace_login__helper_items on menuItems and toolbarItems

        :param list(obj) plugins: Plugins configurations
        :param bool signed_in: Whether user is signed in
        """
        topbars = list(filter(lambda entry: entry['name'] == 'TopBar', plugins))
        for topbar in topbars:
            if "menuItems" in topbar["cfg"]:
                self.__replace_login__helper_items(
                    topbar["cfg"]["menuItems"], signed_in)
            if "toolbarItems" in topbar["cfg"]:
                self.__replace_login__helper_items(
                    topbar["cfg"]["toolbarItems"], signed_in)

    def __replace_login__helper_items(self, items, signed_in):
        """Replace Login with Logout if identity is not None on Login items in
           menuItems and toolbarItems.

        :param list(obj) items: Menu or toolbar items
        :param bool signed_in: Whether user is signed in
        """
        for item in items:
            if item["key"] == "Login" and signed_in:
                item["key"] = "Logout"
                item["icon"] = "logout"
            elif "subitems" in item:
                self.__replace_login__helper_items(item["subitems"], signed_in)

    def __filter_restricted_viewer_tasks(self, plugins,
                                         viewer_task_permissions):
        """Remove restricted viewer task items from menu and toolbar.

        :param list(obj) plugins: Plugins configurations
        :param obj viewer_task_permissions: Viewer task permissions as
                                            {<item key>: <permitted>}
        """
        for key in viewer_task_permissions:
            if not viewer_task_permissions[key]:
                topbars = list(filter(
                    lambda entry: entry['name'] == 'TopBar', plugins
                ))
                for topbar in topbars:
                    if 'menuItems' in topbar['cfg']:
                        self.__filter_config_items(
                            topbar['cfg']['menuItems'], key
                        )
                    if 'toolbarItems' in topbar['cfg']:
                        self.__filter_config_items(
                            topbar['cfg']['toolbarItems'], key
                        )

    def __filter_config_items(self, items, key):
        """Remove items with key from menuItems and toolbarItems.

        :param list(obj) items: Menu or toolbar items
        :param str key: Item key
        """
        items_to_remove = []
        for item in items:
            if item['key'] == key:
                # collect items to remove
                items_to_remove.append(item)
            elif 'subitems' in item:
                self.__filter_config_items(item['subitems'], key)

        for item in items_to_remove:
            items.remove(item)

    def qwc2_themes(self, identity):
        """Return QWC2 themes.json for user.

        :param obj identity: User identity
        """
        self.logger.debug('Getting themes.json for identity: %s', identity)

        ogc_server_url = os.environ.get(
            'OGC_SERVICE_URL', 'http://localhost:5013/').rstrip('/') + '/'
        info_service_url = os.environ.get(
            'INFO_SERVICE_URL', ogc_server_url).rstrip('/') + '/'
        legend_service_url = os.environ.get(
            'LEGEND_SERVICE_URL', ogc_server_url).rstrip('/') + '/'
        print_service_url = os.environ.get(
            'PRINT_SERVICE_URL', ogc_server_url).rstrip('/') + '/'
        themes = self.permission.qwc_permissions(identity)
        if not themes:
            return jsonify({"error": "Failed to generate themes.json"})
        for item in themes.get('themes', {}).get('items', []):
            # update service URLs
            wms_name = item['wms_name']
            item.update({
                'url': "%s%s" % (ogc_server_url, wms_name),
                'featureInfoUrl': "%s%s" % (info_service_url, wms_name),
                'legendUrl': "%s%s" % (legend_service_url, wms_name),
                'printUrl': "%s%s" % (print_service_url, wms_name)
            })
            # NOTICE: We're updating the permission cache object!
            # del item['wms_name']

        subdirs = themes.get('themes', {}).get('subdirs', [])
        self.__update_subdir_urls(subdirs, ogc_server_url, info_service_url,
                                  legend_service_url, print_service_url)

        # remove viewer_tasks and viewers
        themes.pop('viewer_tasks', None)
        themes.pop('viewers', None)

        return jsonify(themes)

    def __update_subdir_urls(self, subdirs, ogc_server_url, info_service_url,
                             legend_service_url, print_service_url):
        for subdir in subdirs:
            if 'items' in subdir:
                for item in subdir['items']:
                    wms_name = item['wms_name']
                    item.update({
                        'url': "%s%s" % (ogc_server_url, wms_name),
                        'featureInfoUrl': "%s%s" % (info_service_url, wms_name),
                        'legendUrl': "%s%s" % (legend_service_url, wms_name),
                        'printUrl': "%s%s" % (print_service_url, wms_name)
                    })
            if 'subdirs' in subdir:
                self.__update_subdir_urls(subdir['subdirs'], ogc_server_url,
                                          info_service_url, legend_service_url,
                                          print_service_url)
