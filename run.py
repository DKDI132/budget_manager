import os
from dotenv import load_dotenv
import uvicorn
from controller.controller import app

load_dotenv()

host = os.environ.get("HOST", "127.0.0.1")
port = int(os.environ.get("PORT", "8005"))

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
