const canvas = document.getElementById('fieldCanvas');
const ctx = canvas.getContext('2d');

// Field dimensions in mm (from config.py)
const FIELD_WIDTH = 2430;
const FIELD_HEIGHT = 1820;
const GOAL_WIDTH = 450;
const GOAL_DEPTH = 74;
const GOAL_OFFSET = 915;

// Canvas scaling
const SCALE = Math.min(canvas.width / FIELD_WIDTH, canvas.height / FIELD_HEIGHT);
const OFFSET_X = (canvas.width - FIELD_WIDTH * SCALE) / 2;
const OFFSET_Y = (canvas.height - FIELD_HEIGHT * SCALE) / 2;

// Convert field coordinates to canvas coordinates
function fieldToCanvas(x, y) {
    return [
        OFFSET_X + (x + FIELD_WIDTH/2) * SCALE,
        OFFSET_Y + (-y + FIELD_HEIGHT/2) * SCALE  // Flip Y axis
    ];
}

function drawField() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Field background
    ctx.fillStyle = "#2d8a2f";  // Soccer field green
    const [fieldX, fieldY] = fieldToCanvas(-FIELD_WIDTH/2, FIELD_HEIGHT/2);
    ctx.fillRect(fieldX, fieldY, FIELD_WIDTH * SCALE, FIELD_HEIGHT * SCALE);
    
    // Field border
    ctx.strokeStyle = "white";
    ctx.lineWidth = 3;
    ctx.strokeRect(fieldX, fieldY, FIELD_WIDTH * SCALE, FIELD_HEIGHT * SCALE);
    
    // Center line
    ctx.beginPath();
    const [centerX1, centerY1] = fieldToCanvas(0, FIELD_HEIGHT/2);
    const [centerX2, centerY2] = fieldToCanvas(0, -FIELD_HEIGHT/2);
    ctx.moveTo(centerX1, centerY1);
    ctx.lineTo(centerX2, centerY2);
    ctx.stroke();
    
    // Center circle
    ctx.beginPath();
    const [centerX, centerY] = fieldToCanvas(0, 0);
    ctx.arc(centerX, centerY, 200 * SCALE, 0, 2 * Math.PI);
    ctx.stroke();
    
    // Goals
    drawGoal(1);   // Right goal (blue)
    drawGoal(-1);  // Left goal (yellow)
}

function drawGoal(side) {
    const goalX = side * (FIELD_WIDTH/2 - GOAL_DEPTH);
    const goalBackX = side * FIELD_WIDTH/2;
    
    // Goal posts and crossbar
    ctx.strokeStyle = "white";
    ctx.lineWidth = 4;
    
    // Left post
    const [post1X, post1Y] = fieldToCanvas(goalBackX, GOAL_WIDTH/2);
    const [post1X2, post1Y2] = fieldToCanvas(goalX, GOAL_WIDTH/2);
    ctx.beginPath();
    ctx.moveTo(post1X, post1Y);
    ctx.lineTo(post1X2, post1Y2);
    ctx.stroke();
    
    // Right post  
    const [post2X, post2Y] = fieldToCanvas(goalBackX, -GOAL_WIDTH/2);
    const [post2X2, post2Y2] = fieldToCanvas(goalX, -GOAL_WIDTH/2);
    ctx.beginPath();
    ctx.moveTo(post2X, post2Y);
    ctx.lineTo(post2X2, post2Y2);
    ctx.stroke();
    
    // Back wall
    ctx.beginPath();
    ctx.moveTo(post1X, post1Y);
    ctx.lineTo(post2X, post2Y);
    ctx.stroke();
    
    // Goal area coloring
    ctx.fillStyle = side > 0 ? "#4a90e2" : "#f5d442";  // Blue for right, yellow for left
    ctx.globalAlpha = 0.3;
    
    const [goalAreaX1, goalAreaY1] = fieldToCanvas(Math.min(goalX, goalBackX), GOAL_WIDTH/2);
    const [goalAreaX2, goalAreaY2] = fieldToCanvas(Math.max(goalX, goalBackX), -GOAL_WIDTH/2);
    ctx.fillRect(goalAreaX1, goalAreaY1, (goalAreaX2 - goalAreaX1), (goalAreaY2 - goalAreaY1));
    
    ctx.globalAlpha = 1.0;
}

function drawRobot(pos, angle) {
    const [canvasX, canvasY] = fieldToCanvas(pos[0], pos[1]);
    
    // Robot body (circle)
    ctx.fillStyle = "#333333";
    ctx.beginPath();
    ctx.arc(canvasX, canvasY, 50 * SCALE, 0, 2 * Math.PI);
    ctx.fill();
    
    // Robot direction indicator
    ctx.strokeStyle = "#ff4444";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(canvasX, canvasY);
    const dirX = canvasX + Math.cos(angle) * 60 * SCALE;
    const dirY = canvasY - Math.sin(angle) * 60 * SCALE;  // Flip Y for canvas
    ctx.lineTo(dirX, dirY);
    ctx.stroke();
    
    // Robot outline
    ctx.strokeStyle = "#666666";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(canvasX, canvasY, 50 * SCALE, 0, 2 * Math.PI);
    ctx.stroke();
}

function updateInfo(data) {
    const pos = data.robot.pos;
    const angle = data.robot.angle;
    const error = data.robot.error;
    const timestamp = data.robot.timestamp;
    
    document.getElementById('posX').textContent = `${pos[0].toFixed(1)} mm`;
    document.getElementById('posY').textContent = `${pos[1].toFixed(1)} mm`;
    document.getElementById('angle').textContent = `${(angle * 180 / Math.PI).toFixed(1)}°`;
    document.getElementById('error').textContent = error.toFixed(2);
    
    const now = new Date();
    document.getElementById('timestamp').textContent = now.toLocaleTimeString();
}

// WebSocket connection
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/data`;
const ws = new WebSocket(wsUrl);

const statusElement = document.getElementById('connectionStatus');

ws.onopen = () => {
    console.log('WebSocket connected');
    statusElement.textContent = 'Connected';
    statusElement.className = 'connection-status connected';
};

ws.onclose = () => {
    console.log('WebSocket disconnected');
    statusElement.textContent = 'Disconnected';
    statusElement.className = 'connection-status disconnected';
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    statusElement.textContent = 'Error';
    statusElement.className = 'connection-status disconnected';
};

ws.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        console.log('Received data:', data);
        
        // Update info panel
        updateInfo(data);
        
        // Redraw field with robot
        drawField();
        drawRobot(data.robot.pos, data.robot.angle);
        
    } catch (error) {
        console.error('Error parsing message:', error);
    }
};

// Initial field draw
drawField();