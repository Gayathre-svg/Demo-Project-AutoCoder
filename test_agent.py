from app.utils import run_command, ensure_workspace
from pathlib import Path
def run_tests(project_dir=None):
    p=Path(project_dir or ensure_workspace())
    return run_command('pytest -q --maxfail=1', cwd=p)
