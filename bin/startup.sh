#!/bin/bash
HTTPD_USER=apache
# copy docker env variables to a place where cron/apache will pick them up
# grep is a hack to avoid overwriting home directories
printenv | grep -v '\(HOME\|PATH\)' >> /etc/environment

# Move the SSH key to a place the apache daemon can use it
if ! cp $SSH_KEY ~$HTTPD_USER/.ssh/id_rsa && chwon apache ~$HTTPD_USER/.ssh/id_rsa; then
  echo "Unable to move ssh key to $HTTPD_USER .ssh directory"
  exit 1
fi
export SSH_KEY=~$HTTPD_USER/.ssh/id_rsa

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

# Set the apache user's crontab 
# TODO it would be preferable to fully configure this via the Dockerfile
cat /etc/apache.cron | crontab -u $HTTPD_USER -
# Start crond in the background
crond -s

# Start httpd
httpd -D FOREGROUND
