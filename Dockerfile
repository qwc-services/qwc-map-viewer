FROM sourcepole/qwc-uwsgi-base:alpine-v2021.12.16

# Required for pip with git repos
RUN apk add --no-cache --update git

# Required for downloading QWC2 artifact
RUN apk add --no-cache --update wget unzip

ADD . /srv/qwc_service
RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt
