/**
 * Widget Components
 * 
 * Modular, reusable widgets for displaying robot data.
 * Easy to add new widgets - just create a new component!
 */

const { defineComponent } = Vue;

// ========== Robot Widgets Container ==========

const RobotWidgets = defineComponent({
    name: 'RobotWidgets',
    props: {
        robot: Object,
        visibleWidgets: Set,
        expanded: {
            type: Boolean,
            default: false
        }
    },
    template: `
        <div :class="['widgets-container', {expanded}]">
            <!-- Controls Widget -->
            <control-widget 
                v-if="visibleWidgets.has('controls')"
                :robot="robot"
                :expanded="expanded">
            </control-widget>
            
            <!-- Camera Widget -->
            <camera-widget 
                v-if="visibleWidgets.has('camera')"
                :camera="robot.camera"
                :expanded="expanded">
            </camera-widget>
            
            <!-- Motors Widget -->
            <motors-widget 
                v-if="visibleWidgets.has('motors')"
                :motors="robot.motors"
                :expanded="expanded">
            </motors-widget>
            
            <!-- Localization Widget -->
            <localization-widget 
                v-if="visibleWidgets.has('localization')"
                :localization="robot.localization"
                :expanded="expanded">
            </localization-widget>
            
            <!-- ToF Sensors Widget -->
            <tof-widget 
                v-if="visibleWidgets.has('tof')"
                :tof="robot.tof"
                :expanded="expanded">
            </tof-widget>
            
            <!-- Logs Widget -->
            <logs-widget 
                v-if="visibleWidgets.has('logs')"
                :logs="robot.logs"
                :expanded="expanded">
            </logs-widget>
            
            <!-- Status Widget -->
            <status-widget 
                v-if="visibleWidgets.has('status')"
                :robot="robot"
                :expanded="expanded">
            </status-widget>
        </div>
    `
});

// ========== Control Widget ==========

const ControlWidget = defineComponent({
    name: 'ControlWidget',
    props: ['robot', 'expanded'],
    template: `
        <div class="widget control-widget">
            <h3>🎮 Control</h3>
            <div class="button-group">
                <button 
                    @click="$emit('start-debug')"
                    :disabled="robot.status === 'running'"
                    class="btn btn-primary">
                    ▶️ Debug
                </button>
                <button 
                    @click="$emit('start-production')"
                    :disabled="robot.status === 'running'"
                    class="btn btn-secondary">
                    ▶️ Production
                </button>
                <button 
                    @click="$emit('stop')"
                    :disabled="robot.status !== 'running'"
                    class="btn btn-danger">
                    ⏹️ Stop
                </button>
            </div>
            <div v-if="expanded" class="script-buttons">
                <button @click="$emit('run-script', 'color_calibration')" class="btn btn-sm">
                    🎨 Color Cal
                </button>
                <button @click="$emit('run-script', 'motor_test')" class="btn btn-sm">
                    ⚙️ Motor Test
                </button>
            </div>
        </div>
    `
});

// ========== Camera Widget ==========

const CameraWidget = defineComponent({
    name: 'CameraWidget',
    props: ['camera', 'expanded'],
    template: `
        <div :class="['widget camera-widget', {expanded}]">
            <h3>📷 Camera <span class="fps">{{ camera.fps.toFixed(1) }} FPS</span></h3>
            <div v-if="camera.frame" class="camera-feed">
                <img :src="camera.frame" alt="Camera feed">
                <div class="camera-overlay">
                    <span v-if="camera.ballDetected" class="detection ball">
                        ⚽ Ball ({{ camera.ballPos[0] }}, {{ camera.ballPos[1] }})
                    </span>
                    <span v-if="camera.goalDetected.blue" class="detection goal-blue">
                        🥅 Blue Goal
                    </span>
                    <span v-if="camera.goalDetected.yellow" class="detection goal-yellow">
                        🥅 Yellow Goal
                    </span>
                </div>
            </div>
            <div v-else class="camera-placeholder">
                <p>No camera feed</p>
            </div>
        </div>
    `
});

// ========== Motors Widget ==========

const MotorsWidget = defineComponent({
    name: 'MotorsWidget',
    props: ['motors', 'expanded'],
    computed: {
        motorData() {
            return this.motors.speeds.map((speed, i) => ({
                id: i,
                speed: speed,
                temp: this.motors.temps[i] || 0,
                percentage: Math.abs(speed * 100),
                direction: speed > 0 ? 'forward' : speed < 0 ? 'backward' : 'stop'
            }));
        }
    },
    template: `
        <div :class="['widget motors-widget', {expanded}]">
            <h3>⚙️ Motors <span v-if="!motors.watchdog" class="warning">⚠️ Watchdog</span></h3>
            <div class="motor-grid">
                <div v-for="motor in motorData" :key="motor.id" class="motor-item">
                    <div class="motor-label">Motor {{ motor.id }}</div>
                    <div class="motor-bar">
                        <div 
                            :class="['motor-fill', motor.direction]"
                            :style="{width: motor.percentage + '%'}">
                        </div>
                    </div>
                    <div class="motor-info">
                        <span>{{ (motor.speed * 100).toFixed(0) }}%</span>
                        <span v-if="expanded" class="temp">{{ motor.temp }}°C</span>
                    </div>
                </div>
            </div>
        </div>
    `
});

// ========== Localization Widget ==========

const LocalizationWidget = defineComponent({
    name: 'LocalizationWidget',
    props: ['localization', 'expanded'],
    template: `
        <div :class="['widget localization-widget', {expanded}]">
            <h3>📍 Position</h3>
            <div class="position-data">
                <div class="pos-item">
                    <span class="label">X:</span>
                    <span class="value">{{ localization.x.toFixed(1) }} mm</span>
                </div>
                <div class="pos-item">
                    <span class="label">Y:</span>
                    <span class="value">{{ localization.y.toFixed(1) }} mm</span>
                </div>
                <div class="pos-item">
                    <span class="label">Heading:</span>
                    <span class="value">{{ (localization.heading * 180 / Math.PI).toFixed(1) }}°</span>
                </div>
                <div v-if="expanded" class="pos-item">
                    <span class="label">Confidence:</span>
                    <span class="value">{{ (localization.confidence * 100).toFixed(0) }}%</span>
                </div>
            </div>
        </div>
    `
});

// ========== ToF Sensors Widget ==========

const TofWidget = defineComponent({
    name: 'TofWidget',
    props: ['tof', 'expanded'],
    template: `
        <div :class="['widget tof-widget', {expanded}]">
            <h3>📡 ToF Sensors</h3>
            <div class="tof-visual">
                <svg viewBox="0 0 200 200" class="tof-radar">
                    <!-- Circle background -->
                    <circle cx="100" cy="100" r="80" fill="none" stroke="#333" stroke-width="1"/>
                    <circle cx="100" cy="100" r="60" fill="none" stroke="#333" stroke-width="1"/>
                    <circle cx="100" cy="100" r="40" fill="none" stroke="#333" stroke-width="1"/>
                    <circle cx="100" cy="100" r="20" fill="none" stroke="#333" stroke-width="1"/>
                    
                    <!-- Robot center -->
                    <circle cx="100" cy="100" r="5" fill="#00ff00"/>
                    
                    <!-- ToF readings -->
                    <g v-for="(reading, i) in tof.readings" :key="i">
                        <line 
                            x1="100" y1="100"
                            :x2="100 + Math.cos(reading.angle * Math.PI / 180) * Math.min(reading.distance / 10, 80)"
                            :y2="100 + Math.sin(reading.angle * Math.PI / 180) * Math.min(reading.distance / 10, 80)"
                            :stroke="reading.distance < 200 ? '#ff0000' : '#00ff00'"
                            stroke-width="2"/>
                        <circle 
                            :cx="100 + Math.cos(reading.angle * Math.PI / 180) * Math.min(reading.distance / 10, 80)"
                            :cy="100 + Math.sin(reading.angle * Math.PI / 180) * Math.min(reading.distance / 10, 80)"
                            r="3"
                            :fill="reading.distance < 200 ? '#ff0000' : '#00ff00'"/>
                    </g>
                </svg>
            </div>
            <div v-if="expanded" class="tof-list">
                <div v-for="(reading, i) in tof.readings" :key="i" class="tof-reading">
                    <span>{{ reading.angle }}°:</span>
                    <span>{{ reading.distance }} mm</span>
                </div>
            </div>
        </div>
    `
});

// ========== Logs Widget ==========

const LogsWidget = defineComponent({
    name: 'LogsWidget',
    props: ['logs', 'expanded'],
    template: `
        <div :class="['widget logs-widget', {expanded}]">
            <h3>📝 Logs</h3>
            <div class="logs-container">
                <div v-if="logs.length === 0" class="no-logs">
                    No logs yet
                </div>
                <div v-else class="log-lines">
                    <div v-for="(log, i) in logs.slice(-20)" :key="i" :class="['log-line', log.level]">
                        <span class="log-time">{{ log.time }}</span>
                        <span class="log-message">{{ log.message }}</span>
                    </div>
                </div>
            </div>
        </div>
    `
});

// ========== Status Widget ==========

const StatusWidget = defineComponent({
    name: 'StatusWidget',
    props: ['robot', 'expanded'],
    template: `
        <div class="widget status-widget">
            <h3>ℹ️ Status</h3>
            <div class="status-grid">
                <div class="status-item">
                    <span class="label">Status:</span>
                    <span :class="['value', robot.status]">{{ robot.status }}</span>
                </div>
                <div class="status-item">
                    <span class="label">PID:</span>
                    <span class="value">{{ robot.pid || '-' }}</span>
                </div>
                <div class="status-item">
                    <span class="label">Debug:</span>
                    <span class="value">{{ robot.debugEnabled ? 'Yes' : 'No' }}</span>
                </div>
                <div v-if="expanded" class="status-item">
                    <span class="label">Host:</span>
                    <span class="value">{{ robot.host }}</span>
                </div>
            </div>
        </div>
    `
});

// ========== Register Components ==========

const app = Vue.createApp({});

app.component('robot-widgets', RobotWidgets);
app.component('control-widget', ControlWidget);
app.component('camera-widget', CameraWidget);
app.component('motors-widget', MotorsWidget);
app.component('localization-widget', LocalizationWidget);
app.component('tof-widget', TofWidget);
app.component('logs-widget', LogsWidget);
app.component('status-widget', StatusWidget);
