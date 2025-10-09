/**
 * Multi-Robot Dashboard
 * Vue.js-powered dashboard for controlling Storm and Necron robots
 */

const { createApp } = Vue;

// Robot configuration - EDIT THESE IPs
const ROBOT_CONFIG = {
    storm: { name: 'Storm', host: 'localhost', interfacePort: 8080, debugPort: 8765 },
    necron: { name: 'Necron', host: 'localhost', interfacePort: 8081, debugPort: 8766 }
};

const AVAILABLE_WIDGETS = [
    { id: 'controls', name: 'Controls', icon: '🎮' },
    { id: 'camera', name: 'Camera', icon: '📷' },
    { id: 'motors', name: 'Motors', icon: '⚙️' },
    { id: 'status', name: 'Status', icon: 'ℹ️' }
];

createApp({
    data() {
        return {
            currentView: 'both',
            availableWidgets: AVAILABLE_WIDGETS,
            storm: this.createRobotState('storm'),
            necron: this.createRobotState('necron')
        };
    },
    
    mounted() {
        this.connectRobot('storm');
        this.connectRobot('necron');
    },
    
    methods: {
        createRobotState(name) {
            return {
                name: ROBOT_CONFIG[name].name,
                host: ROBOT_CONFIG[name].host,
                connected: false,
                interfaceWs: null,
                debugWs: null,
                status: 'stopped',
                pid: null,
                debugEnabled: false,
                camera: { fps: 0, frame: null },
                motors: { speeds: [0, 0, 0, 0], temps: [0, 0, 0, 0] },
                logs: [],
                visibleWidgets: new Set(['controls', 'camera', 'motors', 'status'])
            };
        },
        
        connectRobot(robotName) {
            this.connectInterface(robotName);
            this.connectDebug(robotName);
        },
        
        connectInterface(robotName) {
            const robot = this[robotName];
            const config = ROBOT_CONFIG[robotName];
            const url = `ws://${config.host}:${config.interfacePort}/ws`;
            
            console.log(`[${robot.name}] Connecting to interface: ${url}`);
            
            const ws = new WebSocket(url);
            
            ws.onopen = () => {
                console.log(`[${robot.name}] Interface connected`);
                robot.connected = true;
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
                setTimeout(() => this.connectInterface(robotName), 3000);
            };
            
            robot.interfaceWs = ws;
        },
        
        connectDebug(robotName) {
            const robot = this[robotName];
            const config = ROBOT_CONFIG[robotName];
            const url = `ws://${config.host}:${config.debugPort}`;
            
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
                if (robot.connected && robot.debugEnabled) {
                    setTimeout(() => this.connectDebug(robotName), 3000);
                }
            };
            
            robot.debugWs = ws;
        },
        
        handleInterfaceMessage(robotName, data) {
            const robot = this[robotName];
            
            if (data.type === 'status') {
                robot.status = data.data.robot_running ? 'running' : 'stopped';
                robot.pid = data.data.pid;
                robot.debugEnabled = data.data.debug_enabled || false;
            } else if (data.type === 'process_started') {
                robot.status = 'running';
                robot.pid = data.pid;
                robot.debugEnabled = data.script && data.script.includes('debug');
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
                    if (payload.frame_jpeg) {
                        robot.camera.frame = `data:image/jpeg;base64,${payload.frame_jpeg}`;
                    }
                } else if (subsystem === 'motors') {
                    robot.motors.speeds = payload.speeds || [0, 0, 0, 0];
                    robot.motors.temps = payload.temps || [0, 0, 0, 0];
                }
            }
        },
        
        sendCommand(robotName, command, args = {}) {
            const robot = this[robotName];
            
            if (!robot.interfaceWs || robot.interfaceWs.readyState !== WebSocket.OPEN) {
                console.error(`[${robot.name}] Not connected`);
                return;
            }
            
            robot.interfaceWs.send(JSON.stringify({ command, args }));
        },
        
        startRobotDebug(robotName) {
            this.sendCommand(robotName, 'run_script', { script_id: 'scylla_debug' });
        },
        
        stopRobot(robotName) {
            this.sendCommand(robotName, 'stop_script');
        },
        
        toggleWidget(robotName, widgetId) {
            const robot = this[robotName];
            
            if (robot.visibleWidgets.has(widgetId)) {
                robot.visibleWidgets.delete(widgetId);
            } else {
                robot.visibleWidgets.add(widgetId);
            }
            
            // Force Vue reactivity
            robot.visibleWidgets = new Set(robot.visibleWidgets);
        },
        
        isWidgetVisible(view, widgetId) {
            if (view === 'both') {
                return this.storm.visibleWidgets.has(widgetId) || this.necron.visibleWidgets.has(widgetId);
            } else {
                return this[view].visibleWidgets.has(widgetId);
            }
        },
        
        toggleWidgetForCurrentView(widgetId) {
            if (this.currentView === 'both') {
                this.toggleWidget('storm', widgetId);
                this.toggleWidget('necron', widgetId);
            } else {
                this.toggleWidget(this.currentView, widgetId);
            }
        }
    }
}).mount('#app');
