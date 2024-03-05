FROM almalinux:9
RUN yum install -y git httpd gitweb
RUN mkdir /var/lib/git && chown apache:apache /var/lib/git && \
    mkdir /usr/share/httpd/.ssh && chown apache:apache /usr/share/httpd/.ssh
RUN curl -L https://github.com/git-lfs/git-lfs/releases/download/v3.4.1/git-lfs-linux-amd64-v3.4.1.tar.gz | tar -xz && \
    cd git-lfs-3.4.1 && ./install.sh && git lfs install

COPY apache.conf /etc/httpd/conf.d/
COPY gitweb.conf /etc/
COPY /bin/ /bin/

CMD /bin/startup.sh
