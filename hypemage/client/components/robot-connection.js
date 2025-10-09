/**
 * Robot Connection Helper
 * 
 * Handles WebSocket connections to robots with auto-reconnect
 */

class RobotConnection {
    constructor(name, host, interfacePort, debugPort, callbacks) {
        this.name = name;
        this.host = host;
        this.interfacePort = interfacePort;
        this.debugPort = debugPort;
        this.callbacks = callbacks;
        
        this.interfaceWs = null;
        this.debugWs = null;
        this.connected = false;
        this.reconnectInterval = 3000;
    }
    
    // ========== Interface WebSocket ==========
    
    connectInterface() {
        const url = `ws://${this.host}:${this.interfacePort}/ws`;
        
        console.log(`[${this.name}] Connecting to interface: ${url}`);
        
        this.interfaceWs = new WebSocket(url);
        
        this.interfaceWs.onopen = () => {
            console.log(`[${this.name}] Interface connected`);
            this.connected = true;
            
            if (this.callbacks.onConnect) {
                this.callbacks.onConnect('interface');
            }
            
            // Request initial status
            this.sendCommand('get_status');
        };
        
        this.interfaceWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (this.callbacks.onInterfaceMessage) {
                this.callbacks.onInterfaceMessage(data);
            }
        };
        
        this.interfaceWs.onerror = (error) => {
            console.error(`[${this.name}] Interface error:`, error);
            
            if (this.callbacks.onError) {
                this.callbacks.onError('interface', error);
            }
        };
        
        this.interfaceWs.onclose = () => {
            console.log(`[${this.name}] Interface disconnected`);
            this.connected = false;
            
            if (this.callbacks.onDisconnect) {
                this.callbacks.onDisconnect('interface');
            }
            
            // Auto-reconnect
            setTimeout(() => this.connectInterface(), this.reconnectInterval);
        };
    }
    
    // ========== Debug WebSocket ==========
    
    connectDebug() {
        const url = `ws://${this.host}:${this.debugPort}`;
        
        console.log(`[${this.name}] Connecting to debug: ${url}`);
        
        this.debugWs = new WebSocket(url);
        
        this.debugWs.onopen = () => {
            console.log(`[${this.name}] Debug connected`);
            
            if (this.callbacks.onConnect) {
                this.callbacks.onConnect('debug');
            }
        };
        
        this.debugWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (this.callbacks.onDebugMessage) {
                this.callbacks.onDebugMessage(data);
            }
        };
        
        this.debugWs.onerror = (error) => {
            console.error(`[${this.name}] Debug error:`, error);
            
            if (this.callbacks.onError) {
                this.callbacks.onError('debug', error);
            }
        };
        
        this.debugWs.onclose = () => {
            console.log(`[${this.name}] Debug disconnected`);
            
            if (this.callbacks.onDisconnect) {
                this.callbacks.onDisconnect('debug');
            }
            
            // Only reconnect if still connected to interface
            if (this.connected) {
                setTimeout(() => this.connectDebug(), this.reconnectInterval);
            }
        };
    }
    
    // ========== Commands ==========
    
    sendCommand(command, args = {}) {
        if (!this.interfaceWs || this.interfaceWs.readyState !== WebSocket.OPEN) {
            console.error(`[${this.name}] Interface not connected`);
            return false;
        }
        
        this.interfaceWs.send(JSON.stringify({ command, args }));
        return true;
    }
    
    startDebug() {
        return this.sendCommand('run_script', { script_id: 'scylla_debug' });
    }
    
    startProduction() {
        return this.sendCommand('run_script', { script_id: 'scylla_production' });
    }
    
    stop() {
        return this.sendCommand('stop_script');
    }
    
    runScript(scriptId, args = []) {
        return this.sendCommand('run_script', { script_id: scriptId, args });
    }
    
    // ========== Connection Management ==========
    
    connect() {
        this.connectInterface();
        this.connectDebug();
    }
    
    disconnect() {
        if (this.interfaceWs) {
            this.interfaceWs.close();
        }
        if (this.debugWs) {
            this.debugWs.close();
        }
        this.connected = false;
    }
}

// Export for use in main app
if (typeof window !== 'undefined') {
    window.RobotConnection = RobotConnection;
}
