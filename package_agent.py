from app.utils import ensure_workspace
from git import Repo
import time
def package_patch():
    repo_dir=ensure_workspace()
    repo=Repo(repo_dir)
    branch=f'autocoder/{int(time.time())}'
    if branch in repo.heads: repo.git.checkout(branch)
    else: repo.git.checkout(b=branch)
    repo.git.add(A=True)
    repo.index.commit('autocoder commit')
    diff=repo.git.diff('HEAD~1','HEAD')
    return {'branch':branch,'diff':diff}
