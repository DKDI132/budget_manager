from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.tv: WebSocket = None
        self.transmiter: WebSocket = None
        self.used: bool = False

    async def change_tv(self, websocket: WebSocket):
        conn = self.tv
        if conn:
            try:
                await conn.close()
            except:
                pass
        self.tv = websocket

    async def disconnect(self, websocket: WebSocket):
        if websocket == self.transmiter:
            self.transmiter = None
            self.used = False
            try:
                await websocket.close(1008)
            except:
                pass
        elif websocket == self.tv:
            self.tv = None
            try:
                await websocket.close(1008)
            except:
                pass

    async def transmit(self, data: str, websocket: WebSocket):
        if websocket == self.transmiter:
            receiver = self.tv
            if receiver:
                try:
                    await receiver.send_text(data)
                except:
                    await self.disconnect(receiver)
        elif websocket == self.tv:
            receiver = self.transmiter
            if receiver:
                try:
                    await receiver.send_text(data)
                except:
                    await self.disconnect(receiver)

    async def close(self):
        tv = self.tv
        transmiter = self.transmiter
        if tv:
            await self.disconnect(tv)
        if transmiter:
            await self.disconnect(transmiter)
