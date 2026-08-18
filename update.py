import os
import sys
import hmac
import subprocess
import logging
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

def get_real_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(key_func=get_real_ip)
app = FastAPI(title="Zarzadzca Updater")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zarzadca.updater")

REPO_DIR = os.getenv("REPO_DIR", os.path.dirname(os.path.abspath(__file__)))
SERVICE_NAME = os.getenv("SERVICE_NAME", "moja-apka.service")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("DEPLOY_TOKEN")
UPDATE_RATE_LIMIT = os.getenv("RATE_LIMIT_UPDATE", "5/minute")



def get_pip_executable() -> str:
    candidates = [
        os.path.join(REPO_DIR, ".venv", "bin", "pip"),
        os.path.join(REPO_DIR, "venv", "bin", "pip"),
        os.path.join(REPO_DIR, ".venv", "Scripts", "pip.exe"),
        os.path.join(REPO_DIR, "venv", "Scripts", "pip.exe"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return sys.executable.replace("python", "pip")


def update_repository():
    try:
        logger.info(f"🔄 Pobieranie zmian w katalogu: {REPO_DIR}...")
        subprocess.run(["git", "fetch", "origin", "main"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=REPO_DIR, check=True)
        
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h - %s"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"✅ Zaktualizowano do commita: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Błąd Gita: {e}")
        raise e


@app.post("/zmiana", status_code=200)
@limiter.limit(UPDATE_RATE_LIMIT)
def zmiana(request: Request, x_deploy_token: Optional[str] = Header(None, alias="X-Deploy-Token")):
    if not GITHUB_TOKEN:
        logger.error("❌ Brak zmiennej GITHUB_TOKEN lub DEPLOY_TOKEN w pliku .env!")
        raise HTTPException(status_code=500, detail="Błąd serwera: brak skonfigurowanego tokenu wdrożenia")

    if not x_deploy_token or not hmac.compare_digest(x_deploy_token, GITHUB_TOKEN):
        logger.warning("❌ Nieautoryzowana próba wywołania webhooka /zmiana!")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        update_repository()

        req_path = os.path.join(REPO_DIR, "requirements.txt")
        if os.path.exists(req_path):
            pip_path = get_pip_executable()
            logger.info(f"📦 Aktualizacja requirements.txt za pomocą: {pip_path}...")
            subprocess.run([pip_path, "install", "-r", req_path], cwd=REPO_DIR, check=True)

        logger.info(f"🔁 Restartowanie usługi {SERVICE_NAME}...")
        subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME], check=True)

        logger.info("🎉 Wdrożenie zakończone pełnym sukcesem!")
        return {"status": "success", "message": "Zaktualizowano repozytorium i zrestartowano usługę"}

    except Exception as e:
        logger.error(f"💥 Błąd podczas procesu aktualizacji: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd aktualizacji: {str(e)}")


if __name__ == "__main__":
    host = os.getenv("UPDATE_HOST", "127.0.0.1")
    port = int(os.getenv("UPDATE_PORT", "9000"))
    uvicorn.run(app, host=host, port=port)