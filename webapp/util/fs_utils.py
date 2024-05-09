from pathlib import Path
from models.models import RepoListing
import re
import os
from models.models import RepoListing

# URL of upstream repo to use
REPO_URL = os.environ.get('REPO_URL')
# Extract the project name from an upstream URL - assumes clone via SSH
PROJECT_NAME_RE = re.compile(r'/(.*)\.git')

PROJECT_NAME = PROJECT_NAME_RE.search(REPO_URL)[1]

GIT_HOME_DIR = Path('/var/lib/git')
GIT_REPO_DIR = GIT_HOME_DIR / PROJECT_NAME



def get_latest_commit_hash() -> str:
    """ Read the active git hash of the repo
    TODO this is somewhat fragile, want to avoid spinning up a separate git cli instance
    for each client request though. 
    """
    # Get the active ref from HEAD
    git_head_file = GIT_REPO_DIR / '.git' / 'HEAD'
    if not git_head_file.exists():
        raise RuntimeError(f"Git repository {GIT_REPO_DIR} is missing its .git directory")
    with open(git_head_file, 'r') as head:
        active_ref = head.read().strip()
    
    if not active_ref.startswith('ref:'):
        raise RuntimeError(f"Unable to parse HEAD ref: {active_ref}")
    
    # Return the hash of the active ref
    active_ref_path = GIT_REPO_DIR / '.git' / active_ref.removeprefix('ref: ')
    with open(active_ref_path, 'r') as ref:
        return ref.read().strip()

def get_repo_status() -> RepoListing:
    return RepoListing(
        name=PROJECT_NAME,
        commit_hash=get_latest_commit_hash(),
        upstream=REPO_URL)
