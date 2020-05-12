import os

from flask import json, jsonify, send_from_directory

from qwc_services_core.permissions_reader import PermissionsReader
from qwc_services_core.runtime_config import RuntimeConfig


class QWC2Viewer:
    """QWC2Viewer class

    Provide configurations for QWC2 map viewer.
    """

    def __init__(self, tenant, logger):
        """Constructor

        :param str tenant: Tenant ID
        :param Logger logger: Application logger
        """
        self.tenant = tenant
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

        # get config dir for tenant
        self.config_dir = os.path.dirname(
            RuntimeConfig.config_file_path('mapViewer', tenant)
        )

        self.resources = self.load_resources(config)
        self.permissions_handler = PermissionsReader(tenant, logger)

    def qwc2_index(self, identity):
        """Return QWC2 index.html for user.

        :param obj identity: User identity
        """
        # check if index file is present
        viewer_index_file = os.path.join(self.config_dir, 'index.html')
        if not os.path.isfile(viewer_index_file):
            # show FileNotFoundError error
            raise Exception(
                "[Errno 2] No such file or directory: '%s'" %
                viewer_index_file
            )

        # send index.html from config dir
        self.logger.debug("Using index '%s'" % viewer_index_file)
        return send_from_directory(self.config_dir, 'index.html')

    def qwc2_config(self, identity):
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
            config['featureReportService'] = self.document_service_url
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
        if identity:
            if isinstance(identity, dict):
                username = identity.get('username')
                # NOTE: ignore group from identity
            else:
                # identity is username
                username = identity

        # Look for any Login item, and change it to logout if user is signed in
        signed_in = username is not None
        self.__replace_login__helper_plugins(
            config['plugins']['mobile'], signed_in)
        self.__replace_login__helper_plugins(
            config['plugins']['desktop'], signed_in)

        # filter any restricted viewer task items
        viewer_task_permissions = self.viewer_task_permissions(identity)
        self.__filter_restricted_viewer_tasks(
            config['plugins']['mobile'], viewer_task_permissions
        )
        self.__filter_restricted_viewer_tasks(
            config['plugins']['desktop'], viewer_task_permissions
        )
        config['username'] = username

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

        # filter by permissions
        themes = self.permitted_themes(identity)

        for item in themes.get('items', []):
            # update service URLs
            wms_name = item['wms_name']
            item.update({
                'url': "%s%s" % (self.ogc_service_url, wms_name),
                'featureInfoUrl': "%s%s" % (self.info_service_url, wms_name),
                'legendUrl': "%s%s" % (self.legend_service_url, wms_name)
            })
            if item.get('print'):
                # add print URL only if print templates available
                item['printUrl'] = "%s%s" % (self.print_service_url, wms_name)

        subdirs = themes.get('subdirs', [])
        self.__update_subdir_urls(
            subdirs, self.ogc_service_url, self.info_service_url,
            self.legend_service_url, self.print_service_url
        )

        return jsonify({"themes": themes})

    def __update_subdir_urls(self, subdirs, ogc_server_url, info_service_url,
                             legend_service_url, print_service_url):
        for subdir in subdirs:
            if 'items' in subdir:
                for item in subdir['items']:
                    wms_name = item['wms_name']
                    item.update({
                        'url': "%s%s" % (ogc_server_url, wms_name),
                        'featureInfoUrl': "%s%s" % (info_service_url, wms_name),
                        'legendUrl': "%s%s" % (legend_service_url, wms_name)
                    })
                    if item.get('print'):
                        # add print URL only if print templates available
                        item['printUrl'] = "%s%s" % (
                            print_service_url, wms_name
                        )
            if 'subdirs' in subdir:
                self.__update_subdir_urls(subdir['subdirs'], ogc_server_url,
                                          info_service_url, legend_service_url,
                                          print_service_url)

    def qwc2_assets(self, path):
        """Return QWC2 asset from assets/.

        :param str path: Asset path
        """
        return send_from_directory(
            os.path.join(self.qwc2_path, 'assets'), path
        )

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

        return {
            'qwc2_config': qwc2_config,
            'qwc2_themes': qwc2_themes
        }

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

    def permitted_themes(self, identity):
        """Return qwc2_themes filtered by permissions.

        :param obj identity: User identity
        """
        # deep copy qwc2_themes
        themes = json.loads(json.dumps(self.resources['qwc2_themes']))

        # filter theme items by permissions
        items = []
        for item in themes['items']:
            permitted_item = self.permitted_theme_item(item, identity)
            if permitted_item:
                items.append(permitted_item)

        themes['items'] = items

        # filter theme groups by permissions
        groups = []
        for group in themes['subdirs']:
            permitted_group = self.permitted_theme_group(group, identity)
            if permitted_group:
                groups.append(permitted_group)

        # filter background layers by permissions
        self.filter_background_layers(themes, identity)

        # filter unused external layers
        self.filter_external_layers(themes)

        return themes

    def permitted_theme_group(self, theme_group, identity):
        """Return theme group filtered by permissions.

        :param obj theme_group: Theme group
        :param obj identity: User identity
        """
        # collect theme items
        items = []
        for item in theme_group['items']:
            permitted_item = self.permitted_theme_item(item, identity)
            if permitted_item:
                items.append(permitted_item)

        theme_group['items'] = items

        # collect sub groups
        subgroups = []
        for subgroup in theme_group['subdirs']:
            # recursively filter sub group
            permitted_subgroup = self.permitted_theme_group(subgroup, identity)
            if permitted_subgroup:
                subgroups.append(permitted_subgroup)

        theme_group['subdirs'] = subgroups

        if not items and not subgroups:
            # remove empty theme group
            return None

        return theme_group

    def permitted_theme_item(self, item, identity):
        """Return theme item filtered by permissions.

        :param obj item: Theme item
        :param obj identity: User identity
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
        self.filter_item_external_layers(item, permitted_layers)

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
            template for template in item["print"]
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
            item['editConfig'] = None

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
        for permission in dataset_permissions:
            # collect permitted attributes
            permitted_attributes.update(permission.get('attributes', []))

        # filter attributes by permissions
        config['fields'] = [
            field for field in config['fields']
            if field['name'] in permitted_attributes
        ]

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

        # filter background layers by permissions
        themes['backgroundLayers'] = [
            layer for layer in themes['backgroundLayers']
            if layer['name'] in permitted_bg_layers
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

        # filter background layers by permissions
        item['backgroundLayers'] = [
            layer for layer in item['backgroundLayers']
            if layer['name'] in permitted_bg_layers
        ]

    def filter_external_layers(self, themes):
        """Filter unused external layers.

        :param obj themes: qwc2_themes
        """
        if 'externalLayers' in themes:
            # collect used external layer names
            external_layers = self.collectExternalLayers(themes)

            # filter unused external layers
            themes["externalLayers"] = [
                layer for layer in themes["externalLayers"]
                if layer['name'] in external_layers
            ]

    def collectExternalLayers(self, theme_group):
        """Recursively collect used external layer names.

        :param obj theme_group: Theme group
        """
        external_layers = set()
        for item in theme_group['items']:
            for layer in item.get('externalLayers', []):
                external_layers.add(layer.get('name'))

        if 'subdirs' in theme_group:
            for subgroup in theme_group['subdirs']:
                external_layers.update(self.collectExternalLayers(subgroup))

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
