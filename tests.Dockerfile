FROM almalinux:9

ENV DATA_DIR   /etc/gm-file-server/data
ENV API_PREFIX /api

RUN yum update -y && \
    yum install -y git httpd-tools python3-pip && \
    yum clean all && rm -rf /var/cache/yum/*

COPY test_requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

COPY webapp/ /srv/app/
