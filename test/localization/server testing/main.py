from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio
import math

app = FastAPI()

# mount teh static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# tempaltes setup
templates = Jinja2Templates(directory="templates")

@app.get('/')
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket('/ws/data')
async def websocket_data(ws: WebSocket):
    await ws.accept()
    pos = [0., 0.]
    angle = 0.
    # while True:
    #     await ws.send_text('hello, client!')
    while True:
        await ws.send_json({
            'hyperion': {
                'pos': pos,
                'angle': angle
            }
        })
        pos[0] += 1
        pos[1] += 1
        angle += math.pi/256
        if pos[0] > 300:
            pos[0] = -300
        if pos[1] > 300:
            pos[1] = -300
        if angle >= math.pi:
            angle = -math.pi
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)