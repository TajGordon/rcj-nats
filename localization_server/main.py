from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from typing import Dict, Any

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates setup
templates = Jinja2Templates(directory="templates")

# Store the latest localization data
latest_data: Dict[str, Any] = {
    'position': [0.0, 0.0],
    'angle': 0.0,
    'error': float('inf'),
    'timestamp': 0
}

# WebSocket connections for clients
connections = []

@app.get('/')
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket('/ws/data')
async def websocket_data_client(ws: WebSocket):
    """WebSocket endpoint for web clients to receive localization data"""
    await ws.accept()
    connections.append(ws)
    
    try:
        # Send initial data
        await ws.send_json({
            'robot': {
                'pos': latest_data['position'],
                'angle': latest_data['angle'],
                'error': latest_data['error'],
                'timestamp': latest_data['timestamp']
            }
        })
        
        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(0.1)  # Small delay to prevent overwhelming
    except Exception as e:
        print(f"Client websocket error: {e}")
    finally:
        if ws in connections:
            connections.remove(ws)

@app.websocket('/ws/localization')
async def websocket_localization_data(ws: WebSocket):
    """WebSocket endpoint for the robot to send localization data"""
    await ws.accept()
    
    try:
        while True:
            # Receive localization data from robot
            data = await ws.receive_text()
            localization_data = json.loads(data)
            
            # Update latest data
            latest_data.update(localization_data)
            
            # Broadcast to all connected web clients
            for client_ws in connections.copy():
                try:
                    await client_ws.send_json({
                        'robot': {
                            'pos': latest_data['position'],
                            'angle': latest_data['angle'],
                            'error': latest_data['error'],
                            'timestamp': latest_data['timestamp']
                        }
                    })
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    connections.remove(client_ws)
                    
    except Exception as e:
        print(f"Localization websocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting localization server on http://localhost:8002")
    print("📍 Robot should connect to ws://localhost:8002/ws/localization")
    print("🌐 View field at http://localhost:8002")
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)