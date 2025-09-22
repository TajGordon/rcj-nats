const canvas = document.getElementById('fieldCanvas')
const ctx = canvas.getContext('2d')

/* field geometry */
const centre_x = 2430/2;
const centre_y = 1820/2;
// outer walls - just a single coordinate
const left_wall = -2430/2;
const right_wall = 2430/2;
const top_wall = 1820/2;
const bottom_wall = -1820/2;
// goal dimensions - multiply by T[-1, 1] to get opposite goal
const goal_top_wall_y = 450/2;
const goal_bottom_wall_y = -450/2;
const goal_walls_x = 915; 
const goal_back_wall_x = 915 + 74;
const goal_internal_width = 450;
// not actually important, gets ignored anyways <-- hopefully ignoring this isn't a big deal
const wall_width = 3;
const wall_gaps = 300;
const white_line_thickness = 50;

function drawField() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "green";
    ctx.fillRect(centre_x + left_wall, centre_y + bottom_wall, centre_x + right_wall, centre_y + top_wall);
    // white lines
    ctx.fillStyle = "azure";
    ctx.fillRect(centre_x + (right_wall-wall_gaps), centre_y + (bottom_wall + wall_gaps), white_line_thickness, centre_y + (top_wall - 2 * wall_gaps));
    ctx.fillRect(centre_x + (left_wall+wall_gaps), centre_y + (bottom_wall + wall_gaps), -white_line_thickness, centre_y + (top_wall - 2 * wall_gaps));
    ctx.fillRect(centre_x + (left_wall + wall_gaps) - white_line_thickness, centre_y + (bottom_wall + wall_gaps), centre_x + (right_wall - 2*wall_gaps + 2 * white_line_thickness), -white_line_thickness);
    ctx.fillRect(centre_x + (left_wall + wall_gaps) - white_line_thickness, centre_y + (top_wall - wall_gaps), centre_x + (right_wall - 2*wall_gaps + 2*white_line_thickness), white_line_thickness);
    // goals 
    {
        ctx.fillStyle = "black";
        x_multiplier = 1;
        // to do equivalent work on both sides
        for (i = 0; i < 2; i++)
        {
            ctx.fillRect(centre_x + (goal_walls_x * x_multiplier), centre_y + goal_top_wall_y, (right_wall - goal_walls_x) * x_multiplier, wall_width);
            ctx.fillRect(centre_x + (goal_walls_x * x_multiplier), centre_y + goal_bottom_wall_y, (right_wall - goal_walls_x) * x_multiplier, -wall_width);
            ctx.fillRect(centre_x + (goal_back_wall_x * x_multiplier), centre_y - goal_internal_width/2, wall_width * x_multiplier, goal_internal_width);
            x_multiplier = -1;        
        }
        x_multiplier = 1;
        ctx.fillStyle = "cyan";
        ctx.fillRect(centre_x + ((goal_walls_x +white_line_thickness) * x_multiplier), centre_y + goal_bottom_wall_y, (goal_back_wall_x - goal_walls_x - white_line_thickness) * x_multiplier, goal_internal_width);
        x_multiplier = -1;
        ctx.fillStyle = "gold";
        ctx.fillRect(centre_x + ((goal_walls_x + white_line_thickness) * x_multiplier), centre_y + goal_bottom_wall_y, (goal_back_wall_x - goal_walls_x - white_line_thickness) * x_multiplier, goal_internal_width);
    }
    // draw the centre
    ctx.fillStyle = "black";
    ctx.arc(centre_x, centre_y, 10, 0, 2 * Math.PI);
    ctx.fill();
}

function drawBot(pos, angle) {
    // bot body
    ctx.fillStyle = "black";
    ctx.beginPath();
    ctx.arc(centre_x + pos[0], centre_y + pos[1], 220, 0, 2 * Math.PI);
    ctx.fill();
    // little line
    const rad = 300;
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(centre_x + pos[0], centre_y + pos[1]);
    ctx.strokeStyle = 'crimson';
    ctx.lineTo(centre_x + pos[0] + rad * Math.cos(angle), centre_y + pos[1] + rad * Math.sin(angle));
    ctx.lineTo(centre_x + pos[0], centre_y + pos[1]);
    ctx.stroke();
}

drawField();


const ws = new WebSocket('ws://localhost:8001/ws/data');
// ws.onmessage = (event) => {
//     console.log(event);
// }
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('recieved data!');
    const hyperion_pos = data.hyperion.pos;
    const hyperion_angle = data.hyperion.angle;
    console.log('position: ', hyperion_pos, ' angle: ', hyperion_angle);
    
    drawField();
    drawBot(hyperion_pos, hyperion_angle);
}; 