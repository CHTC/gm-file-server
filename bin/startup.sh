#!/bin/bash
printenv | grep -v '\(HOME\|PATH\)' >> /etc/environment
su -l apache -s /bin/sync_upstream_repo trust_repo
su -l apache -s /bin/sync_upstream_repo clone_repo
httpd -D FOREGROUND
