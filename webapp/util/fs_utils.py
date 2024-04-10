from pathlib import Path
from models.models import RepoListing

GIT_HOME_DIR = Path('/var/lib/git')

def list_git_repos() -> list[RepoListing]:
    repo_dirs = [d for d in GIT_HOME_DIR.iterdir() if d.is_dir()]
    return [RepoListing(name=d.name) for d in repo_dirs]

def get_git_hash(repo_name: str) -> str:
    """ Read the active git hash of the given repo
    TODO this is somewhat fragile, want to avoid spinning up a separate git cli instance
    for each client request though. 
    """
    # Get the active ref from HEAD
    git_head_file = GIT_HOME_DIR / repo_name / '.git' / 'HEAD'
    if not git_head_file.exists():
        raise RuntimeError(f"git repository {repo_name} does not exist")
    with open(git_head_file, 'r') as head:
        active_ref = head.read().strip()
    
    if not active_ref.startswith('ref:'):
        raise RuntimeError(f"Unable to parse HEAD ref: {active_ref}")
    
    # Return the hash of the active ref
    active_ref_path = GIT_HOME_DIR / repo_name / '.git' / active_ref.removeprefix('ref: ')
    with open(active_ref_path, 'r') as ref:
        return ref.read().strip()
