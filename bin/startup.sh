#!/bin/bash
su -l apache -s /bin/sync_upstream_repo $REPO_URL $SSH_KEY 
httpd -D FOREGROUND
