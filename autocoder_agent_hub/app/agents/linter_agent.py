from app.utils import run_command, ensure_workspace
from pathlib import Path
def run_lint(project_dir=None):
    p=Path(project_dir or ensure_workspace())
    return run_command('flake8 . --max-line-length=120 || true', cwd=p)
