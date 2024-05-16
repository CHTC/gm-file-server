#!/usr/bin/env python3
import subprocess
import os
import signal
from contextlib import contextmanager
import re
from pathlib import Path
import sys
from models.models import RepoListing
from datetime import datetime
from db.db import log_commit_fetch

# Location of locally cloned version of repo
GIT_PROJECT_ROOT = Path('/var/lib/git/')

# Extract the socket name from the stdout of ssh-agent
SSH_AUTH_SOCK_RE = re.compile(r'SSH_AUTH_SOCK=([^;]*);')
# Extract the agent PID from the stdout of ssh-agent
SSH_AGENT_PID_RE = re.compile(r'SSH_AGENT_PID=([^;]*);')
# Extract the project name from an upstream URL - assumes clone via SSH
PROJECT_NAME_RE = re.compile(r'/(.*)\.git')
# Extract the project host from an upstream URL - assumes clone via SSH
PROJECT_HOST_RE = re.compile(r'git@(.*):')

# URL of upstream repo to use
REPO_URL = os.environ.get('REPO_URL')
# SSH key to use to authenticate to the upstream repo
SSH_KEY  = os.environ.get('SSH_KEY')

PROJECT_NAME = PROJECT_NAME_RE.search(REPO_URL)[1]


@contextmanager
def ssh_agent_session(ssh_key_path: str):
    """ Run the context within an eval $(ssh-agent), closing the agent at the end """
    ssh_agent_out, ssh_agent_err = subprocess.Popen('ssh-agent', stdout=subprocess.PIPE).communicate()
    socket_line, pid_line, *_ = [l.decode() for l in ssh_agent_out.splitlines()]

    socket_match = SSH_AUTH_SOCK_RE.search(socket_line)
    pid_match = SSH_AGENT_PID_RE.search(pid_line)
    if not socket_match or not pid_match:
        raise RuntimeError(f"Unexpected ssh-agent output: {ssh_agent_out.decode()}")

    os.environ['SSH_AUTH_SOCK'] = socket_match[1]
    os.environ['SSH_AGENT_PID'] = pid_match[1]

    try:
        subprocess.run(['ssh-add', ssh_key_path])
        yield
    finally:
        os.kill(int(os.environ['SSH_AGENT_PID']), signal.SIGTERM)

def get_repo_name_from_url(repo_url: str):
    """ Extract the name of a repo from its upstream url """
    if not (repo_name_match := PROJECT_NAME_RE.search(repo_url)):
        raise RuntimeError(f"Unable to determine repo name from {repo_url}")
    return repo_name_match[1]


def trust_upstream_host():
    """ Add a host's fingerprints to known_hosts prior to cloning """
    if not (host_match := PROJECT_HOST_RE.search(REPO_URL)):
        raise RuntimeError(f"Unable to determine remote upstream host name from {REPO_URL}")

    with open(Path.home() / '.ssh' / 'known_hosts', 'a') as known_hosts:
        subprocess.run(['ssh-keyscan', host_match[1]], stdout=known_hosts)

def cloned_repo_exists(repo_url: str):
    """ Check whether the given repo is already cloned. If it is, confirm the origin is correct """
    repo_name = get_repo_name_from_url(repo_url)
    repo_dir = GIT_PROJECT_ROOT / repo_name

    if not repo_dir.exists():
        return False

    upstream_info, _ = subprocess.Popen(['git','config','--get','remote.origin.url'],
                                        cwd=repo_dir,stdout=subprocess.PIPE).communicate()
    upstream_url = upstream_info.decode().strip()

    if upstream_url != repo_url:
        raise RuntimeError(f"Local version of repo has unexpected upstream {upstream_url}")
    
    return True

def log_latest_commit():
    """ Add an entry to the access tracking database indicating that a new commit has been
    pulled from upstream 
    """
    repo_dir = GIT_PROJECT_ROOT / PROJECT_NAME
    commit_info, _ = subprocess.Popen(['git','show','--no-patch','--format=%H,%ct','HEAD'],
                                      stdout=subprocess.PIPE, cwd=repo_dir).communicate()
    commit_hash, commit_timestamp = commit_info.decode().strip().split(',')
    log_commit_fetch(commit_hash, datetime.fromtimestamp(int(commit_timestamp)))

    
def clone_repo():
    """ Clone the repo at the given url """

    if cloned_repo_exists(REPO_URL):
        sync_repo()
        return

    with ssh_agent_session(SSH_KEY):
        repo_name = get_repo_name_from_url(REPO_URL)
        subprocess.run(['git', 'clone', REPO_URL, repo_name], cwd=GIT_PROJECT_ROOT)
        log_latest_commit()

def sync_repo():
    """ Hard reset the state of the repo to the given upstream """
    with ssh_agent_session(SSH_KEY):
        repo_name = PROJECT_NAME_RE.search(REPO_URL)[1]
        repo_dir = GIT_PROJECT_ROOT / repo_name
        branch_info, _ = subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stdout=subprocess.PIPE, cwd=repo_dir).communicate()
        branch_name = branch_info.decode().strip()
        subprocess.run(['git', 'fetch', '--all'], cwd=repo_dir)
        subprocess.run(['git', 'reset', '--hard', f'origin/{branch_name}'], cwd=repo_dir)
        log_latest_commit()

def get_latest_commit_hash() -> str:
    """ Read the active git hash of the repo
    TODO this is somewhat fragile, want to avoid spinning up a separate git cli instance
    for each client request though. 
    """
    # Get the active ref from HEAD
    git_repo_dir = GIT_PROJECT_ROOT / PROJECT_NAME_RE.search(REPO_URL)[1]
    git_head_file = git_repo_dir / '.git' / 'HEAD'
    if not git_head_file.exists():
        raise RuntimeError(f"Git repository {git_repo_dir} is missing its .git directory")
    with open(git_head_file, 'r') as head:
        active_ref = head.read().strip()
    
    if not active_ref.startswith('ref:'):
        raise RuntimeError(f"Unable to parse HEAD ref: {active_ref}")
    
    # Return the hash of the active ref
    active_ref_path = git_repo_dir / '.git' / active_ref.removeprefix('ref: ')
    with open(active_ref_path, 'r') as ref:
        return ref.read().strip()

def get_repo_status() -> RepoListing:
    return RepoListing(
        name=PROJECT_NAME,
        commit_hash=get_latest_commit_hash(),
        upstream=REPO_URL)
