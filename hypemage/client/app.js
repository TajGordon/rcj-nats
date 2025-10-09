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
    { id: 'controls', name: 'Controls', icon: '🎮', resizable: false },
    { id: 'camera', name: 'Camera', icon: '📷', resizable: true },
    { id: 'calibration', name: 'Calibration', icon: '🎨', resizable: false },
    { id: 'motors', name: 'Motors', icon: '⚙️', resizable: false },
    { id: 'logs', name: 'Logs', icon: '📝', resizable: true },
    { id: 'status', name: 'Status', icon: 'ℹ️', resizable: false }
];

const MOTOR_NAMES = ['front_left', 'front_right', 'back_left', 'back_right', 'dribbler'];

createApp({
    data() {
        return {
            currentView: 'both',
            availableWidgets: AVAILABLE_WIDGETS,
            storm: this.createRobotState('storm'),
            necron: this.createRobotState('necron'),
            notifications: [],
            initialConnectionAttempted: false
        };
    },
    
    mounted() {
        // Initial connection - silent (no notifications)
        this.connectRobot('storm', true);
        this.connectRobot('necron', true);
        this.initialConnectionAttempted = true;
        this.initDragAndDrop();
    },
    
    methods: {
        createRobotState(name) {
            return {
                name: ROBOT_CONFIG[name].name,
                host: ROBOT_CONFIG[name].host,
                connected: false,
                connecting: false,
                interfaceWs: null,
                debugWs: null,
                status: 'stopped',
                pid: null,
                camera: { fps: 0, frame: null },
                motors: { 
                    speeds: { front_left: 0, front_right: 0, back_left: 0, back_right: 0, dribbler: 0 },
                    temps: { front_left: 0, front_right: 0, back_left: 0, back_right: 0, dribbler: 0 }
                },
                calibration: {
                    original: null,
                    ball_mask: null,
                    blue_mask: null,
                    yellow_mask: null,
                    ball: { lower: [10, 100, 100], upper: [20, 255, 255] },
                    blue_goal: { lower: [100, 150, 50], upper: [120, 255, 255] },
                    yellow_goal: { lower: [20, 100, 100], upper: [40, 255, 255] }
                },
                logs: [],
                visibleWidgets: new Set(['controls', 'camera', 'motors', 'logs', 'status'])
            };
        },
        
        connectRobot(robotName, silent = false) {
            this.connectInterface(robotName, silent);
            this.connectDebug(robotName, silent);
        },
        
        connectInterface(robotName, silent = false) {
            const robot = this[robotName];
            const config = ROBOT_CONFIG[robotName];
            
            // Prevent duplicate connections
            if (robot.connecting || (robot.interfaceWs && robot.interfaceWs.readyState === WebSocket.CONNECTING)) {
                return;
            }
            
            // Close existing connection if any
            if (robot.interfaceWs) {
                robot.interfaceWs.onclose = null;
                robot.interfaceWs.close();
            }
            
            const url = `ws://${config.host}:${config.interfacePort}/ws`;
            console.log(`[${robot.name}] Connecting to interface: ${url}`);
            
            robot.connecting = true;
            const ws = new WebSocket(url);
            
            ws.onopen = () => {
                console.log(`[${robot.name}] Interface connected`);
                robot.connected = true;
                robot.connecting = false;
                if (!silent) {
                    this.showNotification(`${robot.name} connected`, 'success');
                }
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleInterfaceMessage(robotName, data);
            };
            
            ws.onerror = (error) => {
                console.error(`[${robot.name}] Interface error:`, error);
                robot.connecting = false;
                if (!silent) {
                    this.showNotification(`${robot.name} connection failed`, 'error');
                }
            };
            
            ws.onclose = () => {
                console.log(`[${robot.name}] Interface disconnected`);
                robot.connected = false;
                robot.connecting = false;
                // NO AUTO-RECONNECT - user must manually reconnect via badge click
            };
            
            robot.interfaceWs = ws;
        },
        
        connectDebug(robotName, silent = false) {
            const robot = this[robotName];
            const config = ROBOT_CONFIG[robotName];
            
            // Close existing connection if any
            if (robot.debugWs) {
                robot.debugWs.onclose = null;
                robot.debugWs.close();
            }
            
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
                // NO AUTO-RECONNECT - debug connection follows robot state
            };
            
            robot.debugWs = ws;
        },
        
        handleInterfaceMessage(robotName, data) {
            const robot = this[robotName];
            
            if (data.type === 'status') {
                // Server status update
                robot.status = data.data.robot_running ? 'running' : 'stopped';
                robot.pid = data.data.pid;
            } else if (data.type === 'process_started') {
                // Process successfully started
                robot.status = 'running';
                robot.pid = data.pid;
                this.showNotification(`${robot.name}: ${data.script_name || 'Script'} started`, 'success');
            } else if (data.type === 'process_stopped') {
                // Process stopped
                robot.status = 'stopped';
                robot.pid = null;
                this.showNotification(`${robot.name}: Script stopped`, 'info');
            } else if (data.type === 'error') {
                // Error message from server
                this.showNotification(`${robot.name}: ${data.message}`, 'error');
            }
        },
        
        handleDebugMessage(robotName, data) {
            const robot = this[robotName];
            
            if (data.type !== 'update') return;
            
            const subsystem = data.subsystem;
            const payload = data.data;
            
            if (subsystem === 'camera' && payload.frame_jpeg) {
                robot.camera.fps = payload.fps || 0;
                robot.camera.frame = `data:image/jpeg;base64,${payload.frame_jpeg}`;
            } else if (subsystem === 'camera_debug' && payload) {
                // Camera debug frame with overlays (base64 encoded)
                robot.camera.frame = `data:image/jpeg;base64,${payload}`;
            } else if (subsystem === 'camera_calibrate' && payload) {
                // Camera calibration data - original frame + 3 masks
                if (payload.original) {
                    robot.calibration.original = `data:image/jpeg;base64,${payload.original}`;
                }
                if (payload.ball_mask) {
                    robot.calibration.ball_mask = `data:image/jpeg;base64,${payload.ball_mask}`;
                }
                if (payload.blue_mask) {
                    robot.calibration.blue_mask = `data:image/jpeg;base64,${payload.blue_mask}`;
                }
                if (payload.yellow_mask) {
                    robot.calibration.yellow_mask = `data:image/jpeg;base64,${payload.yellow_mask}`;
                }
                // Update HSV ranges if provided
                if (payload.hsv_ranges) {
                    if (payload.hsv_ranges.ball) {
                        robot.calibration.ball = payload.hsv_ranges.ball;
                    }
                    if (payload.hsv_ranges.blue_goal) {
                        robot.calibration.blue_goal = payload.hsv_ranges.blue_goal;
                    }
                    if (payload.hsv_ranges.yellow_goal) {
                        robot.calibration.yellow_goal = payload.hsv_ranges.yellow_goal;
                    }
                }
            } else if (subsystem === 'motors') {
                // Handle both array and object formats from debug manager
                if (Array.isArray(payload.speeds)) {
                    MOTOR_NAMES.forEach((name, i) => {
                        robot.motors.speeds[name] = payload.speeds[i] || 0;
                        robot.motors.temps[name] = (payload.temps && payload.temps[i]) || 0;
                    });
                } else if (payload.speeds) {
                    Object.assign(robot.motors.speeds, payload.speeds);
                    if (payload.temps) {
                        Object.assign(robot.motors.temps, payload.temps);
                    }
                }
            } else if (subsystem === 'logs' && payload.logs && Array.isArray(payload.logs)) {
                robot.logs.push(...payload.logs);
                // Keep only last 100 logs
                if (robot.logs.length > 100) {
                    robot.logs = robot.logs.slice(-100);
                }
            }
        },
        
        sendCommand(robotName, command, args = {}) {
            const robot = this[robotName];
            
            if (!robot.interfaceWs || robot.interfaceWs.readyState !== WebSocket.OPEN) {
                this.showNotification(`${robot.name} not connected`, 'error');
                return false;
            }
            
            robot.interfaceWs.send(JSON.stringify({ command, args }));
            return true;
        },
        
        startRobotDebug(robotName) {
            if (this.sendCommand(robotName, 'run_script', { script_id: 'scylla_debug' })) {
                this.showNotification(`${this[robotName].name}: Starting debug mode...`, 'info');
            }
        },
        
        stopRobot(robotName) {
            if (this.sendCommand(robotName, 'stop_script')) {
                this.showNotification(`${this[robotName].name}: Stopping...`, 'info');
            }
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
        },
        
        initDragAndDrop() {
            // Professional drag-and-drop system with animations and ghost preview
            this.$nextTick(() => {
                let dragState = {
                    element: null,
                    clone: null,
                    placeholder: null,
                    startX: 0,
                    startY: 0,
                    offsetX: 0,
                    offsetY: 0,
                    container: null,
                    isDragging: false
                };
                
                document.addEventListener('mousedown', (e) => {
                    const widget = e.target.closest('.widget');
                    if (!widget || !widget.closest('.single-view')) return;
                    
                    // Don't drag if clicking on interactive elements or resize handle
                    if (e.target.closest('button, input, img, .logs-container')) return;
                    
                    // Don't drag if clicking near any resize edge (40px from any edge)
                    if (widget.classList.contains('widget-resizable')) {
                        const rect = widget.getBoundingClientRect();
                        const isNearResizeEdge = (
                            (e.clientX > rect.right - 40) ||   // Right edge
                            (e.clientX < rect.left + 40) ||    // Left edge
                            (e.clientY > rect.bottom - 40) ||  // Bottom edge
                            (e.clientY < rect.top + 40)        // Top edge
                        );
                        if (isNearResizeEdge) return;
                    }
                    
                    // Initialize drag state
                    dragState.element = widget;
                    dragState.container = widget.closest('.widgets-container');
                    dragState.startX = e.clientX;
                    dragState.startY = e.clientY;
                    
                    const widgetRect = widget.getBoundingClientRect();
                    dragState.offsetX = e.clientX - widgetRect.left;
                    dragState.offsetY = e.clientY - widgetRect.top;
                    
                    // Add initial grab state (not yet dragging)
                    widget.classList.add('grab-active');
                    
                    const moveHandler = (e) => {
                        if (!dragState.element) return;
                        
                        const deltaX = Math.abs(e.clientX - dragState.startX);
                        const deltaY = Math.abs(e.clientY - dragState.startY);
                        
                        // Start dragging after 5px movement (prevents accidental drags)
                        if (!dragState.isDragging && (deltaX > 5 || deltaY > 5)) {
                            startDragging(dragState, e);
                        }
                        
                        if (dragState.isDragging) {
                            updateDragPosition(dragState, e);
                            updatePlaceholderPosition(dragState, e);
                        }
                    };
                    
                    const upHandler = () => {
                        if (dragState.isDragging) {
                            finishDragging(dragState);
                        } else if (dragState.element) {
                            dragState.element.classList.remove('grab-active');
                        }
                        
                        // Reset state
                        dragState = {
                            element: null,
                            clone: null,
                            placeholder: null,
                            startX: 0,
                            startY: 0,
                            offsetX: 0,
                            offsetY: 0,
                            container: null,
                            isDragging: false
                        };
                        
                        document.removeEventListener('mousemove', moveHandler);
                        document.removeEventListener('mouseup', upHandler);
                    };
                    
                    document.addEventListener('mousemove', moveHandler);
                    document.addEventListener('mouseup', upHandler);
                });
                
                function startDragging(state, e) {
                    state.isDragging = true;
                    const widget = state.element;
                    
                    // Create floating clone
                    const clone = widget.cloneNode(true);
                    clone.classList.add('widget-dragging-clone');
                    clone.classList.remove('grab-active');
                    const rect = widget.getBoundingClientRect();
                    clone.style.width = rect.width + 'px';
                    clone.style.height = rect.height + 'px';
                    clone.style.left = (e.clientX - state.offsetX) + 'px';
                    clone.style.top = (e.clientY - state.offsetY) + 'px';
                    document.body.appendChild(clone);
                    state.clone = clone;
                    
                    // Create placeholder (ghost outline showing drop position)
                    const placeholder = document.createElement('div');
                    placeholder.classList.add('widget-placeholder');
                    placeholder.style.height = rect.height + 'px';
                    widget.parentNode.insertBefore(placeholder, widget);
                    state.placeholder = placeholder;
                    
                    // Hide original widget (it's now represented by clone + placeholder)
                    widget.classList.add('widget-dragging-original');
                    widget.style.display = 'none';
                }
                
                function updateDragPosition(state, e) {
                    if (!state.clone) return;
                    state.clone.style.left = (e.clientX - state.offsetX) + 'px';
                    state.clone.style.top = (e.clientY - state.offsetY) + 'px';
                }
                
                function updatePlaceholderPosition(state, e) {
                    if (!state.placeholder || !state.container) return;
                    
                    // Find the best insertion point based on cursor position
                    const widgets = [...state.container.querySelectorAll('.widget:not(.widget-dragging-original)')];
                    let insertBefore = null;
                    let minDistance = Infinity;
                    let hoveredWidget = null;
                    
                    // Clear all previous highlights
                    widgets.forEach(w => w.classList.remove('drop-zone-highlight'));
                    
                    widgets.forEach(widget => {
                        const rect = widget.getBoundingClientRect();
                        const widgetCenterY = rect.top + rect.height / 2;
                        const distance = Math.abs(e.clientY - widgetCenterY);
                        
                        // Check if mouse is over this widget
                        if (e.clientX >= rect.left && e.clientX <= rect.right &&
                            e.clientY >= rect.top && e.clientY <= rect.bottom) {
                            hoveredWidget = widget;
                        }
                        
                        // If cursor is above this widget's center, consider inserting before it
                        if (e.clientY < widgetCenterY && distance < minDistance) {
                            minDistance = distance;
                            insertBefore = widget;
                        }
                    });
                    
                    // Highlight the widget we're hovering over
                    if (hoveredWidget) {
                        hoveredWidget.classList.add('drop-zone-highlight');
                    }
                    
                    // Move placeholder to the calculated position
                    if (insertBefore && insertBefore !== state.placeholder) {
                        state.container.insertBefore(state.placeholder, insertBefore);
                    } else if (!insertBefore && state.container.lastElementChild !== state.placeholder) {
                        // Insert at the end if cursor is below all widgets
                        state.container.appendChild(state.placeholder);
                    }
                }
                
                function finishDragging(state) {
                    if (!state.element || !state.placeholder) return;
                    
                    // Clear all highlights
                    if (state.container) {
                        const widgets = [...state.container.querySelectorAll('.widget')];
                        widgets.forEach(w => w.classList.remove('drop-zone-highlight'));
                    }
                    
                    // Remove clone with fade animation
                    if (state.clone) {
                        state.clone.classList.add('widget-dropping');
                        setTimeout(() => {
                            if (state.clone && state.clone.parentNode) {
                                state.clone.parentNode.removeChild(state.clone);
                            }
                        }, 200);
                    }
                    
                    // Move original element to placeholder position
                    const placeholder = state.placeholder;
                    placeholder.parentNode.insertBefore(state.element, placeholder);
                    
                    // Show original element again with pop-in animation
                    state.element.style.display = '';
                    state.element.classList.remove('widget-dragging-original', 'grab-active');
                    state.element.classList.add('widget-dropped');
                    
                    // Remove animations after they complete
                    setTimeout(() => {
                        if (state.element) {
                            state.element.classList.remove('widget-dropped');
                        }
                    }, 300);
                    
                    // Remove placeholder
                    if (placeholder.parentNode) {
                        placeholder.parentNode.removeChild(placeholder);
                    }
                }
            });
        },
        
        manualReconnect(robotName) {
            const robot = this[robotName];
            
            if (robot.connecting) {
                this.showNotification(`${robot.name} already connecting...`, 'info');
                return;
            }
            
            this.showNotification(`Reconnecting to ${robot.name}...`, 'info');
            
            // Close existing connections
            if (robot.interfaceWs) {
                robot.interfaceWs.onclose = null;
                robot.interfaceWs.close();
            }
            if (robot.debugWs) {
                robot.debugWs.onclose = null;
                robot.debugWs.close();
            }
            
            // Reset state
            robot.connected = false;
            
            // Attempt new connection (with notifications)
            setTimeout(() => {
                this.connectRobot(robotName, false);
            }, 100);
        },
        
        showNotification(message, type = 'info') {
            const id = Date.now();
            const notification = { id, message, type };
            this.notifications.push(notification);
            
            // Auto-remove after 4 seconds
            setTimeout(() => {
                const index = this.notifications.findIndex(n => n.id === id);
                if (index !== -1) {
                    this.notifications.splice(index, 1);
                }
            }, 4000);
        },
        
        dismissNotification(id) {
            const index = this.notifications.findIndex(n => n.id === id);
            if (index !== -1) {
                this.notifications.splice(index, 1);
            }
        },
        
        updateHSV(robotName, target) {
            const robot = this[robotName];
            
            if (!robot.debugWs || robot.debugWs.readyState !== WebSocket.OPEN) {
                console.warn(`[${robot.name}] Debug WebSocket not connected, cannot send HSV update`);
                return;
            }
            
            // Send HSV update to debug manager
            const message = {
                command: 'update_hsv',
                target: target,
                lower: robot.calibration[target].lower,
                upper: robot.calibration[target].upper
            };
            
            robot.debugWs.send(JSON.stringify(message));
            console.log(`[${robot.name}] Sent HSV update for ${target}:`, message);
        },
        
        saveCalibration(robotName) {
            const robot = this[robotName];
            
            if (!robot.debugWs || robot.debugWs.readyState !== WebSocket.OPEN) {
                this.showNotification(`${robot.name}: Not connected to debug server`, 'error');
                return;
            }
            
            // Send save command to debug manager
            const message = {
                command: 'save_calibration',
                hsv_ranges: {
                    ball: robot.calibration.ball,
                    blue_goal: robot.calibration.blue_goal,
                    yellow_goal: robot.calibration.yellow_goal
                }
            };
            
            robot.debugWs.send(JSON.stringify(message));
            this.showNotification(`${robot.name}: Calibration saved`, 'success');
            console.log(`[${robot.name}] Saved calibration:`, message);
        }
    }
}).mount('#app');
