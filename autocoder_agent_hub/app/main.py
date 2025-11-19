# app/main.py
"""
AutoCoder Hub - FastAPI main with lifespan (startup/shutdown) pattern.

Features:
- Loads .env from common locations (project root, .venv, app/)
- Initializes OpenAI client (new SDK or legacy fallback)
- Calls ensure_workspace() on startup
- Exposes /feature_request endpoint (sync orchestration)
- Health endpoint
"""

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import os
import logging
import traceback

# Agents/tools used by endpoints (these modules live under app/agents)
# They may import utils.ensure_workspace etc. Keep imports local inside handlers if you
# want to further delay import-time failures.
# from agents.code_agent import generate_code_files
# from agents.test_agent import run_tests
# ... (we'll import lazily in the handler to avoid import-time failures)

logger = logging.getLogger("autocoder")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------
# Utility: robust dotenv loader
# ---------------------------
def load_dotenv_locations():
    """
    Try to find and load a .env file from typical locations:
      - find_dotenv() (walks up from current working dir)
      - project_root/.env (one level above app/)
      - project_root/.venv/.env
      - app/.env
    Returns the Path that was loaded or None.
    """
    # try automatic find
    found = find_dotenv()
    if found:
        load_dotenv(found)
        return Path(found)

    # relative to this file: project root is parent of app/
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / ".env",
        project_root / ".venv" / ".env",
        project_root / "app" / ".env",
    ]
    for c in candidates:
        if c.exists():
            load_dotenv(c)
            return c
    return None

# ---------------------------
# OpenAI client initializer
# ---------------------------
def init_openai_client():
    """
    Initialize an OpenAI client. Prefer the new `openai.OpenAI` client; fallback to legacy module.
    Returns a client object (or raises if key missing).
    """
    # Validate key
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY not found in environment. Put it in .env or export the variable.")

    # Try new client API
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        logger.info("Initialized OpenAI (new OpenAI class)")
        return client
    except Exception:
        # Fallback to legacy openai usage
        try:
            import openai
            openai.api_key = OPENAI_KEY
            logger.info("Initialized OpenAI (legacy openai module)")
            return openai
        except Exception as e:
            logger.error("Failed to initialize any OpenAI client: %s", e)
            raise

# ---------------------------
# Lifespan context (startup/shutdown)
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    try:
        env_loaded = load_dotenv_locations()
        logger.info("dotenv loaded from: %s", str(env_loaded) if env_loaded else "none found")
        logger.info("OPENAI_API_KEY present: %s", bool(os.getenv("OPENAI_API_KEY")))

        # Initialize workspace/tools - lazy import to avoid import-time failures
        try:
            from app.utils import ensure_workspace
            ensure_workspace()
            logger.info("Workspace ensured.")
        except Exception as e:
            # don't crash the app; log the traceback and continue.
            logger.warning("ensure_workspace() raised an exception (continuing): %s", e)
            logger.debug(traceback.format_exc())

        # Initialize OpenAI client and attach to app.state for handlers to use
        try:
            app.state.openai_client = init_openai_client()
        except Exception as e:
            # If you want to allow the server to run without OpenAI, set client to None.
            # Here we choose to raise so developers are forced to provide the key.
            logger.error("OpenAI client initialization failed: %s", e)
            raise

    except Exception:
        logger.error("Startup failed; re-raising to stop app.")
        raise

    # Yield control — the app will run at this point
    yield

    # SHUTDOWN
    logger.info("Shutting down AutoCoder Hub...")

# ---------------------------
# Create FastAPI app with lifespan
# ---------------------------
app = FastAPI(title="AutoCoder Agent Hub", lifespan=lifespan)

# app/main.py (add near top, then after app = FastAPI(...))
from fastapi.middleware.cors import CORSMiddleware

# --- add CORS middleware (development-friendly example) ---
# In dev, allow Vite origin (default: http://localhost:5173). Replace with your real frontend origin(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # or ["*"] for quick dev (not for prod)
    allow_credentials=True,   # required if you send cookies or Authorization
    allow_methods=["*"],      # allow POST, GET, OPTIONS, etc.
    allow_headers=["*"],      # allow Content-Type, Authorization, etc.
)


# ---------------------------
# Request/response models
# ---------------------------
class FeatureRequest(BaseModel):
    title: str
    description: str

# ---------------------------
# Health endpoint
# ---------------------------
@app.get("/health")
async def health():
    """
    Basic liveness check.
    """
    ok = True
    details = {"openai_client": bool(getattr(app.state, "openai_client", None))}
    return {"ok": ok, "details": details}

# ---------------------------
# Main orchestration endpoint
# ---------------------------
@app.post("/feature_request")
def handle_feature(req: FeatureRequest):
    """
    Synchronous orchestration that:
    - asks CodeAgent to generate files (LLM)
    - writes files in temp workspace
    - runs tests and linter
    - generates docs
    - if tests pass, commits/creates branch (if git available)
    """
    # Lazy imports to avoid import-time dependency errors
    try:
        from app.utils import ensure_workspace, write_files, create_git_branch_and_commit
        # agent wrappers
        from app.agents.code_agent import generate_code_files
        from app.agents.test_agent import run_tests
        from app.agents.linter_agent import run_lint
        from app.agents.doc_agent import generate_docs
        from app.agents.package_agent import package_patch
    except Exception as e:
        logger.error("Failed to import agent modules: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent import failed: {e}")

    project_dir = ensure_workspace()

    # 1) Generate files using the code agent (LLM)
    try:
        files = generate_code_files(f"{req.title}\n\n{req.description}", "small project context")
    except Exception as e:
        logger.error("Code generation failed: %s", e)
        return {"status": "error", "stage": "code_generation", "error": str(e)}

    # 2) Create a temporary workspace copy and write files there
    import tempfile, shutil
    from pathlib import Path
    tmpdir = tempfile.mkdtemp(prefix="autocoder_")
    try:
        shutil.copytree(project_dir, tmpdir, dirs_exist_ok=True)
    except Exception as e:
        logger.warning("Copy workspace warning: %s", e)

    created_paths = []
    try:
        created_paths = write_files(tmpdir, files)
    except Exception as e:
        logger.error("Writing files failed: %s", e)
        return {"status": "error", "stage": "write_files", "error": str(e)}

    # 3) Run tests
    try:
        test_res = run_tests(tmpdir)
    except Exception as e:
        test_res = {"returncode": 1, "stdout": "", "stderr": str(e)}

    # 4) Run linter
    try:
        lint_res = run_lint(tmpdir)
    except Exception as e:
        lint_res = {"returncode": 1, "stdout": "", "stderr": str(e)}

    # 5) Generate docs
    try:
        docs = generate_docs(req.description, "files: " + ", ".join(files.keys()))
    except Exception as e:
        docs = {"readme_md": "", "usage_example": "", "error": str(e)}

    final = {
        "status": None,
        "created_files": created_paths,
        "tests": test_res,
        "lint": lint_res,
        "docs": docs,
    }

    # 6) If tests passed, copy back to the real repo and attempt to create a branch/commit
    if test_res.get("returncode", 1) == 0:
        try:
            # copy files into actual project repo
            for rel_path, content in files.items():
                dest = Path(project_dir) / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
            # Create a package/branch
            pkg = package_patch()
            final["package"] = pkg
            final["status"] = "success"
        except Exception as e:
            logger.error("Packaging/commit failed: %s", e)
            final["status"] = "packaging_failed"
            final["package_error"] = str(e)
    else:
        final["status"] = "tests_failed"

    return final

# ---------------------------
# Convenience root route
# ---------------------------
@app.get("/")
def root():
    return {"message": "AutoCoder Agent Hub running. See /health and /feature_request"}
