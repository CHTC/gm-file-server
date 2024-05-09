#!/bin/bash
HTTPD_USER=apache

# Move the SSH key to a place the apache daemon can use it
SSH_KEY_DEST=/usr/share/httpd/.ssh/id_rsa
cp $SSH_KEY $SSH_KEY_DEST && chown apache $SSH_KEY_DEST && chmod 400 $SSH_KEY_DEST
export SSH_KEY=$SSH_KEY_DEST

# copy docker env variables to a place where uvicorn/apache will pick them up
# grep is a hack to avoid overwriting home directories
printenv | grep -v '\(HOME\|PATH\)' >> /etc/environment

# Ensure the apache daemon user can write to the storage directory
if ! chown $HTTPD_USER /var/lib/git ; then
  echo "$HTTP_USER cannot write to storage directory"
  exit 1
fi

# start tailing the logs that processes write to so they show up in kubernetes
touch /var/log/httpd/access_log && tail -f /var/log/httpd/access_log &
touch /var/log/httpd/error_log && tail -f /var/log/httpd/error_log &
touch /var/log/sync_repo.log && chown $HTTPD_USER /var/log/sync_repo.log && tail -f /var/log/sync_repo.log &

# create a data directory for persistent server data if it doesn't exist
mkdir -p $DATA_DIR && chown apache:apache $DATA_DIR
touch $DATA_DIR/.htpasswd && chown apache:apache $DATA_DIR/.htpasswd

# start fastapi
su -l $HTTPD_USER -s /bin/bash -c "cd /srv/app; nohup uvicorn app:app --host 0.0.0.0 --port 8089" &

# Start httpd
httpd -D FOREGROUND
