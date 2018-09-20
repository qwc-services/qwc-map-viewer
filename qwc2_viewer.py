import os

from flask import json, jsonify, render_template, Response

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

    def qwc2_config(self, username):
        """Return QWC2 config.json for user.

        :param str username: User name
        """
        self.logger.debug('Generating config.json for username: %s', username)

        qwc2_path = os.environ.get('QWC2_PATH', 'qwc2/')
        configfile = os.environ.get('QWC2_CONFIG',
                               os.path.join(qwc2_path, 'config.json'))
        with open(configfile, encoding='utf-8') as fh:
            config = json.load(fh)

        config['proxyServiceUrl'] = os.environ.get('PROXY_SERVICE_URL', config.get('proxyServiceUrl', '')).rstript('/') + '/'
        config['permalinkServiceUrl'] = os.environ.get('PERMALINK_SERVICE_URL', config.get('permalinkServiceUrl', '')).rstript('/') + '/'
        config['elevationServiceUrl'] = os.environ.get('ELEVATION_SERVICE_URL', config.get('elevationServiceUrl', '')).rstript('/') + '/'
        config['mapInfoService'] = os.environ.get('MAPINFO_SERVICE_URL', config.get('mapInfoService', '')).rstript('/') + '/'
        config['featureReportService'] = os.environ.get('DOCUMENT_SERVICE_URL', config.get('featureReportService', '')).rstript('/') + '/'
        config['editServiceUrl'] = os.environ.get('DATA_SERVICE_URL', config.get('editServiceUrl', '')).rstript('/') + '/'
        config['searchServiceUrl'] = os.environ.get('SEARCH_SERVICE_URL', config.get('searchServiceUrl', '')).rstript('/') + '/'
        config['authServiceUrl'] = os.environ.get('AUTH_SERVICE_URL', config.get('authServiceUrl', '')).rstript('/') + '/'
        config['wmsDpi'] = os.environ.get('WMS_DPI', config.get('wmsDpi', '96'))

        # Look for any Login item, and change it to logout if username is not None
        self.__replace_login__helper_plugins(config['plugins']['mobile'], username)
        self.__replace_login__helper_plugins(config['plugins']['desktop'], username)

        return jsonify(config)

    def __replace_login__helper_plugins(self, plugins, username):
        """Search plugins configurations and call
           self.__replace_login__helper_items on menuItems and toolbarItems
        """
        topbars = filter(lambda entry: entry['name'] == 'TopBar', plugins)
        for topbar in topbars:
            if "menuItems" in topbar["cfg"]:
                self.__replace_login__helper_items(topbar["cfg"]["menuItems"], username)
            if "toolbarItems" in topbar["cfg"]:
                self.__replace_login__helper_items(topbar["cfg"]["toolbarItems"], username)

    def __replace_login__helper_items(self, items, username):
        """Replace Login with Logout if username is not None on Login items in
           menuItems and toolbarItems.
        """
        for item in items:
            if item["key"] == "Login" and username is not None:
                item["key"] = "Logout"
                item["icon"] = "logout"
            elif "subitems" in item:
                self.__replace_login__helper_items(item["subitems"], username)

    def qwc2_themes(self, username):
        """Return QWC2 themes.json for user.

        :param str username: User name
        """
        self.logger.debug('Getting themes.json for username: %s', username)

        ogc_server_url = os.environ.get('OGC_SERVICE_URL', 'http://localhost:5013/').rstript('/') + '/'
        info_service_url = os.environ.get('INFO_SERVICE_URL', ogc_server_url).rstript('/') + '/'
        legend_service_url = os.environ.get('LEGEND_SERVICE_URL', ogc_server_url).rstript('/') + '/'
        print_service_url = os.environ.get('PRINT_SERVICE_URL', ogc_server_url).rstript('/') + '/'
        themes = self.permission.qwc_permissions(username)
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

        return jsonify(themes)
