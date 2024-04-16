#!/bin/bash
HTTPD_USER=apache

# Move the SSH key to a place the apache daemon can use it
SSH_KEY_DEST=/usr/share/httpd/.ssh/id_rsa
cp $SSH_KEY $SSH_KEY_DEST && chown apache $SSH_KEY_DEST && chmod 400 $SSH_KEY_DEST
export SSH_KEY=$SSH_KEY_DEST

# copy docker env variables to a place where cron/apache will pick them up
# grep is a hack to avoid overwriting home directories
printenv | grep -v '\(HOME\|PATH\)' >> /etc/environment

# Ensure the apache daemon user can write to the storage directory
if ! chown $HTTPD_USER /var/lib/git ; then
  echo "$HTTP_USER cannot write to storage directory"
  exit 1
fi

# Generate a known_hosts file that trusts the specified git upstream
if ! su -l $HTTPD_USER -s /bin/sync_upstream_repo trust_repo ; then
  echo "Unable to generate known_hosts file for $REPO_URL"
  exit 1
fi

# Clone the specified git upstream
if ! su -l $HTTPD_USER -s /bin/sync_upstream_repo clone_repo ; then
  echo "Unable to clone $REPO_URL"
  exit 1
fi

# start tailing the logs that processes write to so they show up in kubernetes
touch /var/log/httpd/access_log && tail -f /var/log/httpd/access_log &
touch /var/log/httpd/error_log && tail -f /var/log/httpd/error_log &
touch /var/log/sync_repo.log && chown $HTTPD_USER /var/log/sync_repo.log && tail -f /var/log/sync_repo.log &
mkdir /var/log/wsgi/ && touch /var/log/wsgi/wsgi.log && chown -R $HTTPD_USER /var/log/wsgi/ && tail -f /var/log/wsgi/wsgi.log &

# Set the apache user's crontab 
# TODO it would be preferable to fully configure this via the Dockerfile
cat /etc/apache.cron | crontab -u $HTTPD_USER -
# Start crond in the background
crond -s

# create a data directory for persistent server data if it doesn't exist
mkdir -p $DATA_DIR && chown apache:apache $DATA_DIR
touch $DATA_DIR/.htpasswd && chown apache:apache $DATA_DIR/.htpasswd

# Start httpd
httpd -D FOREGROUND
