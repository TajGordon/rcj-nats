/**
 * Multi-Robot Dashboard - Main Application
 * 
 * Features:
 * - Connect to multiple robots (Storm, Necron)
 * - Switch between views (both, storm, necron)
 * - Modular widget system (camera, motors, logs, etc.)
 * - Toggle widget visibility
 */

const { createApp } = Vue;

// Robot configuration
const ROBOTS = {
    storm: {
        name: 'Storm',
        host: 'storm.local',  // Change to actual IP/hostname
        interfacePort: 8080,
        debugPort: 8765
    },
    necron: {
        name: 'Necron',
        host: 'necron.local',  // Change to actual IP/hostname
        interfacePort: 8080,
        debugPort: 8765
    }
};

// Available widget types
const AVAILABLE_WIDGETS = [
    { id: 'controls', name: 'Controls', icon: '🎮' },
    { id: 'camera', name: 'Camera', icon: '📷' },
    { id: 'motors', name: 'Motors', icon: '⚙️' },
    { id: 'localization', name: 'Position', icon: '📍' },
    { id: 'tof', name: 'ToF Sensors', icon: '📡' },
    { id: 'logs', name: 'Logs', icon: '📝' },
    { id: 'status', name: 'Status', icon: 'ℹ️' }
];

// Create Vue app
createApp({
    data() {
        return {
            currentView: 'both',  // 'both', 'storm', or 'necron'
            availableWidgets: AVAILABLE_WIDGETS,
            
            // Storm robot state
            storm: {
                name: 'Storm',
                host: ROBOTS.storm.host,
                connected: false,
                interfaceWs: null,
                debugWs: null,
                
                // Robot data
                status: 'stopped',
                pid: null,
                debugEnabled: false,
                
                // Debug data
                camera: {
                    fps: 0,
                    frame: null,
                    ballDetected: false,
                    ballPos: [0, 0],
                    goalDetected: { blue: false, yellow: false }
                },
                motors: {
                    speeds: [0, 0, 0, 0],
                    temps: [0, 0, 0, 0],
                    watchdog: true
                },
                localization: {
                    x: 0,
                    y: 0,
                    heading: 0,
                    confidence: 0
                },
                tof: {
                    readings: []
                },
                logs: [],
                
                // Widget visibility
                visibleWidgets: new Set(['controls', 'camera', 'motors', 'status'])
            },
            
            // Necron robot state (same structure)
            necron: {
                name: 'Necron',
                host: ROBOTS.necron.host,
                connected: false,
                interfaceWs: null,
                debugWs: null,
                
                status: 'stopped',
                pid: null,
                debugEnabled: false,
                
                camera: {
                    fps: 0,
                    frame: null,
                    ballDetected: false,
                    ballPos: [0, 0],
                    goalDetected: { blue: false, yellow: false }
                },
                motors: {
                    speeds: [0, 0, 0, 0],
                    temps: [0, 0, 0, 0],
                    watchdog: true
                },
                localization: {
                    x: 0,
                    y: 0,
                    heading: 0,
                    confidence: 0
                },
                tof: {
                    readings: []
                },
                logs: [],
                
                visibleWidgets: new Set(['controls', 'camera', 'motors', 'status'])
            }
        };
    },
    
    mounted() {
        // Connect to both robots on startup
        this.connectRobot('storm');
        this.connectRobot('necron');
    },
    
    methods: {
        // ========== Robot Connection ==========
        
        connectRobot(robotName) {
            const robot = this[robotName];
            
            // Connect to interface WebSocket (commands & status)
            this.connectInterface(robotName);
            
            // Connect to debug WebSocket (camera, motors, etc.)
            this.connectDebug(robotName);
        },
        
        connectInterface(robotName) {
            const robot = this[robotName];
            const url = `ws://${robot.host}:${ROBOTS[robotName].interfacePort}/ws`;
            
            console.log(`[${robot.name}] Connecting to interface: ${url}`);
            
            const ws = new WebSocket(url);
            
            ws.onopen = () => {
                console.log(`[${robot.name}] Interface connected`);
                robot.connected = true;
                
                // Request initial status
                this.sendCommand(robotName, 'get_status');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleInterfaceMessage(robotName, data);
            };
            
            ws.onerror = (error) => {
                console.error(`[${robot.name}] Interface error:`, error);
            };
            
            ws.onclose = () => {
                console.log(`[${robot.name}] Interface disconnected`);
                robot.connected = false;
                
                // Reconnect after 3 seconds
                setTimeout(() => this.connectInterface(robotName), 3000);
            };
            
            robot.interfaceWs = ws;
        },
        
        connectDebug(robotName) {
            const robot = this[robotName];
            const url = `ws://${robot.host}:${ROBOTS[robotName].debugPort}`;
            
            console.log(`[${robot.name}] Connecting to debug: ${url}`);
            
            const ws = new WebSocket(url);
            
            ws.onopen = () => {
                console.log(`[${robot.name}] Debug connected`);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleDebugMessage(robotName, data);
            };
            
            ws.onerror = (error) => {
                console.error(`[${robot.name}] Debug error:`, error);
            };
            
            ws.onclose = () => {
                console.log(`[${robot.name}] Debug disconnected`);
                
                // Only reconnect if robot is still connected to interface
                if (robot.connected && robot.debugEnabled) {
                    setTimeout(() => this.connectDebug(robotName), 3000);
                }
            };
            
            robot.debugWs = ws;
        },
        
        // ========== Message Handlers ==========
        
        handleInterfaceMessage(robotName, data) {
            const robot = this[robotName];
            
            if (data.type === 'init') {
                // Initial status
                if (data.status) {
                    robot.status = data.status.running ? 'running' : 'stopped';
                    robot.pid = data.status.pid;
                }
            } else if (data.type === 'response') {
                // Command response
                if (data.data.success !== undefined) {
                    if (data.data.pid) {
                        robot.pid = data.data.pid;
                        robot.status = 'running';
                    }
                }
            } else if (data.type === 'process_started') {
                robot.status = 'running';
                robot.pid = data.pid;
                robot.debugEnabled = data.script.includes('debug');
            } else if (data.type === 'process_stopped') {
                robot.status = 'stopped';
                robot.pid = null;
                robot.debugEnabled = false;
            }
        },
        
        handleDebugMessage(robotName, data) {
            const robot = this[robotName];
            
            if (data.type === 'update') {
                const subsystem = data.subsystem;
                const payload = data.data;
                
                if (subsystem === 'camera') {
                    robot.camera.fps = payload.fps || 0;
                    robot.camera.ballDetected = payload.ball_detected || false;
                    robot.camera.ballPos = payload.ball_pos || [0, 0];
                    robot.camera.goalDetected = payload.goal_detected || { blue: false, yellow: false };
                    
                    // Decode base64 JPEG
                    if (payload.frame_jpeg) {
                        robot.camera.frame = `data:image/jpeg;base64,${payload.frame_jpeg}`;
                    }
                } else if (subsystem === 'motors') {
                    robot.motors.speeds = payload.speeds || [0, 0, 0, 0];
                    robot.motors.temps = payload.temps || [0, 0, 0, 0];
                    robot.motors.watchdog = payload.watchdog_ok !== false;
                } else if (subsystem === 'localization') {
                    robot.localization.x = payload.x || 0;
                    robot.localization.y = payload.y || 0;
                    robot.localization.heading = payload.heading || 0;
                    robot.localization.confidence = payload.confidence || 0;
                } else if (subsystem === 'tof') {
                    robot.tof.readings = payload.readings || [];
                }
            }
        },
        
        // ========== Commands ==========
        
        sendCommand(robotName, command, args = {}) {
            const robot = this[robotName];
            
            if (!robot.interfaceWs || robot.interfaceWs.readyState !== WebSocket.OPEN) {
                console.error(`[${robot.name}] Not connected to interface`);
                return;
            }
            
            robot.interfaceWs.send(JSON.stringify({ command, args }));
        },
        
        startRobotDebug(robotName) {
            this.sendCommand(robotName, 'run_script', { script_id: 'scylla_debug' });
        },
        
        startRobotProduction(robotName) {
            this.sendCommand(robotName, 'run_script', { script_id: 'scylla_production' });
        },
        
        stopRobot(robotName) {
            this.sendCommand(robotName, 'stop_script');
        },
        
        runScript(robotName, scriptId) {
            this.sendCommand(robotName, 'run_script', { script_id: scriptId });
        },
        
        // ========== Widget Management ==========
        
        toggleWidget(robotName, widgetId) {
            const robot = this[robotName];
            
            if (robot.visibleWidgets.has(widgetId)) {
                robot.visibleWidgets.delete(widgetId);
            } else {
                robot.visibleWidgets.add(widgetId);
            }
            
            // Force reactivity update
            robot.visibleWidgets = new Set(robot.visibleWidgets);
        },
        
        isWidgetVisible(view, widgetId) {
            if (view === 'both') {
                // Check if visible in either robot
                return this.storm.visibleWidgets.has(widgetId) || 
                       this.necron.visibleWidgets.has(widgetId);
            } else {
                return this[view].visibleWidgets.has(widgetId);
            }
        },
        
        toggleWidgetForCurrentView(widgetId) {
            if (this.currentView === 'both') {
                // Toggle for both robots
                this.toggleWidget('storm', widgetId);
                this.toggleWidget('necron', widgetId);
            } else {
                // Toggle for current robot
                this.toggleWidget(this.currentView, widgetId);
            }
        }
    }
}).mount('#app');
