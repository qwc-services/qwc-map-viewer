FROM sourcepole/qwc-uwsgi-base:alpine-v2022.01.08

# Required for pip with git repos
RUN apk add --no-cache --update git

# Required for downloading QWC2 artifact
RUN apk add --no-cache --update wget unzip

ADD . /srv/qwc_service
RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt
