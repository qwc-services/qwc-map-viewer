# WSGI service environment

FROM sourcepole/qwc-uwsgi-base:alpine-latest

# Required for pip with git repos
RUN apk add --no-cache --update git

# Required for downloading QWC2 artifact
RUN apk add --no-cache --update wget unzip

ARG QWC2_URL
# Optional token for download with authorization
ARG AUTH_TOKEN

ADD . /srv/qwc_service

RUN wget -O /tmp/appbundle.zip --header="PRIVATE-TOKEN: $AUTH_TOKEN" "$QWC2_URL"
RUN cd /tmp && \
    unzip appbundle.zip && \
    cd prod && \
    mkdir /qwc2 && mv * /qwc2 && \
    # Replace configurable options with template variables or docker build args
    sed --in-place \
        -e '/proxyServiceUrl/d' \
        -e 's!permalinkServiceUrl":\s*".*"!permalinkServiceUrl": "{{ permalink_service_url }}"!' \
        -e 's!elevationServiceUrl":\s*".*"!elevationServiceUrl": "{{ elevation_service_url }}"!' \
        -e 's!searchServiceUrl":\s*".*"!searchServiceUrl": "{{ search_service_url }}"!' \
        -e 's!dataproductServiceUrl":\s*".*"!dataproductServiceUrl": "{{ dataproduct_service_url }}"!' \
        -e 's!editServiceUrl":\s*".*"!editServiceUrl": "{{ data_service_url }}"!' \
        -e 's!authServiceUrl":\s*".*"!authServiceUrl": "{{ auth_service_url }}"!' \
        -e 's!mapInfoService":\s*".*"!mapInfoService": "{{ mapinfo_service_url }}"!' \
        -e 's!featureReportService":\s*".*"!featureReportService": "{{ feature_report_service_url }}"!' \
        -e 's!landRegisterService":\s*".*"!landRegisterService": "{{ land_register_extract_service_url }}"!' \
        -e 's!cccConfigService":\s*".*"!cccConfigService": "{{ ccc_config_service_url }}"!' \
        -e 's!plotInfoService":\s*".*"!plotInfoService": "{{ plotinfo_service_url }}"!' \
        -e 's!"key": "Editing",!"key": "Editing, {{editing_theme_whitelist}}",!g' \
        -e 's!"wmsDpi":.*,!"wmsDpi": "{{ wms_dpi }}",!' \
        -e 's!"minResultsExanded":.*,!"minResultsExanded": "{{ min_results_exanded }}",!' \
        -e 's!{"key": "Login", "icon": "login"}!"{{ login_logout_item }}"!g' \
        -e 's!"translationsPath"\s*:.*,!"translationsPath": "'${SERVICE_MOUNTPOINT%/}'/translations",!' \
        -e 's!"assetsPath"\s*:.*,!"assetsPath": "'${SERVICE_MOUNTPOINT%/}'/assets",!' \
        /qwc2/config.json && \
    sed -E -i 's!"logoUrl"\s*:\s*"/"(,?)!"logoUrl": "'${SERVICE_MOUNTPOINT%/}'"\1!g' \
        /qwc2/config.json && \
    rm -rf appbundle.zip

RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt