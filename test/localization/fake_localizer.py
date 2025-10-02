




# Debug flags - set to True to enable debug output
DEBUG_RAYCAST = False
DEBUG_LOCALIZATION = False

# Global test angles for localization
import random
import math
# random.seed(42)  # For reproducible results
TEST_ANGLES = []
# Add some common angles first
TEST_ANGLES.extend([0, 45, 90, 135, 180, -45, -90, -135])
# Add random angles
for i in range(8):  # 8 more random angles
    angle = random.uniform(-180, 180)
    TEST_ANGLES.append(angle)

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
    def __init__(self, addr, angle, offset):
        self.addr = addr
        self.angle = angle  # Angle relative to robot's forward direction
        self.offset = offset  # Position offset from robot center
        self.distance = 0.0
    
    def _set_distance(self, distance):
        self.distance = distance
    
    def cur_dist(self):
        return self.distance
    
    def raycast_distance(self, robot_pos, robot_angle, field):
        """Raycast from robot position in sensor direction to find wall/goal intersection"""
        import math
        
        # Calculate absolute angle of sensor relative to field
        real_absolute_angle = robot_angle + self.angle
        absolute_angle = real_absolute_angle + (random.uniform(-1, 1) * 0.01 * real_absolute_angle)
        
        # Robot position
        robot_x, robot_y = robot_pos
        
        # Ray direction
        dx = math.cos(math.radians(absolute_angle))
        dy = math.sin(math.radians(absolute_angle))
        
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
        
        # Debug output (only for first sensor and only during localization, not grid search)
        if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
            print(f"DEBUG: Sensor {self.angle}° raycast from ({robot_x:.1f}, {robot_y:.1f}) at angle {absolute_angle:.1f}°")
            print(f"DEBUG: Ray direction: dx={dx:.3f}, dy={dy:.3f}")
            print(f"DEBUG: Field bounds: left={left_wall}, right={right_wall}, top={top_wall}, bottom={bottom_wall}")
        
        # Check intersection with field walls
        # Left wall
        if dx != 0:
            t = (left_wall - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if bottom_wall <= y <= top_wall:
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit left wall at distance {t:.1f}, y={y:.1f}")
        
        # Right wall
        if dx != 0:
            t = (right_wall - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if bottom_wall <= y <= top_wall:
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit right wall at distance {t:.1f}, y={y:.1f}")
        
        # Top wall
        if dy != 0:
            t = (top_wall - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_wall <= x <= right_wall:
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit top wall at distance {t:.1f}, x={x:.1f}")
        
        # Bottom wall
        if dy != 0:
            t = (bottom_wall - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_wall <= x <= right_wall:
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit bottom wall at distance {t:.1f}, x={x:.1f}")
        
        # Check intersection with goals
        # Goals have sidewalls extending to the end wall and a back wall 74mm from the main wall
        
        # Left goal (cyan) - goal area starts 915mm from center, goal walls are 74mm deeper
        # Check front wall of left goal (at goal area start)
        if dx != 0:
            t = (left_goal_front - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit left goal front wall at distance {t:.1f}, y={y:.1f}")
        
        # Check back wall of left goal (74mm deeper)
        if dx != 0:
            t = (left_goal_back - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit left goal back wall at distance {t:.1f}, y={y:.1f}")
        
        # Check left goal sidewalls (extend from goal to border wall)
        if dy != 0:
            # Top sidewall of left goal (extends from goal to top border wall)
            t = (225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_goal_back <= x <= left_goal_front:  # Between back and front of goal
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit left goal top sidewall at distance {t:.1f}, x={x:.1f}")
            
            # Bottom sidewall of left goal (extends from goal to bottom border wall)
            t = (-225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if left_goal_back <= x <= left_goal_front:  # Between back and front of goal
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit left goal bottom sidewall at distance {t:.1f}, x={x:.1f}")
        
        # Right goal (yellow) - goal area starts 915mm from center, goal walls are 74mm deeper
        # Check front wall of right goal (at goal area start)
        if dx != 0:
            t = (right_goal_front - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit right goal front wall at distance {t:.1f}, y={y:.1f}")
        
        # Check back wall of right goal (74mm deeper)
        if dx != 0:
            t = (right_goal_back - robot_x) / dx
            if t > 0:
                y = robot_y + t * dy
                if -225 <= y <= 225:  # Goal width is 450mm, so ±225mm from center
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit right goal back wall at distance {t:.1f}, y={y:.1f}")
        
        # Check right goal sidewalls (extend from goal to border wall)
        if dy != 0:
            # Top sidewall of right goal (extends from goal to top border wall)
            t = (225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if right_goal_front <= x <= right_goal_back:  # Between front and back of goal
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit right goal top sidewall at distance {t:.1f}, x={x:.1f}")
            
            # Bottom sidewall of right goal (extends from goal to bottom border wall)
            t = (-225 - robot_y) / dy
            if t > 0:
                x = robot_x + t * dx
                if right_goal_front <= x <= right_goal_back:  # Between front and back of goal
                    min_distance = min(min_distance, t)
                    if DEBUG_RAYCAST and self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
                        print(f"DEBUG: Hit right goal bottom sidewall at distance {t:.1f}, x={x:.1f}")
        
        # Return distance in mm (field units are already in mm)
        final_distance = min_distance if min_distance != float('inf') else 5000.0
        if self.angle == 0 and hasattr(self, '_debug_raycast') and self._debug_raycast:
            print(f"DEBUG: Final distance for sensor {self.angle}°: {final_distance:.1f}mm")
        return final_distance

class FakeIMU:
    def __init__(self):
        self.angle = 0.0
    
    def _set_angle(self, angle):
        self.angle = angle
    
    def set_rotation(self, angle):
        """Set the rotation angle of the robot"""
        self.angle = angle
    
    def get_angle(self):
        return self.angle


class FakeLocalizer:
    def __init__(self, field):
        self.field = field
        self.tof_sensors = []
        self.distances = []
        self.angles = []
        self.best_guess = (935.0, 400.0)  # random guess for starting position
        self.best_error = float('inf')
        self.best_angle = 0.0  # Best angle found for the best guess
        
        # Initialize 8 ToF sensors with random angles around the robot
        import random
        random.seed(123)  # Different seed for sensor angles
        for i in range(8):
            angle = random.uniform(0, 360)  # Random angles between 0 and 360 degrees
            sensor = FakeToF(addr=i, angle=angle, offset=(0, 0))
            self.tof_sensors.append(sensor)
    
    def localize(self):
        """Collect ToF sensor data from real position and return estimated position"""
        if not hasattr(self, 'real_pos') or not hasattr(self, 'real_angle'):
            return (0.0, 0.0)
        
        # Get current REAL robot position and angle for raycasting
        real_robot_pos = self.real_pos
        real_robot_angle = self.real_angle
        
        if DEBUG_LOCALIZATION:
            print(f"DEBUG: Localizing from real position ({real_robot_pos[0]:.1f}, {real_robot_pos[1]:.1f}) at angle {real_robot_angle:.1f}°")
        
        # Collect distance and angle data from all sensors using REAL position
        self.distances = []
        self.angles = []
        
        for sensor in self.tof_sensors:
            # Enable debug for raycasting during initial localization
            sensor._debug_raycast = True
            # Get distance via raycasting from REAL position
            distance = sensor.raycast_distance(real_robot_pos, real_robot_angle, self.field)
            self.distances.append(distance)
            self.angles.append(sensor.angle)
            # Disable debug for grid search
            sensor._debug_raycast = False
        
        if DEBUG_LOCALIZATION:
            print(f"DEBUG: Collected distances: {[f'{d:.1f}' for d in self.distances]}")
            print(f"DEBUG: Sensor angles: {self.angles}")
        
        # Start the search from the previously found position (or center if first time)
        best_guess = self.best_guess
        
        # Allow robot to go anywhere within field walls for localization
        # Only prevent robot from going completely outside the field
        robot_radius = 30  # mm - just enough to prevent going outside field walls
        best_guess = (max(self.field.left_wall_x + robot_radius, 
                         min(self.field.right_wall_x - robot_radius, best_guess[0])),
                     max(self.field.bottom_wall_y + robot_radius, 
                         min(self.field.top_wall_y - robot_radius, best_guess[1])))
        best_error = float('inf')
        size_mul = 20
        while size_mul > 0.1:
            converged = False
            while not converged:
                converged = True
                for x_offset in range(-1, 2):
                    for y_offset in range(-1, 2):
                        guess_pos = (best_guess[0] + size_mul * x_offset * 10, best_guess[1] + size_mul * y_offset * 10)
                        
                        # Clamp position to field boundaries (accounting for robot radius)
                        # Allow robot to go into out-of-bounds areas for localization
                        robot_radius = 30  # mm - just enough to prevent going outside field walls
                        guess_x = max(self.field.left_wall_x + robot_radius, 
                                    min(self.field.right_wall_x - robot_radius, guess_pos[0]))
                        guess_y = max(self.field.bottom_wall_y + robot_radius, 
                                    min(self.field.top_wall_y - robot_radius, guess_pos[1]))
                        guess_pos = (guess_x, guess_y)
                        
                        error, angle = self.compute_error(guess_pos)
                        if error < best_error:
                            if DEBUG_LOCALIZATION:
                                print(f"DEBUG: Found better guess: ({guess_pos[0]:.1f}, {guess_pos[1]:.1f}) with error {error:.1f} using real angle {angle:.1f}°")
                            best_error = error
                            best_guess = guess_pos
                            self.best_angle = angle  # Store the real angle
                            converged = False
            size_mul *= 0.75
        # Update the best guess and error for next iteration
        self.best_guess = best_guess
        self.best_error = best_error
        
        return best_guess
    
    def compute_error(self, guess_pos):
        """Compute error between actual sensor readings and expected readings at guess position"""
        if not hasattr(self, 'distances') or not hasattr(self, 'angles'):
            return float('inf'), 0.0
        
        # Use the real IMU angle instead of testing multiple angles
        if not hasattr(self, 'real_angle'):
            return float('inf'), 0.0
        
        total_error = 0.0
        
        # For each sensor, compute what distance it would read at the guess position with the real robot angle
        for i, (actual_distance, sensor_angle) in enumerate(zip(self.distances, self.angles)):
            # Calculate what this sensor would read at the guess position with the real robot angle
            expected_distance = self.tof_sensors[i].raycast_distance(guess_pos, self.real_angle, self.field)
            
            # Add the absolute difference to total error
            error = abs(actual_distance - expected_distance)
            total_error += error
        
        # Debug: Show total error
        if DEBUG_LOCALIZATION and len(self.distances) > 0:
            print(f"DEBUG: Error for position ({guess_pos[0]:.1f}, {guess_pos[1]:.1f}): {total_error:.1f} using real angle {self.real_angle:.1f}°")
        
        return total_error, self.real_angle
    





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
        # Allow robot to go into out-of-bounds areas for localization
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
            # Allow robot to go into out-of-bounds areas for localization
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
        
        # Draw white border lines to mark the playing zone (250mm from walls) with anti-aliasing
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
        
        
        # Draw center line (25mm thick gray line) with anti-aliasing
        center_x = field_bounds['x'] + field_bounds['width'] / 2
        center_thickness = max(2, int(25 * field_bounds['scale']))
        pg.draw.rect(screen, (150, 150, 150), (
            center_x - center_thickness/2,
            field_bounds['y'] + border_offset,
            center_thickness,
            field_bounds['height'] - 2 * border_offset
        ))
        
        # Draw center circle (light gray) with anti-aliasing
        center_y = field_bounds['y'] + field_bounds['height'] / 2
        circle_radius = min(field_bounds['width'], field_bounds['height']) * 0.15
        pg.draw.circle(screen, (150, 150, 150), (int(center_x), int(center_y)), int(circle_radius), 3)
    
    def render_position(self, screen, position, angle, field_bounds, color=(0, 0, 0), radius=30, show_tof_rays=False, localizer=None, real_pos=None, real_angle=None, is_fake_field=False, show_guess_rays=False):
        """Render a position on the field with direction indicator and optional ToF rays"""
        if position:
            screen_pos = self.field_to_screen(position[0], position[1], field_bounds)
            
            # Draw black circle for the robot with anti-aliasing
            pg.draw.circle(screen, color, screen_pos, radius)
            
            # Draw simple direction indicator line
            import math
            direction_length = radius + 8
            end_x = screen_pos[0] + direction_length * math.cos(math.radians(angle))
            end_y = screen_pos[1] - direction_length * math.sin(math.radians(angle))  # Negative because screen Y is inverted
            
            # Draw the direction line with anti-aliasing
            pg.draw.line(screen, color, screen_pos, (end_x, end_y), 2)
            
            # Use the current robot position for all ray calculations
            robot_screen_pos = screen_pos  # This is already the correct position for the current field
            
            # Draw ToF sensor rays if requested and localizer data is available
            if show_tof_rays and localizer and hasattr(localizer, 'distances') and hasattr(localizer, 'angles') and real_pos and real_angle:
                
                # Choose ray colors based on field type
                if is_fake_field:
                    ray_color = (255, 150, 150)  # Light red for fake field rays
                    dot_color = (200, 100, 100)  # Darker red for intersection dots
                    label_color = (255, 200, 200)  # Light red for labels
                else:
                    ray_color = (150, 150, 150)  # Gray for real field rays
                    dot_color = (100, 100, 100)  # Dark gray for intersection dots
                    label_color = (200, 200, 200)  # Light gray for labels
                
                for i, (distance, sensor_angle) in enumerate(zip(localizer.distances, localizer.angles)):
                    # Calculate absolute angle using robot angle
                    if is_fake_field and hasattr(localizer, 'real_angle'):
                        # For fake field, use the real IMU angle
                        absolute_angle = localizer.real_angle + sensor_angle
                    else:
                        # For real field, use the actual robot angle
                        absolute_angle = angle + sensor_angle
                    
                    # Debug: Show what distances we're using for rendering
                    if DEBUG_RAYCAST and i == 0:
                        print(f"DEBUG: Rendering using distance {distance:.1f}mm for sensor angle {sensor_angle}°")
                    
                    # Calculate ray end point
                    if distance < 5000:  # Valid distance (not the max distance)
                        ray_length = distance * field_bounds['scale']  # Use actual distance
                        ray_end_x = robot_screen_pos[0] + ray_length * math.cos(math.radians(absolute_angle))
                        ray_end_y = robot_screen_pos[1] - ray_length * math.sin(math.radians(absolute_angle))
                        
                        # Debug rendering (only for first sensor and only when input received)
                        if i == 0 and hasattr(localizer, '_debug_render') and localizer._debug_render:
                            if DEBUG_RAYCAST:
                                print(f"DEBUG: Rendering test angle {test_angle:.1f}° - distance={distance:.1f}mm, ray_length={ray_length:.1f}px, scale={field_bounds['scale']:.3f}")
                                print(f"DEBUG: Robot screen pos: {robot_screen_pos}, ray end: ({ray_end_x:.1f}, {ray_end_y:.1f})")
                        
                        # Draw ray from robot position to intersection point
                        pg.draw.line(screen, ray_color, robot_screen_pos, (ray_end_x, ray_end_y), 1)
                        
                        # Draw small dot at intersection point
                        pg.draw.circle(screen, dot_color, (int(ray_end_x), int(ray_end_y)), 2)
                        
                        # Draw sensor angle labels with white outline
                        if i % 2 == 0:  # Only show every other sensor to avoid clutter
                            font = pg.font.Font(None, 16)
                            mid_x = (robot_screen_pos[0] + ray_end_x) / 2
                            mid_y = (robot_screen_pos[1] + ray_end_y) / 2
                            text_str = f"{sensor_angle}°"
                            
                            # Render text with white outline for visibility
                            outline_text = font.render(text_str, True, (255, 255, 255))  # White outline
                            main_text = font.render(text_str, True, label_color)  # Main color
                            
                            # Draw outline (offset by 1 pixel in each direction)
                            for dx in [-1, 0, 1]:
                                for dy in [-1, 0, 1]:
                                    if dx != 0 or dy != 0:  # Don't draw outline at center
                                        screen.blit(outline_text, (mid_x + dx, mid_y + dy))
                            
                            # Draw main text on top
                            screen.blit(main_text, (mid_x, mid_y))
                    else:
                        # Draw a long ray if no intersection found
                        ray_length = 200
                        ray_end_x = robot_screen_pos[0] + ray_length * math.cos(math.radians(absolute_angle))
                        ray_end_y = robot_screen_pos[1] - ray_length * math.sin(math.radians(absolute_angle))
                        
                        # Draw dashed ray for no intersection
                        pg.draw.line(screen, (100, 100, 100), robot_screen_pos, (ray_end_x, ray_end_y), 1)
            
            # Draw guess position rays if requested (for comparison with actual rays)
            if show_guess_rays and localizer and hasattr(localizer, 'distances') and hasattr(localizer, 'angles') and hasattr(localizer, 'best_guess') and hasattr(localizer, 'real_angle'):
                guess_pos = localizer.best_guess
                guess_screen_pos = self.field_to_screen(guess_pos[0], guess_pos[1], field_bounds)
                real_angle = localizer.real_angle  # Use the real IMU angle
                
                # Draw guess position rays in a different color (blue) using the real angle
                for i, (actual_distance, sensor_angle) in enumerate(zip(localizer.distances, localizer.angles)):
                    # Calculate what this sensor would read at the guess position with the real angle
                    expected_distance = localizer.tof_sensors[i].raycast_distance(guess_pos, real_angle, localizer.field)
                    
                    # Calculate absolute angle using the real angle
                    absolute_angle = real_angle + sensor_angle
                    
                    # Calculate ray end point for expected distance
                    if expected_distance < 5000:  # Valid distance
                        ray_length = expected_distance * field_bounds['scale']  # Use actual distance
                        ray_end_x = guess_screen_pos[0] + ray_length * math.cos(math.radians(absolute_angle))
                        ray_end_y = guess_screen_pos[1] - ray_length * math.sin(math.radians(absolute_angle))
                        
                        # Draw expected ray in blue
                        pg.draw.line(screen, (100, 150, 255), guess_screen_pos, (ray_end_x, ray_end_y), 2)
                        
                        # Draw small dot at expected intersection point
                        pg.draw.circle(screen, (50, 100, 255), (int(ray_end_x), int(ray_end_y)), 3)
                        
                        # Draw error line connecting actual and expected intersection points
                        if actual_distance < 5000:
                            actual_ray_length = actual_distance * field_bounds['scale']  # Use actual distance
                            actual_ray_end_x = robot_screen_pos[0] + actual_ray_length * math.cos(math.radians(absolute_angle))
                            actual_ray_end_y = robot_screen_pos[1] - actual_ray_length * math.sin(math.radians(absolute_angle))
                            
                            # Draw error line in red
                            pg.draw.line(screen, (255, 100, 100), (int(actual_ray_end_x), int(actual_ray_end_y)), (int(ray_end_x), int(ray_end_y)), 1)
                    else:
                        # Draw a long ray if no intersection found
                        ray_length = 200
                        ray_end_x = guess_screen_pos[0] + ray_length * math.cos(math.radians(absolute_angle))
                        ray_end_y = guess_screen_pos[1] - ray_length * math.sin(math.radians(absolute_angle))
                        
                        # Draw dashed ray for no intersection
                        pg.draw.line(screen, (100, 150, 255), guess_screen_pos, (ray_end_x, ray_end_y), 1)
            
            # Draw position and angle label with better font and white outline
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


# test code
if __name__ == "__main__":
    import pygame as pg
    
    field = Field()
    real_pos = (0.0, 0.0)  # Real position
    real_angle = 0.0
    fake_pos = (0.0, 0.0)  # Fake position (from localizer)
    fake_angle = 0.0
    
    if DEBUG_LOCALIZATION:
        print(f"DEBUG: Initial robot position: {real_pos}")
        print(f"DEBUG: Initial robot angle: {real_angle}")
        print(f"DEBUG: Field bounds: left={field.left_wall_x}, right={field.right_wall_x}, top={field.top_wall_y}, bottom={field.bottom_wall_y}")

    # Initialize systems
    fakeIMU = FakeIMU()
    fakeLo = FakeLocalizer(field=field)
    
    # Initialize pygame with anti-aliasing
    pg.init()
    screen = pg.display.set_mode((1200, 800), pg.RESIZABLE)
    pg.display.set_caption("Localization Visualization - Real vs Fake")
    clock = pg.time.Clock()
    
    # Enable anti-aliasing for better rendering quality
    pg.display.set_allow_screensaver(True)
    
    # Initialize systems
    input_handler = InputHandler()
    field_renderer = FieldRenderer(field)
    
    # Calculate field bounds for each view
    screen_width, screen_height = screen.get_size()
    field_width = screen_width // 2
    field_height = screen_height
    
    real_field_bounds = field_renderer.calculate_field_bounds(field_width, field_height)
    fake_field_bounds = field_renderer.calculate_field_bounds(field_width, field_height)
    fake_field_bounds['x'] += field_width  # Offset for right side
    
    running = True
    while running:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)
                screen_width, screen_height = screen.get_size()
                field_width = screen_width // 2
                field_height = screen_height
                
                # Recalculate field bounds
                real_field_bounds = field_renderer.calculate_field_bounds(field_width, field_height)
                fake_field_bounds = field_renderer.calculate_field_bounds(field_width, field_height)
                fake_field_bounds['x'] += field_width
        
        # Handle input
        input_handler.handle_events(events)
        
        # Update positions only when input is received
        if input_handler.input_received:
            # Handle keyboard input for real position and rotation with field constraints
            new_real_pos, new_real_angle = input_handler.get_keyboard_input(real_pos, real_angle, field=field)
            if new_real_pos != real_pos or new_real_angle != real_angle:
                if DEBUG_LOCALIZATION:
                    print(f"DEBUG: Robot position changed from {real_pos} to {new_real_pos}")
                    print(f"DEBUG: Robot angle changed from {real_angle} to {new_real_angle}")
                real_pos = new_real_pos
                real_angle = new_real_angle
            
            # Handle mouse input for both fields
            # Check if mouse is over real field (left side)
            if input_handler.mouse_pos[0] < field_width:
                mouse_pos = input_handler.get_mouse_input(field_renderer, real_field_bounds, field=field)
                if mouse_pos:
                    real_pos = mouse_pos
            # Check if mouse is over fake field (right side)
            else:
                mouse_pos = input_handler.get_mouse_input(field_renderer, fake_field_bounds, field=field)
                if mouse_pos:
                    fake_pos = mouse_pos
            
            # Update IMU with real rotation
            fakeIMU.set_rotation(real_angle)
        
        # Always update fake position from localizer (every frame)
        fakeLo.real_pos = real_pos  # Pass real position to localizer
        fakeLo.real_angle = real_angle  # Pass real angle to localizer
        if input_handler.input_received:
            if DEBUG_LOCALIZATION:
                print(f"DEBUG: === LOCALIZATION UPDATE ===")
        fake_pos = fakeLo.localize()
        if input_handler.input_received and DEBUG_LOCALIZATION:
            print(f"DEBUG: Best guess position: ({fake_pos[0]:.1f}, {fake_pos[1]:.1f})")
        fake_angle = fakeIMU.get_angle()  # Get fake angle from IMU
        
        # Clear screen
        screen.fill((30, 30, 30))
        
        # Render real position field (left side) with ToF rays
        field_renderer.render_field(screen, real_field_bounds, (100, 255, 100))
        field_renderer.render_position(screen, real_pos, real_angle, real_field_bounds, (0, 0, 0), 30, show_tof_rays=True, localizer=fakeLo, real_pos=real_pos, real_angle=real_angle, is_fake_field=False)
        
        # Draw semi-transparent overlay of estimated position over real position
        if hasattr(fakeLo, 'best_guess') and hasattr(fakeLo, 'real_angle'):
            # Create a semi-transparent surface
            overlay_surface = pg.Surface((60, 60), pg.SRCALPHA)
            overlay_surface.fill((255, 255, 0, 128))  # Yellow with 50% transparency
            
            # Convert estimated position to screen coordinates
            estimated_screen_pos = field_renderer.field_to_screen(fakeLo.best_guess[0], fakeLo.best_guess[1], real_field_bounds)
            
            # Draw the overlay circle
            pg.draw.circle(overlay_surface, (255, 255, 0, 128), (30, 30), 30)
            
            # Blit the overlay surface to the screen
            screen.blit(overlay_surface, (estimated_screen_pos[0] - 30, estimated_screen_pos[1] - 30))
            
            # Draw direction line for estimated position using real angle
            end_x = estimated_screen_pos[0] + 40 * math.cos(math.radians(fakeLo.real_angle))
            end_y = estimated_screen_pos[1] - 40 * math.sin(math.radians(fakeLo.real_angle))
            pg.draw.line(screen, (255, 255, 0, 128), estimated_screen_pos, (end_x, end_y), 3)
        
        # Render fake position field (right side) with fake rays and guess rays
        field_renderer.render_field(screen, fake_field_bounds, (100, 100, 255))
        field_renderer.render_position(screen, fake_pos, fake_angle, fake_field_bounds, (0, 0, 0), 30, show_tof_rays=True, localizer=fakeLo, real_pos=fake_pos, real_angle=fake_angle, is_fake_field=True, show_guess_rays=True)
        
        # Draw field labels above each field
        font = pg.font.Font(None, 36)
        real_label = font.render("REAL POSITION (actual sensor rays)", True, (255, 255, 255))
        fake_label = font.render("FAKE POSITION (red=actual, blue=expected)", True, (255, 255, 255))
        
        # Center labels above each field
        real_label_x = real_field_bounds['x'] + real_field_bounds['width'] / 2 - real_label.get_width() / 2
        fake_label_x = fake_field_bounds['x'] + fake_field_bounds['width'] / 2 - fake_label.get_width() / 2
        
        screen.blit(real_label, (real_label_x, 10))
        screen.blit(fake_label, (fake_label_x, 10))
        
        # Draw instructions
        small_font = pg.font.Font(None, 24)
        instructions = [
            "Controls:",
            "WASD/Arrow Keys: Move real position",
            "E/Q Keys: Rotate real position",
            "Mouse Click: Set position on either field",
            "Window: Resizable"
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (10, screen_height - 100 + i * 20))
        
        # Draw ToF sensor data in a dedicated area
        if hasattr(fakeLo, 'distances') and hasattr(fakeLo, 'angles'):
            # Show sensor data in a box on the right side
            sensor_box_x = screen_width - 300
            sensor_box_y = 50
            
            # Draw background box
            pg.draw.rect(screen, (50, 50, 50), (sensor_box_x, sensor_box_y, 290, 220))
            pg.draw.rect(screen, (100, 100, 100), (sensor_box_x, sensor_box_y, 290, 220), 2)
            
            # Draw title
            title_font = pg.font.Font(None, 20)
            title_text = title_font.render("ToF Sensor Data:", True, (255, 255, 255))
            screen.blit(title_text, (sensor_box_x + 10, sensor_box_y + 10))
            
            # Draw sensor data in two columns
            for i, (dist, angle) in enumerate(zip(fakeLo.distances, fakeLo.angles)):
                col = i // 4
                row = i % 4
                x_offset = col * 140
                y_offset = row * 20
                
                sensor_text = f"{angle:3.0f}°: {dist:5.0f}mm"
                text = small_font.render(sensor_text, True, (200, 200, 200))
                screen.blit(text, (sensor_box_x + 10 + x_offset, sensor_box_y + 35 + y_offset))
            
            # Draw localization error
            if hasattr(fakeLo, 'best_error'):
                error_text = f"Localization Error: {fakeLo.best_error:.1f}mm"
                error_color = (255, 255, 0) if fakeLo.best_error < 100 else (255, 100, 100)
                text = small_font.render(error_text, True, error_color)
                screen.blit(text, (sensor_box_x + 10, sensor_box_y + 195))
        
        pg.display.flip()
        clock.tick(60)
    
    pg.quit()