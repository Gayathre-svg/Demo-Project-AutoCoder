# app/utils.py
"""
Utility helpers for the AutoCoder Hub.
This version is defensive: it avoids raising at import time if git is missing,
and provides write_files used by the coordinator.
"""

import os
import subprocess
from pathlib import Path
import tempfile
import shutil
import time

# Lazy import helper for GitPython Repo (returns None if git not available)
def _get_git_repo(path: Path):
    try:
        from git import Repo
    except Exception:
        return None
    try:
        return Repo(path)
    except Exception:
        return None

def ensure_workspace():
    """
    Create workspace/sample_project and an initial commit if git available.
    Does not raise if git is missing; returns Path to the sample project.
    """
    base = Path(__file__).resolve().parent / "workspace" / "sample_project"
    base.mkdir(parents=True, exist_ok=True)

    # create minimal sample files if missing
    if not (base / "hello.py").exists():
        (base / "hello.py").write_text('def greet(name):\\n    return f"Hello, {name}"\\n')
    if not (base / "test_hello.py").exists():
        (base / "test_hello.py").write_text(
            'from hello import greet\\n\\ndef test_greet():\\n    assert greet("World") == "Hello, World"\\n'
        )

    # Attempt to initialize git repo if possible (non-fatal)
    repo = _get_git_repo(base)
    if repo is None:
        # try to see if git is on PATH and use subprocess to initialize
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            git_available = True
        except Exception:
            git_available = False

        if git_available and not (base / ".git").exists():
            try:
                subprocess.run(["git", "init"], cwd=str(base), check=True)
                subprocess.run(["git", "add", "."], cwd=str(base), check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(base), check=True)
            except Exception:
                # non-fatal
                pass
    else:
        # Repo object exists — ensure initial commit exists
        try:
            if not repo.head.is_valid():
                repo.index.add(["hello.py", "test_hello.py"])
                repo.index.commit("Initial sample project")
        except Exception:
            pass

    return base

def run_command(cmd, cwd=None, timeout=60):
    """
    Run a shell command and return dict with returncode, stdout, stderr.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": "timeout"}

def write_files(base_dir, files: dict):
    """
    Write files into base_dir.

    Args:
      base_dir: path to project directory (str or Path)
      files: dict mapping relative_path -> content (string)

    Returns:
      list of absolute paths written (strings)
    """
    base_dir = Path(base_dir)
    created = []
    for rel_path, content in files.items():
        p = base_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        created.append(str(p))
    return created

def create_git_branch_and_commit(repo_dir, branch_name, commit_msg):
    """
    Attempt to create branch and commit using GitPython if available.
    Returns a dict describing result. Does not raise if git missing.
    """
    repo_dir = Path(repo_dir)
    repo = _get_git_repo(repo_dir)
    if repo is None:
        return {"ok": False, "reason": "git not available; branch/commit skipped", "branch": None}

    try:
        origin_head = None
        try:
            origin_head = repo.active_branch.name if not repo.head.is_detached else None
        except Exception:
            origin_head = None

        if branch_name in [h.name for h in repo.heads]:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout(b=branch_name)
        repo.git.add(A=True)
        repo.index.commit(commit_msg)
        # produce a diff for the last commit
        diff = repo.git.diff(f"{origin_head or 'HEAD~1'}..HEAD")
        return {"ok": True, "branch": branch_name, "commit": commit_msg, "diff": diff}
    except Exception as e:
        return {"ok": False, "reason": str(e)}
