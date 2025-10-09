/**
 * Robot Control Dashboard - Client Application
 * 
 * Connects to interface server (ws://robot:8080) for robot control
 * and debug manager (ws://robot:8765) for debug data
 */

// Configuration
const INTERFACE_URL = `ws://${window.location.hostname || 'localhost'}:8080`;
const DEBUG_URL = `ws://${window.location.hostname || 'localhost'}:8765`;

// WebSocket connections
let interfaceWs = null;
let debugWs = null;

// State
let robotRunning = false;
let debugEnabled = false;

// ========== Interface WebSocket (Commands & Status) ==========

function connectInterface() {
    console.log(`Connecting to interface server: ${INTERFACE_URL}`);
    
    interfaceWs = new WebSocket(INTERFACE_URL);
    
    interfaceWs.onopen = () => {
        console.log('Connected to interface server');
        updateConnectionStatus(true);
    };
    
    interfaceWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleInterfaceMessage(data);
    };
    
    interfaceWs.onerror = (error) => {
        console.error('Interface WebSocket error:', error);
        updateConnectionStatus(false);
    };
    
    interfaceWs.onclose = () => {
        console.log('Disconnected from interface server');
        updateConnectionStatus(false);
        // Reconnect after 3 seconds
        setTimeout(connectInterface, 3000);
    };
}

function handleInterfaceMessage(data) {
    console.log('Interface message:', data);
    
    if (data.type === 'status') {
        updateRobotStatus(data.data.status);
    } else if (data.type === 'robot_stopped') {
        alert(`Robot stopped with exit code: ${data.exit_code}`);
        robotRunning = false;
        debugEnabled = false;
        updateRobotStatus({
            robot_running: false,
            debug_enabled: false,
            pid: null
        });
    } else if (data.success !== undefined) {
        // Command response
        if (data.success) {
            console.log('Command succeeded:', data);
            if (data.pid) {
                // Robot started
                requestStatus();
            }
        } else {
            alert(`Error: ${data.error}`);
        }
    }
}

function sendCommand(command, args = {}) {
    if (!interfaceWs || interfaceWs.readyState !== WebSocket.OPEN) {
        alert('Not connected to interface server');
        return;
    }
    
    const message = {
        command: command,
        args: args
    };
    
    console.log('Sending command:', message);
    interfaceWs.send(JSON.stringify(message));
}

function requestStatus() {
    sendCommand('get_status');
}

// ========== Debug WebSocket (Camera, Motors, etc.) ==========

function connectDebug() {
    if (debugWs && debugWs.readyState === WebSocket.OPEN) {
        return; // Already connected
    }
    
    console.log(`Connecting to debug server: ${DEBUG_URL}`);
    
    debugWs = new WebSocket(DEBUG_URL);
    
    debugWs.onopen = () => {
        console.log('Connected to debug server');
    };
    
    debugWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleDebugMessage(data);
    };
    
    debugWs.onerror = (error) => {
        console.error('Debug WebSocket error:', error);
    };
    
    debugWs.onclose = () => {
        console.log('Disconnected from debug server');
        if (debugEnabled) {
            // Try to reconnect if debug is still enabled
            setTimeout(connectDebug, 2000);
        }
    };
}

function disconnectDebug() {
    if (debugWs) {
        debugWs.close();
        debugWs = null;
    }
}

function handleDebugMessage(data) {
    if (data.type === 'init') {
        // Initial data
        console.log('Debug init data:', data);
    } else if (data.type === 'update') {
        // Update from specific subsystem
        const subsystem = data.subsystem;
        const debugData = data.data;
        
        if (subsystem === 'camera') {
            updateCamera(debugData);
        } else if (subsystem === 'motors') {
            updateMotors(debugData);
        }
    }
}

// ========== UI Updates ==========

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');
    
    if (connected) {
        indicator.className = 'connected';
        text.textContent = 'Connected';
    } else {
        indicator.className = 'disconnected';
        text.textContent = 'Disconnected';
    }
}

function updateRobotStatus(status) {
    robotRunning = status.robot_running;
    debugEnabled = status.debug_enabled;
    
    // Update status text
    document.getElementById('robot-status').textContent = robotRunning ? 'Running' : 'Stopped';
    document.getElementById('robot-pid').textContent = status.pid || '-';
    document.getElementById('debug-status').textContent = debugEnabled ? 'Enabled' : 'Disabled';
    
    // Update button states
    document.getElementById('btn-start-debug').disabled = robotRunning;
    document.getElementById('btn-start-production').disabled = robotRunning;
    document.getElementById('btn-stop').disabled = !robotRunning;
    
    // Show/hide debug panels
    const cameraPanel = document.getElementById('camera-panel');
    const motorPanel = document.getElementById('motor-panel');
    
    if (debugEnabled) {
        cameraPanel.style.display = 'block';
        motorPanel.style.display = 'block';
        connectDebug();
    } else {
        cameraPanel.style.display = 'none';
        motorPanel.style.display = 'none';
        disconnectDebug();
    }
}

function updateCamera(data) {
    // Update FPS and frame counter
    document.getElementById('camera-fps').textContent = data.fps.toFixed(1);
    document.getElementById('camera-frame').textContent = data.frame_id;
    
    // Update camera feed image
    if (data.frame_jpeg) {
        const img = document.getElementById('camera-feed');
        img.src = `data:image/jpeg;base64,${data.frame_jpeg}`;
    }
    
    // Update detection status
    const ballStatus = document.getElementById('ball-status');
    if (data.ball_detected) {
        ballStatus.textContent = `Detected at (${data.ball_x}, ${data.ball_y})`;
        ballStatus.className = 'detection-status detected';
    } else {
        ballStatus.textContent = 'Not detected';
        ballStatus.className = 'detection-status';
    }
    
    const blueGoalStatus = document.getElementById('blue-goal-status');
    if (data.blue_goal_detected) {
        blueGoalStatus.textContent = `Detected at x=${data.blue_goal_x}`;
        blueGoalStatus.className = 'detection-status detected';
    } else {
        blueGoalStatus.textContent = 'Not detected';
        blueGoalStatus.className = 'detection-status';
    }
    
    const yellowGoalStatus = document.getElementById('yellow-goal-status');
    if (data.yellow_goal_detected) {
        yellowGoalStatus.textContent = `Detected at x=${data.yellow_goal_x}`;
        yellowGoalStatus.className = 'detection-status detected';
    } else {
        yellowGoalStatus.textContent = 'Not detected';
        yellowGoalStatus.className = 'detection-status';
    }
}

function updateMotors(data) {
    // Update motor gauges (speeds are -1.0 to 1.0)
    for (let i = 0; i < 4; i++) {
        const speed = data.motor_speeds[i];
        const percentage = ((speed + 1.0) / 2.0) * 100; // Convert to 0-100%
        
        const fill = document.getElementById(`motor-${i + 1}`);
        const val = document.getElementById(`motor-${i + 1}-val`);
        
        fill.style.width = `${percentage}%`;
        val.textContent = speed.toFixed(2);
        
        // Color based on direction
        if (speed > 0.1) {
            fill.style.backgroundColor = '#4CAF50'; // Green (forward)
        } else if (speed < -0.1) {
            fill.style.backgroundColor = '#f44336'; // Red (backward)
        } else {
            fill.style.backgroundColor = '#888'; // Gray (stopped)
        }
    }
    
    // Update watchdog status
    document.getElementById('watchdog-status').textContent = 
        data.watchdog_active ? 'Active' : 'Inactive';
}

function loadLogs() {
    sendCommand('get_logs', {lines: 100});
    
    // Handle response separately (will come as command response)
    // For now, we'll update this when we get the response
}

// ========== Event Handlers ==========

document.getElementById('btn-start-debug').addEventListener('click', () => {
    if (confirm('Start robot in DEBUG mode?')) {
        sendCommand('scylla_debug');
    }
});

document.getElementById('btn-start-production').addEventListener('click', () => {
    if (confirm('Start robot in PRODUCTION mode?')) {
        sendCommand('scylla_production');
    }
});

document.getElementById('btn-stop').addEventListener('click', () => {
    if (confirm('Stop robot?')) {
        sendCommand('stop_robot');
    }
});

document.getElementById('btn-color-ball').addEventListener('click', () => {
    sendCommand('color_calibration', {target: 'ball'});
});

document.getElementById('btn-color-blue').addEventListener('click', () => {
    sendCommand('color_calibration', {target: 'blue_goal'});
});

document.getElementById('btn-color-yellow').addEventListener('click', () => {
    sendCommand('color_calibration', {target: 'yellow_goal'});
});

document.getElementById('btn-motor-test').addEventListener('click', () => {
    sendCommand('motor_test');
});

document.getElementById('btn-refresh-logs').addEventListener('click', () => {
    loadLogs();
});

// ========== Initialization ==========

window.addEventListener('load', () => {
    console.log('Robot Control Dashboard initialized');
    connectInterface();
    
    // Request status every 5 seconds
    setInterval(requestStatus, 5000);
});
