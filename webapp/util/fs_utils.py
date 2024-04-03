from pathlib import Path
from ..models.models import RepoListing
GIT_HOME_DIR = Path('/var/lib/git')

def list_git_repos() -> list[RepoListing]:
    repo_dirs = [d for d in GIT_HOME_DIR.iterdir() if d.is_dir()]
    return [RepoListing(name=d.name) for d in repo_dirs]
