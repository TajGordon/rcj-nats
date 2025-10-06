import config
import board
import busio
from tof import ToF
from imu import IMU

import math

class Localizer:
    def __init__(self, i2c = busio.I2C(board.SCL, board.SDA), tofs=None, imu=IMU(i2c=busio.I2C(board.SCL, board.SDA))):
        self.tofs = tofs if tofs is not None else []
        self.tof_angles = [] # used to key for distances
        self.tof_distances = {} # angle -> distance
        # initialize tofs if not provided, this lets us fake the tofs
        if tofs is None:
            for addr in config.tof_addrs:
                self.tofs.append(ToF(addr=addr, offset=config.tof_offsets[addr], angle=config.tof_angles[addr], i2c=i2c))
                self.tof_angles.append(self.tofs[-1].angle)
                self.tof_distances[self.tof_angles[-1]] = 0 # default value
        
        # get angle from the imu, just call 'cur_angle()'
        self.imu = imu

        # for debug stuff (mainly for simulator)
        if tofs is not None:
            self.tofs = tofs
        if imu is not None:
            self.imu = imu

        self.best_guess = [0, 0] # list because fk python tuples
        self.best_error = float('inf')
        
    
    def _update_distances(self):
        for tof in self.tofs:
            dist = tof.next_dist()
            self.tof_distances[tof.angle] = dist
    
    def _cast_ray(self, position, angle):
        # just stores the distance of the closest one 
        # could be changed to report what wall it hit
        # checks ray intersection of each wall / line
        minimum_distance = float('inf') # stores distance squared
        dx = math.cos(angle)
        dy = math.sin(angle)
        for wall in config.walls: # should be 10 walls
            # TODO! write the code
            if wall['type'] == 'horizontal':
                t = (wall['x'] - position[0])/dx
                if t <= 0:
                    continue
                y = t * dy
                if y < wall['y_min'] or y > wall['y_max']:
                    continue
                x = t * dx
                dist = math.sqrt(x**2 + y**2)
                if dist < minimum_distance:
                    minimum_distance = dist
            else:
                t = (wall['y'] - position[0])/dy
                if t <= 0:
                    continue
                x = t * dx
                if x < wall['x_min'] or x > wall['x_max']:
                    continue
                y = t * dy
                dist = (x**2 + y**2) # store distance squared
                if dist < minimum_distance:
                    minimum_distance = dist
        return minimum_distance
    
    def _cast_rays(self, position, bot_angle):
        # goes through each angle and computes the raycast
        distances = {}
        for angle in self.tof_angles:
            dist = self._cast_ray(position, bot_angle + angle)
            distances[angle] = dist
        return distances

        
    def _compute_error(self, position, bot_angle):
        # simple cumulative error function, can be pulled out to create more complex ones
        # for example, you could take into account whether the tof had a huge difference to its last variation - perhaps a bot is blocking / unblocking it
        error = 0
        raycast_distances = self._cast_rays(position, bot_angle)
        for angle in self.tof_angles:
            diff = abs(raycast_distances[angle] - (self.tof_distances[angle] ** 2)) # square the tof distance to match the squared distance from the raycasting
            error += diff
        return error

        
    def localize(self):
        self._update_distances() # update to start the localization with accurate distances
        
        angle = self.imu.cur_angle() # to not recall a bunch of times
        
        # in mm
        move_amount = 32 # power of two cuz why not
        decay_rate = 0.5
        cutoff = 0.05
        while move_amount > cutoff:
            converged = False
            while not converged:
                converged = True
                # only checks on axis aligned grid instead of relative positions
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        guess_pos = [self.best_guess[0] + move_amount * dx, self.best_guess[1] + move_amount * dy]
                        error = self._compute_error(guess_pos, angle)
                        if error < self.best_error:
                            converged = False
                            self.best_error = error
                            self.best_guess = guess_pos
            move_amount *= decay_rate
        
        # now should be able to just do localizer.best_guess, but will return the position as well jsut in case
        return self.best_guess, self.best_error


if __name__ == "__main__":
    import asyncio
    import websockets
    import json
    import time
    from tof import ToF
    from imu import IMU
    
    print("🤖 Starting real hardware localization system...")
    
    # Initialize real hardware components
    try:
        print("🔧 Initializing I2C bus...")
        i2c = board.I2C(board.SCL, board.SDA)
        
        print("🧭 Initializing IMU...")
        imu = IMU(i2c=i2c)
        
        print("📡 Initializing ToF sensors...")
        # Create ToF sensors based on config
        tofs = []
        if config.tof_addrs:  # Use config if available
            for addr in config.tof_addrs:
                offset = config.tof_offsets.get(addr, (0, 0))
                angle = config.tof_angles.get(addr, 0)
                tof = ToF(addr=addr, offset=offset, angle=math.radians(angle), i2c=i2c)
                tofs.append(tof)
                print(f"  ✅ ToF sensor at 0x{addr:02x}, angle {angle}°")
        else:
            print("⚠️  No ToF configuration found in config.py")
            print("  Using default sensor configuration...")
            # Default configuration for testing
            default_config = [
                (0x29, 0),    # Front
                (0x2A, 45),   # Front-right  
                (0x2B, 90),   # Right
                (0x2C, 135),  # Back-right
                (0x2D, 180),  # Back
                (0x2E, -135), # Back-left
                (0x2F, -90),  # Left
                (0x30, -45),  # Front-left
            ]
            
            for addr, angle in default_config:
                try:
                    tof = ToF(addr=addr, offset=(0, 0), angle=math.radians(angle), i2c=i2c)
                    tofs.append(tof)
                    print(f"  ✅ ToF sensor at 0x{addr:02x}, angle {angle}°")
                except Exception as e:
                    print(f"  ❌ Failed to initialize ToF at 0x{addr:02x}: {e}")
        
        print(f"📊 Initialized {len(tofs)} ToF sensors")
        
        # Create localizer with real hardware
        localizer = Localizer(i2c=i2c, tofs=tofs, imu=imu)
        print("✅ Localizer initialized successfully!")
        
    except Exception as e:
        print(f"❌ Hardware initialization failed: {e}")
        print("🔧 Please check your hardware connections and try again")
        exit(1)
    
    # WebSocket client to send data to server
    async def send_localization_data():
        uri = "ws://localhost:8002/ws/localization"
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🌐 Connecting to localization server at {uri}...")
                async with websockets.connect(uri) as websocket:
                    print("✅ Connected to localization server!")
                    retry_count = 0  # Reset retry count on successful connection
                    
                    while True:
                        try:
                            # Perform localization
                            start_time = time.time()
                            position, error = localizer.localize()
                            angle = localizer.imu.cur_angle()
                            localization_time = time.time() - start_time
                            
                            # Prepare data to send
                            data = {
                                'position': position,
                                'angle': angle,
                                'error': error,
                                'timestamp': time.time(),
                                'localization_time_ms': localization_time * 1000
                            }
                            
                            # Send data to server
                            await websocket.send(json.dumps(data))
                            
                            # Print status
                            print(f"📍 Position: ({position[0]:.1f}, {position[1]:.1f}) mm, "
                                  f"Angle: {math.degrees(angle):.1f}°, "
                                  f"Error: {error:.2f}, "
                                  f"Time: {localization_time*1000:.1f}ms")
                            
                            # Wait before next localization
                            await asyncio.sleep(0.1)  # 10 Hz update rate
                            
                        except Exception as e:
                            print(f"❌ Localization error: {e}")
                            await asyncio.sleep(1)  # Wait before retrying
                            
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.InvalidURI,
                    ConnectionRefusedError) as e:
                retry_count += 1
                print(f"🔄 Connection failed (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    wait_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
                    print(f"⏳ Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    print("❌ Max retries exceeded. Please check if the server is running.")
                    break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                await asyncio.sleep(5)
    
    # Run the localization system
    print("🚀 Starting localization loop...")
    print("💡 Make sure the localization server is running:")
    print("   cd localization_server && python main.py")
    print("📱 View results at: http://localhost:8002")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        asyncio.run(send_localization_data())
    except KeyboardInterrupt:
        print("\n🛑 Localization system stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("🔧 Cleaning up hardware...")
        # Add any necessary cleanup code here
