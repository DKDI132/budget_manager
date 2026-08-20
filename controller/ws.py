import json
from typing import Optional
from config.security import verify_jwt_token
from fastapi import Cookie, APIRouter
from starlette.websockets import WebSocket
from .WebSocketManager import WebSocketManager
from config.limiter import limiter, DEFAULT_RATE_LIMIT

ws_router = APIRouter()


@ws_router.websocket("/ws/stream")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def stream(request: WebSocket, auth_token: Optional[str] = Cookie(None)):
    manager: WebSocketManager = request.app.state.tv_manager

    if request.client.host in ("localhost", "127.0.0.1", "::1"):
        if manager.tv:
            await manager.change_tv(request)
        else:
            manager.tv = request
    else:
        if not auth_token:
            await request.close(1008)
            return
        else:
            try:
                verify_jwt_token(auth_token)
                if manager.transmiter:
                    await request.close(1008)
                    return
                else:
                    manager.transmiter = request
                    manager.used = True
                    import platform
                    if "aarch64" in platform.machine():
                        import subprocess
                        subprocess.Popen(['bash', '-c', 'echo "as" | cec-client -s -d 1'])
            except Exception:
                await request.close(1008)
                return
    try:
        while True:
            data = await request.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                if msg_type == "ping":
                    continue
                elif msg_type == "stop":
                    break
            except Exception:
                pass

            await manager.transmit(data, request)
    except Exception:
        pass
    finally:
        await manager.disconnect(request)
