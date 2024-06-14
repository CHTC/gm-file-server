FROM almalinux:9
ENV REPO_URL   git@github.com/CHTC/gm-file-server
ENV SSH_KEY    /mnt/ssh_deploy_key
ENV DATA_DIR   /etc/gm-file-server/data
ENV CONFIG_DIR /etc/gm-file-server/config
ENV API_PREFIX /api

RUN yum update -y && \
    yum install -y git httpd gitweb sqlite python3-pip && \
    yum clean all && rm -rf /var/cache/yum/*

RUN mkdir /var/lib/git && chown apache:apache /var/lib/git && \
    mkdir /usr/share/httpd/.ssh && chown apache:apache /usr/share/httpd/.ssh
RUN curl -L https://github.com/git-lfs/git-lfs/releases/download/v3.4.1/git-lfs-linux-amd64-v3.4.1.tar.gz | tar -xz && \
    cd git-lfs-3.4.1 && ./install.sh && git lfs install

COPY requirements.txt /srv/
RUN pip install -r /srv/requirements.txt

COPY apache-conf/*.conf /etc/httpd/conf.d/
COPY gitweb.conf /etc/
COPY /bin/ /bin/

COPY --chown=apache webapp/ /srv/app/

CMD /bin/startup.sh
