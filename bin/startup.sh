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

# Add a FIFO for updating the DB based on access logging
LOG_FIFO=/tmp/httpd/access_log.pipe
mkdir -p /tmp/httpd
mkfifo $LOG_FIFO && chown -R $HTTPD_USER /tmp/httpd
# Create a reader for the fifo so it doesn't block httpd on startup TODO this is hacky
su -l $HTTPD_USER -s /bin/bash -c "cd /srv/app; nohup python3 -m scripts.pipe_db_access_logs $LOG_FIFO" &

# Set the apache user's crontab 
# TODO it would be preferable to fully configure this via the Dockerfile
cat /etc/apache.cron | crontab -u $HTTPD_USER -
# Start crond in the background
crond -s

# create a data directory for persistent server data if it doesn't exist
mkdir -p $DATA_DIR && chown apache:apache $DATA_DIR
touch $DATA_DIR/.htpasswd && chown apache:apache $DATA_DIR/.htpasswd

# start fastapi
su -l $HTTPD_USER -s /bin/bash -c "cd /srv/app; nohup uvicorn app:app --host 0.0.0.0 --port 8089 > /var/log/wsgi/wsgi.log" &

# Start httpd
httpd -D FOREGROUND
