#!/bin/bash
HTTPD_USER=apache
# copy docker env variables to a place where cron/apache will pick them up
# grep is a hack to avoid overwriting home directories
printenv | grep -v '\(HOME\|PATH\)' >> /etc/environment

# Generate a known_hosts file that trusts the specified git upstream
su -l $HTTPD_USER -s /bin/sync_upstream_repo trust_repo

# Clone the specified git upstream
su -l $HTTPD_USER -s /bin/sync_upstream_repo clone_repo

# Set the apache user's crontab 
# TODO it would be preferable to fully configure this via the Dockerfile
cat /etc/apache.cron | crontab -u $HTTPD_USER -
# Start crond in the background
crond -s

# Start httpd
httpd -D FOREGROUND
