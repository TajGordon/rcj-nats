#!/usr/bin/env python3
"""
Simple WebSocket test to debug connection issues
"""

import asyncio
from aiohttp import web

active_connections = set()

async def websocket_handler(request):
    """Handle websocket connections"""
    print(f"✓ WebSocket connection attempt from {request.remote}")
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.add(ws)
    print(f"✓ WebSocket connected! Total connections: {len(active_connections)}")
    
    try:
        # Send a test message
        await ws.send_json({'message': 'Connected successfully!'})
        
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                print(f"Received: {msg.data}")
                await ws.send_json({'echo': msg.data})
    finally:
        active_connections.discard(ws)
        print(f"✓ WebSocket disconnected. Remaining: {len(active_connections)}")
    
    return ws


async def index_handler(request):
    """Serve test HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
    <style>
        body {
            font-family: monospace;
            padding: 20px;
            background: #000;
            color: #0f0;
        }
        #log {
            border: 1px solid #0f0;
            padding: 10px;
            height: 400px;
            overflow-y: scroll;
            background: #001100;
        }
        button {
            background: #0f0;
            color: #000;
            border: none;
            padding: 10px 20px;
            margin: 10px 5px;
            cursor: pointer;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>WebSocket Connection Test</h1>
    <div>Status: <span id="status">Not connected</span></div>
    <div>
        <button onclick="testConnect()">Test Connect</button>
        <button onclick="sendTest()">Send Test Message</button>
        <button onclick="clearLog()">Clear Log</button>
    </div>
    <h3>Log:</h3>
    <div id="log"></div>
    
    <script>
        let ws = null;
        
        function log(message) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML += `[${time}] ${message}<br>`;
            logDiv.scrollTop = logDiv.scrollHeight;
            console.log(message);
        }
        
        function clearLog() {
            document.getElementById('log').innerHTML = '';
        }
        
        function testConnect() {
            log('--- Starting connection test ---');
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            log(`Protocol: ${window.location.protocol}`);
            log(`Host: ${window.location.host}`);
            log(`Constructed WebSocket URL: ${wsUrl}`);
            
            try {
                log('Creating WebSocket...');
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    log('✓ WebSocket OPENED successfully!');
                    document.getElementById('status').textContent = 'Connected ✓';
                    document.getElementById('status').style.color = '#0f0';
                };
                
                ws.onclose = (event) => {
                    log(`✗ WebSocket CLOSED - Code: ${event.code}, Reason: ${event.reason || 'none'}`);
                    document.getElementById('status').textContent = 'Disconnected ✗';
                    document.getElementById('status').style.color = '#f00';
                };
                
                ws.onerror = (error) => {
                    log(`✗ WebSocket ERROR: ${JSON.stringify(error)}`);
                    document.getElementById('status').textContent = 'Error ✗';
                    document.getElementById('status').style.color = '#f00';
                };
                
                ws.onmessage = (event) => {
                    log(`✓ Received message: ${event.data}`);
                };
                
            } catch (e) {
                log(`✗ Exception creating WebSocket: ${e.message}`);
                log(`Stack: ${e.stack}`);
            }
        }
        
        function sendTest() {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                log('✗ Cannot send - WebSocket not connected');
                return;
            }
            
            const testMsg = 'Test message at ' + new Date().toLocaleTimeString();
            log(`Sending: ${testMsg}`);
            ws.send(testMsg);
        }
        
        // Auto-connect on page load
        log('Page loaded, auto-connecting...');
        testConnect();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')


async def broadcaster():
    """Send periodic messages to all connections"""
    counter = 0
    while True:
        await asyncio.sleep(1)
        counter += 1
        
        if active_connections:
            print(f"Broadcasting message {counter} to {len(active_connections)} connections")
            for ws in list(active_connections):
                try:
                    await ws.send_json({'broadcast': f'Message #{counter}'})
                except:
                    active_connections.discard(ws)


async def start_background_tasks(app):
    """Start background tasks"""
    app['broadcaster'] = asyncio.create_task(broadcaster())


async def cleanup_background_tasks(app):
    """Cleanup background tasks"""
    app['broadcaster'].cancel()
    await app['broadcaster']


def main():
    print("="*60)
    print("Simple WebSocket Test Server")
    print("="*60)
    
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    print("\nServer starting on http://0.0.0.0:8083")
    print("Open http://localhost:8083 or http://<your-ip>:8083 in your browser")
    print("\nThis will test basic WebSocket connectivity")
    print("="*60)
    
    try:
        web.run_app(app, host='0.0.0.0', port=8083, print=lambda x: print(f"aiohttp: {x}"))
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
