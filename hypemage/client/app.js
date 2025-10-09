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
            notifications: []
        };
    },
    
    mounted() {
        this.connectRobot('storm');
        this.connectRobot('necron');
        this.initDragAndDrop();
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
                motors: { 
                    speeds: { front_left: 0, front_right: 0, back_left: 0, back_right: 0, dribbler: 0 },
                    temps: { front_left: 0, front_right: 0, back_left: 0, back_right: 0, dribbler: 0 }
                },
                logs: [],
                visibleWidgets: new Set(['controls', 'camera', 'motors', 'logs', 'status'])
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
                this.showNotification(`${robot.name} connected successfully`, 'success');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleInterfaceMessage(robotName, data);
            };
            
            ws.onerror = (error) => {
                console.error(`[${robot.name}] Interface error:`, error);
                this.showNotification(`${robot.name} connection failed`, 'error');
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
                    // Handle both array and object formats
                    if (Array.isArray(payload.speeds)) {
                        MOTOR_NAMES.forEach((name, i) => {
                            robot.motors.speeds[name] = payload.speeds[i] || 0;
                            robot.motors.temps[name] = (payload.temps && payload.temps[i]) || 0;
                        });
                    } else {
                        robot.motors.speeds = payload.speeds || robot.motors.speeds;
                        robot.motors.temps = payload.temps || robot.motors.temps;
                    }
                } else if (subsystem === 'logs') {
                    // Add new log entries
                    if (payload.logs && Array.isArray(payload.logs)) {
                        robot.logs.push(...payload.logs);
                        // Keep only last 100 logs
                        if (robot.logs.length > 100) {
                            robot.logs = robot.logs.slice(-100);
                        }
                    }
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
                    
                    widgets.forEach(widget => {
                        const rect = widget.getBoundingClientRect();
                        const widgetCenterY = rect.top + rect.height / 2;
                        const distance = Math.abs(e.clientY - widgetCenterY);
                        
                        // If cursor is above this widget's center, consider inserting before it
                        if (e.clientY < widgetCenterY && distance < minDistance) {
                            minDistance = distance;
                            insertBefore = widget;
                        }
                    });
                    
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
            this.showNotification(`Attempting to reconnect to ${robot.name}...`, 'info');
            
            // Close existing connections
            if (robot.interfaceWs) {
                robot.interfaceWs.onclose = null; // Prevent auto-reconnect
                robot.interfaceWs.close();
            }
            if (robot.debugWs) {
                robot.debugWs.onclose = null;
                robot.debugWs.close();
            }
            
            // Reset state
            robot.connected = false;
            
            // Attempt new connection
            setTimeout(() => {
                this.connectRobot(robotName);
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
        }
    }
}).mount('#app');
