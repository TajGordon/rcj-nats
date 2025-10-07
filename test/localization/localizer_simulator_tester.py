'''
This file is like fake_localizer, but it uses the real localizer.py and just gives it fake info
Simulates robot position, raycasts ToF sensors with ±2% error, and displays localization results
'''

import pygame as pg
import math
import random
import config

# Mock classes to avoid importing hardware-specific libraries
class MockToF:
    """Mock ToF class to avoid importing hardware libraries"""
    def __init__(self, addr, offset, angle, i2c=None):
        self.addr = addr
        self.offset = offset
        self.angle = angle
        self.i2c = i2c
        self.distance = 0.0
    
    def next_dist(self):
        return self.distance
    
    def cur_dist(self):
        return self.distance

class MockIMU:
    """Mock IMU class to avoid importing hardware libraries"""
    def __init__(self, i2c=None):
        self.i2c = i2c
        self.angle = 0.0
    
    def cur_angle(self):
        return self.angle

# Mock the localizer module to avoid hardware imports
class MockLocalizer:
    """Mock localizer that uses our fake sensors"""
    def __init__(self, i2c, tofs=None, imu=None):
        self.tofs = tofs if tofs is not None else []
        self.imu = imu if imu is not None else MockIMU(i2c)
        self.tof_angles = []
        self.tof_distances = {}
        self.best_guess = [0, 0]
        self.best_error = float('inf')
        
        # Initialize ToF sensors from config or use defaults
        if hasattr(config, 'tof_addrs') and config.tof_addrs and False:
            # Use config if available
            for addr in config.tof_addrs:
                mock_tof = MockToF(addr=addr, offset=config.tof_offsets[addr], 
                                 angle=config.tof_angles[addr], i2c=i2c)
                self.tofs.append(mock_tof)
                self.tof_angles.append(mock_tof.angle)
                self.tof_distances[mock_tof.angle] = 0
        else:
            # Use default ToF configuration for simulator
            default_tof_configs = [
                {'addr': 0x10, 'angle': 0, 'offset': (0, 0)},
                {'addr': 0x11, 'angle': 45, 'offset': (0, 0)},
                {'addr': 0x12, 'angle': 90, 'offset': (0, 0)},
                {'addr': 0x13, 'angle': 135, 'offset': (0, 0)},
                {'addr': 0x14, 'angle': 180, 'offset': (0, 0)},
                {'addr': 0x15, 'angle': -135, 'offset': (0, 0)},
                {'addr': 0x16, 'angle': -90, 'offset': (0, 0)},
                {'addr': 0x17, 'angle': -45, 'offset': (0, 0)},
            ]
            for tof_config in default_tof_configs:
                mock_tof = MockToF(addr=tof_config['addr'], offset=tof_config['offset'], 
                                 angle=tof_config['angle'], i2c=i2c)
                self.tofs.append(mock_tof)
                self.tof_angles.append(mock_tof.angle)
                self.tof_distances[mock_tof.angle] = 0
    
    def _update_distances(self):
        for tof in self.tofs:
            dist = tof.next_dist()
            self.tof_distances[tof.angle] = dist
    
    def _cast_ray(self, position, angle):
        """Raycast implementation from the real localizer"""
        minimum_distance = float('inf')
        dx = math.cos(angle)
        dy = math.sin(angle)
        for wall in config.walls:
            if wall['type'] == 'horizontal': 
                t = (wall['y'] - position[1]) / dy  if dy != 0 else float('inf') # Fixed: should be position[1] for y
                if t <= 0:
                    continue
                x = position[0] + t * dx
                if x < wall['x_min'] or x > wall['x_max']:
                    continue
                y = position[1] + t * dy
                dist_squared = (t * dx)**2 + (t * dy)**2  # Return distance squared like real localizer
                if dist_squared < minimum_distance:
                    minimum_distance = dist_squared
            else:  # vertical wall
                t = (wall['x'] - position[0]) / dx  if dx != 0 else float('inf') # Fixed: should be position[0] for x
                if t <= 0:
                    continue
                y = position[1] + t * dy
                if y < wall['y_min'] or y > wall['y_max']:
                    continue
                x = position[0] + t * dx
                dist_squared = (t * dx)**2 + (t * dy)**2  # Return distance squared like real localizer
                if dist_squared < minimum_distance:
                    minimum_distance = dist_squared
        return minimum_distance
    
    def _cast_rays(self, position, bot_angle):
        distances = {}
        for angle in self.tof_angles:
            dist = self._cast_ray(position, math.radians(bot_angle + angle))
            distances[angle] = dist
        return distances
    
    def _compute_error(self, position, bot_angle):
        error = 0
        raycast_distances = self._cast_rays(position, bot_angle)
        for angle in self.tof_angles:
            # ToF distance is in meters, raycast returns distance squared in mm²
            # Convert ToF distance to mm and square it to match raycast
            tof_dist_mm = self.tof_distances[angle] * 1000  # Convert meters to mm
            tof_dist_squared = tof_dist_mm ** 2  # Square it to match raycast units
            diff = abs(raycast_distances[angle] - tof_dist_squared)
            error += diff
        return error
    
    def localize(self):
        self._update_distances()
        angle = math.degrees(self.imu.cur_angle())  # Convert from radians to degrees
        self.best_error = self._compute_error(self.best_guess, angle)
        
        # Localization algorithm from the real localizer
        move_amount = 32
        decay_rate = 0.5
        cutoff = 0.05
        while move_amount > cutoff:
            converged = False
            while not converged:
                converged = True
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        guess_pos = [self.best_guess[0] + move_amount * dx, 
                                   self.best_guess[1] + move_amount * dy]
                        error = self._compute_error(guess_pos, angle)
                        if error < self.best_error:
                            converged = False
                            self.best_error = error
                            self.best_guess = guess_pos
            move_amount *= decay_rate
        
        return self.best_guess, self.best_error

# Debug flags
DEBUG_RAYCAST = False
DEBUG_LOCALIZATION = False

class Field:
    def __init__(self):
        # Field walls (outer boundaries)
        self.left_wall_x = -2430/2
        self.right_wall_x = 2430/2
        self.top_wall_y = 1820/2
        self.bottom_wall_y = -1820/2
        
        # Playing zone boundaries (250mm from walls)
        self.playing_zone_left = self.left_wall_x + 250
        self.playing_zone_right = self.right_wall_x - 250
        self.playing_zone_top = self.top_wall_y - 250
        self.playing_zone_bottom = self.bottom_wall_y + 250

class FakeToF:
    """Fake ToF sensor that simulates real sensor behavior with raycasting"""
    def __init__(self, addr, angle, offset):
        self.addr = addr
        self.angle = angle  # Angle relative to robot's forward direction
        self.offset = offset  # Position offset from robot center
        self.distance = 0.0
    
    def next_dist(self):
        """Simulate ToF sensor reading with ±2% error"""
        # Add random error of ±2%
        error_factor = random.uniform(0.98, 1.02)
        # Convert from mm to meters to match real ToF sensor units
        return (self.distance * error_factor) / 1000.0
    
    def raycast_distance(self, robot_pos, robot_angle, field):
        """Raycast from robot position in sensor direction to find wall/goal intersection"""
        # Calculate absolute angle of sensor relative to field
        absolute_angle = math.radians(robot_angle + self.angle)
        
        # Robot position
        robot_x, robot_y = robot_pos
        
        # Ray direction
        dx = math.cos(absolute_angle)
        dy = math.sin(absolute_angle)
        
        # Field boundaries
        left_wall = field.left_wall_x
        right_wall = field.right_wall_x
        top_wall = field.top_wall_y
        bottom_wall = field.bottom_wall_y
        
        # Goal positions (goal area starts 915mm from center, goal walls are 74mm deeper)
        goal_area_start = 915  # mm - where goal area starts
        goal_depth = 74  # mm - depth of goal
        left_goal_front = -goal_area_start  # Front of left goal area
        left_goal_back = left_goal_front - goal_depth  # Back wall of left goal
        right_goal_front = goal_area_start  # Front of right goal area  
        right_goal_back = right_goal_front + goal_depth  # Back wall of right goal
        
        min_distance = float('inf')
        
        # Check intersection with field walls
        # Left wall
        if dx != 0:
            t = (left_wall - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if bottom_wall <= y <= top_wall:
                    min_distance = min(min_distance, t)
        
        # Right wall
        if dx != 0:
            t = (right_wall - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if bottom_wall <= y <= top_wall:
                    min_distance = min(min_distance, t)
        
        # Top wall
        if dy != 0:
            t = (top_wall - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_wall <= x <= right_wall:
                    min_distance = min(min_distance, t)
        
        # Bottom wall
        if dy != 0:
            t = (bottom_wall - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_wall <= x <= right_wall:
                    min_distance = min(min_distance, t)
        
        # Check intersection with goals
        # Left goal (cyan) - goal area starts 915mm from center, goal walls are 74mm deeper
        # Check front wall of left goal (at goal area start)
        if dx != 0:
            t = (left_goal_front - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
        
        # Check back wall of left goal (74mm deeper)
        if dx != 0:
            t = (left_goal_back - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
        
        # Check left goal sidewalls (extend from goal to border wall)
        if dy != 0:
            # Top sidewall of left goal (extends from goal to top border wall)
            t = (225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_goal_back <= x <= left_goal_front:  # Between back and front of goal
                    min_distance = min(min_distance, t)
            
            # Bottom sidewall of left goal (extends from goal to bottom border wall)
            t = (-225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_goal_back <= x <= left_goal_front:  # Between back and front of goal
                    min_distance = min(min_distance, t)
        
        # Right goal (yellow) - goal area starts 915mm from center, goal walls are 74mm deeper
        # Check front wall of right goal (at goal area start)
        if dx != 0:
            t = (right_goal_front - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
        
        # Check back wall of right goal (74mm deeper)
        if dx != 0:
            t = (right_goal_back - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
        
        # Check right goal sidewalls (extend from goal to border wall)
        if dy != 0:
            # Top sidewall of right goal (extends from goal to top border wall)
            t = (225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if right_goal_front <= x <= right_goal_back:  # Between front and back of goal
                    min_distance = min(min_distance, t)
            
            # Bottom sidewall of right goal (extends from goal to bottom border wall)
            t = (-225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if right_goal_front <= x <= right_goal_back:  # Between front and back of goal
                    min_distance = min(min_distance, t)
        
        # Return distance in mm (field units are already in mm)
        final_distance = min_distance if min_distance != float('inf') else 5000.0
        return final_distance

class FakeIMU:
    """Fake IMU that simulates real IMU behavior"""
    def __init__(self):
        self.angle = 0.0
    
    def cur_angle(self):
        return self.angle
    
    def set_rotation(self, angle):
        """Set the rotation angle of the robot"""
        self.angle = angle

class FakeI2C:
    """Fake I2C interface for the real localizer"""
    def __init__(self):
        pass

class LocalizationSimulator:
    """Main simulator class that uses the mock localizer with fake sensors"""
    def __init__(self, field):
        self.field = field
        self.real_pos = (0.0, 0.0)  # Real robot position
        self.real_angle = 0.0  # Real robot angle
        
        # Create fake I2C interface
        fake_i2c = FakeI2C()
        
        # Create mock localizer instance (avoids hardware imports)
        self.localizer = MockLocalizer(fake_i2c)
        
        # Replace the mock ToF sensors with our fake ones that do raycasting
        self.fake_tofs = []
        for i, tof in enumerate(self.localizer.tofs):
            # Create fake ToF with same parameters as mock one
            fake_tof = FakeToF(addr=tof.addr, angle=tof.angle, offset=tof.offset)
            self.fake_tofs.append(fake_tof)
            # Replace the mock ToF in the localizer
            self.localizer.tofs[i] = fake_tof
        
        # Replace the mock IMU with our fake one
        self.fake_imu = FakeIMU()
        self.localizer.imu = self.fake_imu
        
        # Store estimated position from localizer
        self.estimated_pos = (0.0, 0.0)
        self.estimated_error = float('inf')
    
    def update_sensors(self):
        """Update all fake sensors with current real position and angle"""
        # Update IMU
        self.fake_imu.set_rotation(self.real_angle)
        
        # Update ToF sensors with raycast distances
        for fake_tof in self.fake_tofs:
            distance = fake_tof.raycast_distance(self.real_pos, self.real_angle, self.field)
            fake_tof.distance = distance
    
    def localize(self):
        """Run localization using the real localizer"""
        # Update sensors first
        self.update_sensors()
        
        # Run the real localizer
        estimated_pos, estimated_error = self.localizer.localize()
        
        # Store results
        self.estimated_pos = tuple(estimated_pos)
        self.estimated_error = estimated_error
        
        return self.estimated_pos, self.estimated_error

class InputHandler:
    """Modular input handling for keyboard and mouse"""
    def __init__(self):
        self.keys_pressed = set()
        self.mouse_pos = (0, 0)
        self.mouse_clicked = False
        self.input_received = False
    
    def handle_events(self, events):
        """Process pygame events and update input state"""
        self.input_received = False
        
        for event in events:
            if event.type == pg.KEYDOWN:
                self.keys_pressed.add(event.key)
                self.input_received = True
            elif event.type == pg.KEYUP:
                self.keys_pressed.discard(event.key)
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_clicked = True
                    self.mouse_pos = event.pos
                    self.input_received = True
            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_clicked = False
        
        # Update mouse position continuously
        self.mouse_pos = pg.mouse.get_pos()
        
        # Check if any movement or rotation keys are currently pressed for continuous input
        movement_keys = {pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN, pg.K_a, pg.K_s, pg.K_d, pg.K_w, pg.K_e, pg.K_q}
        if any(key in self.keys_pressed for key in movement_keys):
            self.input_received = True
    
    def get_keyboard_input(self, real_pos, real_angle, move_speed=50, rotation_speed=5, field=None):
        """Handle keyboard input for position movement and rotation"""
        new_pos = list(real_pos)
        new_angle = real_angle
        
        # Movement controls
        if pg.K_LEFT in self.keys_pressed or pg.K_a in self.keys_pressed:
            new_pos[0] -= move_speed
        if pg.K_RIGHT in self.keys_pressed or pg.K_d in self.keys_pressed:
            new_pos[0] += move_speed
        if pg.K_UP in self.keys_pressed or pg.K_w in self.keys_pressed:
            new_pos[1] += move_speed
        if pg.K_DOWN in self.keys_pressed or pg.K_s in self.keys_pressed:
            new_pos[1] -= move_speed
        
        # Constrain position to field boundaries (accounting for robot diameter of 60mm)
        if field:
            robot_radius = 30  # mm - half of 60mm diameter
            new_pos[0] = max(field.left_wall_x + robot_radius, min(field.right_wall_x - robot_radius, new_pos[0]))
            new_pos[1] = max(field.bottom_wall_y + robot_radius, min(field.top_wall_y - robot_radius, new_pos[1]))
        
        # Rotation controls
        if pg.K_e in self.keys_pressed:
            new_angle += rotation_speed
        if pg.K_q in self.keys_pressed:
            new_angle -= rotation_speed
        
        # Constrain angle to -180 to 180 degrees
        while new_angle > 180:
            new_angle -= 360
        while new_angle < -180:
            new_angle += 360
            
        return tuple(new_pos), new_angle
    
    def get_mouse_input(self, field_renderer, field_bounds, field=None):
        """Handle mouse input for position setting"""
        if self.mouse_clicked:
            # Convert screen coordinates to field coordinates
            field_x, field_y = field_renderer.screen_to_field(self.mouse_pos, field_bounds)
            
            # Constrain position to field boundaries (accounting for robot diameter of 60mm)
            if field:
                robot_radius = 30  # mm - half of 60mm diameter
                field_x = max(field.left_wall_x + robot_radius, min(field.right_wall_x - robot_radius, field_x))
                field_y = max(field.bottom_wall_y + robot_radius, min(field.top_wall_y - robot_radius, field_y))
            
            return (field_x, field_y)
        return None

class FieldRenderer:
    """Modular field rendering system"""
    def __init__(self, field):
        self.field = field
        self.field_width = field.right_wall_x - field.left_wall_x
        self.field_height = field.top_wall_y - field.bottom_wall_y
        self.field_ratio = self.field_width / self.field_height
    
    def calculate_field_bounds(self, screen_width, screen_height, margin=20):
        """Calculate field rendering bounds within screen area"""
        available_width = screen_width - 2 * margin
        available_height = screen_height - 2 * margin
        
        # Calculate scale to fit field while maintaining aspect ratio
        scale_x = available_width / self.field_width
        scale_y = available_height / self.field_height
        scale = min(scale_x, scale_y)
        
        # Calculate field dimensions on screen
        field_screen_width = self.field_width * scale
        field_screen_height = self.field_height * scale
        
        # Center the field
        x_offset = (screen_width - field_screen_width) / 2
        y_offset = (screen_height - field_screen_height) / 2
        
        return {
            'x': x_offset,
            'y': y_offset,
            'width': field_screen_width,
            'height': field_screen_height,
            'scale': scale
        }
    
    def field_to_screen(self, field_x, field_y, field_bounds):
        """Convert field coordinates to screen coordinates"""
        screen_x = field_bounds['x'] + (field_x - self.field.left_wall_x) * field_bounds['scale']
        screen_y = field_bounds['y'] + (self.field.top_wall_y - field_y) * field_bounds['scale']
        return (int(screen_x), int(screen_y))
    
    def screen_to_field(self, screen_pos, field_bounds):
        """Convert screen coordinates to field coordinates"""
        field_x = self.field.left_wall_x + (screen_pos[0] - field_bounds['x']) / field_bounds['scale']
        field_y = self.field.top_wall_y - (screen_pos[1] - field_bounds['y']) / field_bounds['scale']
        return (field_x, field_y)
    
    def render_field(self, screen, field_bounds, border_color=(255, 255, 255)):
        """Render the field with proper layout including goals and border lines"""
        # Calculate border dimensions first
        border_offset = 250 * field_bounds['scale']  # 250mm from walls
        border_thickness = max(3, int(50 * field_bounds['scale']))  # 50mm thick lines, minimum 3 pixels
        
        # Draw the entire field green first
        pg.draw.rect(screen, (144, 238, 144), (  # Light green pastel for entire field
            field_bounds['x'], field_bounds['y'],
            field_bounds['width'], field_bounds['height']
        ))
        
        # Draw white border lines to mark the playing zone (250mm from walls)
        # Top border line
        pg.draw.rect(screen, (255, 255, 255), (
            field_bounds['x'] + border_offset,
            field_bounds['y'] + border_offset,
            field_bounds['width'] - 2 * border_offset,
            border_thickness
        ))
        
        # Bottom border line
        pg.draw.rect(screen, (255, 255, 255), (
            field_bounds['x'] + border_offset,
            field_bounds['y'] + field_bounds['height'] - border_offset - border_thickness,
            field_bounds['width'] - 2 * border_offset,
            border_thickness
        ))
        
        # Left border line
        pg.draw.rect(screen, (255, 255, 255), (
            field_bounds['x'] + border_offset,
            field_bounds['y'] + border_offset,
            border_thickness,
            field_bounds['height'] - 2 * border_offset
        ))
        
        # Right border line
        pg.draw.rect(screen, (255, 255, 255), (
            field_bounds['x'] + field_bounds['width'] - border_offset - border_thickness,
            field_bounds['y'] + border_offset,
            border_thickness,
            field_bounds['height'] - 2 * border_offset
        ))
        
        # Draw outer field border to make field boundaries visible
        pg.draw.rect(screen, (200, 200, 200), (
            field_bounds['x'], field_bounds['y'],
            field_bounds['width'], field_bounds['height']
        ), 2)
        
        # Calculate goal dimensions in field coordinates
        goal_width = 450  # mm
        goal_depth = 74   # mm
        goal_width_screen = goal_width * field_bounds['scale']
        goal_depth_screen = goal_depth * field_bounds['scale']
        
        # Calculate goal positions - goals start 915mm from center of field
        field_center_x = field_bounds['x'] + field_bounds['width'] / 2
        field_center_y = field_bounds['y'] + field_bounds['height'] / 2
        goal_distance_from_center = 915  # mm
        goal_distance_screen = goal_distance_from_center * field_bounds['scale']
        
        # Left goal (pastel cyan) - starts 915mm from center, extends 74mm deeper
        left_goal_x = field_center_x - goal_distance_screen - goal_depth_screen
        left_goal_rect = (left_goal_x, field_center_y - goal_width_screen/2, 
                         goal_depth_screen, goal_width_screen)
        pg.draw.rect(screen, (175, 238, 238), left_goal_rect)  # Light cyan pastel
        pg.draw.rect(screen, (100, 100, 100), left_goal_rect, 2)   # Gray border
        
        # Right goal (pastel yellow) - starts 915mm from center, extends 74mm deeper
        right_goal_x = field_center_x + goal_distance_screen
        right_goal_rect = (right_goal_x, field_center_y - goal_width_screen/2,
                         goal_depth_screen, goal_width_screen)
        pg.draw.rect(screen, (255, 255, 224), right_goal_rect)  # Light yellow pastel
        pg.draw.rect(screen, (100, 100, 100), right_goal_rect, 2)   # Gray border
        
        # Draw center line (25mm thick gray line)
        center_x = field_bounds['x'] + field_bounds['width'] / 2
        center_thickness = max(2, int(25 * field_bounds['scale']))
        pg.draw.rect(screen, (150, 150, 150), (
            center_x - center_thickness/2,
            field_bounds['y'] + border_offset,
            center_thickness,
            field_bounds['height'] - 2 * border_offset
        ))
        
        # Draw center circle (light gray)
        center_y = field_bounds['y'] + field_bounds['height'] / 2
        circle_radius = min(field_bounds['width'], field_bounds['height']) * 0.15
        pg.draw.circle(screen, (150, 150, 150), (int(center_x), int(center_y)), int(circle_radius), 3)
    
    def render_position(self, screen, position, angle, field_bounds, color=(0, 0, 0), radius=30, show_tof_rays=False, simulator=None, is_real=True):
        """Render a position on the field with direction indicator and optional ToF rays"""
        if position:
            screen_pos = self.field_to_screen(position[0], position[1], field_bounds)
            
            # Draw circle for the robot
            pg.draw.circle(screen, color, screen_pos, radius)
            
            # Draw direction indicator line
            direction_length = radius + 8
            end_x = screen_pos[0] + direction_length * math.cos(math.radians(angle))
            end_y = screen_pos[1] - direction_length * math.sin(math.radians(angle))  # Negative because screen Y is inverted
            
            # Draw the direction line
            pg.draw.line(screen, color, screen_pos, (end_x, end_y), 2)
            
            # Draw ToF sensor rays if requested and simulator data is available
            if show_tof_rays and simulator and hasattr(simulator, 'fake_tofs'):
                for i, fake_tof in enumerate(simulator.fake_tofs):
                    # Calculate absolute angle using robot angle
                    absolute_angle = angle + fake_tof.angle
                    
                    # Calculate ray end point
                    if fake_tof.distance < 5000:  # Valid distance (not the max distance)
                        ray_length = fake_tof.distance * field_bounds['scale']
                        ray_end_x = screen_pos[0] + ray_length * math.cos(math.radians(absolute_angle))
                        ray_end_y = screen_pos[1] - ray_length * math.sin(math.radians(absolute_angle))
                        
                        # Choose ray colors based on position type
                        if is_real:
                            ray_color = (150, 150, 150)  # Gray for real position rays
                            dot_color = (100, 100, 100)  # Dark gray for intersection dots
                        else:
                            ray_color = (100, 150, 255)  # Blue for estimated position rays
                            dot_color = (50, 100, 255)   # Darker blue for intersection dots
                        
                        # Draw ray from robot position to intersection point
                        pg.draw.line(screen, ray_color, screen_pos, (ray_end_x, ray_end_y), 1)
                        
                        # Draw small dot at intersection point
                        pg.draw.circle(screen, dot_color, (int(ray_end_x), int(ray_end_y)), 2)
            
            # Draw position and angle label with white outline
            font = pg.font.Font(None, 24)
            text_str = f"({position[0]:.0f}, {position[1]:.0f}) {angle:.0f}°"
            
            # Render text with white outline for visibility
            outline_text = font.render(text_str, True, (255, 255, 255))  # White outline
            main_text = font.render(text_str, True, color)  # Main color
            
            # Draw outline (offset by 1 pixel in each direction)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:  # Don't draw outline at center
                        screen.blit(outline_text, (screen_pos[0] + 12 + dx, screen_pos[1] - 12 + dy))
            
            # Draw main text on top
            screen.blit(main_text, (screen_pos[0] + 12, screen_pos[1] - 12))

# Main simulation code
if __name__ == "__main__":
    # Initialize field and simulator
    field = Field()
    simulator = LocalizationSimulator(field)
    
    # Initialize pygame
    pg.init()
    screen = pg.display.set_mode((1200, 800), pg.RESIZABLE)
    pg.display.set_caption("Localization Simulator - Real Localizer with Fake Sensors")
    clock = pg.time.Clock()
    
    # Initialize systems
    input_handler = InputHandler()
    field_renderer = FieldRenderer(field)
    
    # Calculate field bounds
    screen_width, screen_height = screen.get_size()
    field_bounds = field_renderer.calculate_field_bounds(screen_width - 300, screen_height - 100)
    
    running = True
    while running:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)
                screen_width, screen_height = screen.get_size()
                field_bounds = field_renderer.calculate_field_bounds(screen_width - 300, screen_height - 100)
        
        # Handle input
        input_handler.handle_events(events)
        
        # Update positions only when input is received
        if input_handler.input_received:
            # Handle keyboard input for real position and rotation
            new_real_pos, new_real_angle = input_handler.get_keyboard_input(
                simulator.real_pos, simulator.real_angle, field=field)
            if new_real_pos != simulator.real_pos or new_real_angle != simulator.real_angle:
                simulator.real_pos = new_real_pos
                simulator.real_angle = new_real_angle
            
            # Handle mouse input
            mouse_pos = input_handler.get_mouse_input(field_renderer, field_bounds, field=field)
            if mouse_pos:
                simulator.real_pos = mouse_pos
        
        # Run localization using the real localizer
        estimated_pos, estimated_error = simulator.localize()
        
        # Clear screen
        screen.fill((30, 30, 30))
        
        # Render field
        field_renderer.render_field(screen, field_bounds)
        
        # Render real position (black) with ToF rays
        field_renderer.render_position(screen, simulator.real_pos, simulator.real_angle, 
                                     field_bounds, (0, 0, 0), 30, show_tof_rays=True, 
                                     simulator=simulator, is_real=True)
        
        # Render estimated position (red) with ToF rays
        field_renderer.render_position(screen, estimated_pos, simulator.real_angle, 
                                     field_bounds, (255, 0, 0), 25, show_tof_rays=True, 
                                     simulator=simulator, is_real=False)
        
        # Draw error line between real and estimated positions
        real_screen = field_renderer.field_to_screen(simulator.real_pos[0], simulator.real_pos[1], field_bounds)
        est_screen = field_renderer.field_to_screen(estimated_pos[0], estimated_pos[1], field_bounds)
        pg.draw.line(screen, (255, 255, 0), real_screen, est_screen, 3)
        
        # Draw error distance text
        error_distance = math.sqrt((simulator.real_pos[0] - estimated_pos[0])**2 + 
                                 (simulator.real_pos[1] - estimated_pos[1])**2)
        font = pg.font.Font(None, 24)
        error_text = f"Position Error: {error_distance:.1f}mm"
        text_surface = font.render(error_text, True, (255, 255, 0))
        screen.blit(text_surface, (10, 10))
        
        # Draw localization error
        loc_error_text = f"Localization Error: {estimated_error:.1f}"
        loc_error_surface = font.render(loc_error_text, True, (255, 255, 0))
        screen.blit(loc_error_surface, (10, 35))
        
        # Draw sensor data panel
        sensor_box_x = screen_width - 300
        sensor_box_y = 50
        
        # Draw background box
        pg.draw.rect(screen, (50, 50, 50), (sensor_box_x, sensor_box_y, 290, 300))
        pg.draw.rect(screen, (100, 100, 100), (sensor_box_x, sensor_box_y, 290, 300), 2)
        
        # Draw title
        title_font = pg.font.Font(None, 20)
        title_text = title_font.render("ToF Sensor Data (±2% error):", True, (255, 255, 255))
        screen.blit(title_text, (sensor_box_x + 10, sensor_box_y + 10))
        
        # Draw sensor data
        small_font = pg.font.Font(None, 16)
        for i, fake_tof in enumerate(simulator.fake_tofs):
            row = i // 2
            col = i % 2
            x_offset = col * 140
            y_offset = row * 20
            
            sensor_text = f"{fake_tof.angle:3.0f}°: {fake_tof.distance:5.0f}mm"
            text = small_font.render(sensor_text, True, (200, 200, 200))
            screen.blit(text, (sensor_box_x + 10 + x_offset, sensor_box_y + 35 + y_offset))
        
        # Draw instructions
        instructions = [
            "Controls:",
            "WASD/Arrow Keys: Move real position",
            "E/Q Keys: Rotate real position", 
            "Mouse Click: Set position",
            "Black: Real position",
            "Red: Estimated position",
            "Yellow line: Position error"
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (sensor_box_x + 10, sensor_box_y + 200 + i * 15))
        
        pg.display.flip()
        clock.tick(60)
    
    pg.quit()
