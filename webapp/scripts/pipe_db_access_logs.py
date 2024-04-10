from db import db
from util.fs_utils import get_git_hash
import sys
import json
# TODO this will need a lot of error handling and/or some supervisor process
# that automatically restarts it - should probably look into supervisorctl

def _parse_request(req: str):
    if not req:
        return None
    method, route, *_ = req.split(' ')
    if method == 'POST' and route.startswith('/git/'):
        return route.split('/')[2]
    return None


def handle_log_line(log_line: str):
    if not log_line:
        return
    log_json = json.loads(log_line)

    client_name = log_json.get('user')
    status = log_json.get('status')
    repo = _parse_request(log_json.get('request'))

    repo_hash = get_git_hash(repo)

    if client_name and repo and status == "200":
        db.log_client_repo_access(client_name, repo, repo_hash)

with open(sys.argv[1], 'r') as input_stream:
    while True:
        log_line = input_stream.readline()
        print(log_line)
        try:
            handle_log_line(log_line)
        except Exception as e:
            print(e)
            pass
