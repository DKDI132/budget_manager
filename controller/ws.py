import json
from typing import Optional
from config.security import verify_jwt_token
from fastapi import Cookie, APIRouter
from starlette.websockets import WebSocket
from .WebSocketManager import WebSocketManager

ws_router = APIRouter()


@ws_router.websocket("/ws/stream")
async def stream(websocket: WebSocket, auth_token: Optional[str] = Cookie(None)):
    await websocket.accept()
    manager: WebSocketManager = websocket.app.state.tv_manager

    if websocket.client.host in ("localhost", "127.0.0.1", "::1"):
        if manager.tv:
            await manager.change_tv(websocket)
        else:
            manager.tv = websocket
    else:
        if not auth_token:
            await websocket.close(code=1008)
            return
        try:
            verify_jwt_token(auth_token)
        except Exception:
            await websocket.close(code=1008)
            return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    continue
                
                elif msg_type == "register":
                    role = message.get("role")
                    if role == "streamer":
                        if manager.transmiter and manager.transmiter != websocket:
                            await websocket.close(code=1008)
                            return
                        
                        manager.transmiter = websocket
                        manager.used = True
                    continue
                    
                elif msg_type == "stop":
                    break
            except Exception:
                pass

            await manager.transmit(data, websocket)
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket)
