from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.get('/')
async def root():
    return {"message": "Hello world!"}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)