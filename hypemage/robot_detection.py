"""Robot Detection Utilities

Detects which robot is running and provides robot-specific configuration.
"""

import socket
from typing import Dict, List
from hypemage.logger import get_logger

logger = get_logger(__name__)


def get_robot_name() -> str:
    """
    Get the robot name from hostname
    
    Returns:
        'f7' for storm robot
        'm7' for necron robot
        'unknown' if cannot determine
    """
    try:
        hostname = socket.gethostname().lower()
        logger.debug(f"Detected hostname: {hostname}")
        
        if 'f7' in hostname:
            return 'f7'
        elif 'm7' in hostname:
            return 'm7'
        else:
            logger.warning(f"Unknown hostname '{hostname}', defaulting to 'm7'")
            return 'm7'
    except Exception as e:
        logger.error(f"Failed to get hostname: {e}, defaulting to 'm7'")
        return 'm7'


def get_motor_addresses(robot_name: str = None) -> List[int]:
    """
    Get motor I2C addresses for the current robot
    
    Motor address mapping:
    - m7 (necron): [27, 29, 25, 26] (back_left, front_left, front_right, back_right)
    - f7 (storm):  [28, 30, 26, 27] (mapped from m7: 25->26, 26->27, 27->28, 29->30)
    
    Args:
        robot_name: Optional robot name override. If None, auto-detects.
    
    Returns:
        List of 4 I2C addresses for motors
    """
    if robot_name is None:
        robot_name = get_robot_name()
    
    # m7 (necron) base addresses
    m7_addresses = [27, 29, 25, 26]
    
    if robot_name == 'm7':
        logger.info(f"Robot: m7 (necron) - Motor addresses: {m7_addresses}")
        return m7_addresses
    elif robot_name == 'f7':
        # f7 (storm) mapping:
        # m7: 25 -> f7: 26
        # m7: 26 -> f7: 27
        # m7: 27 -> f7: 28
        # m7: 29 -> f7: 30
        address_mapping = {
            25: 26,
            26: 27,
            27: 28,
            29: 30
        }
        
        f7_addresses = [address_mapping[addr] for addr in m7_addresses]
        logger.info(f"Robot: f7 (storm) - Motor addresses: {f7_addresses}")
        return f7_addresses
    else:
        logger.warning(f"Unknown robot '{robot_name}', using m7 addresses")
        return m7_addresses


def get_dribbler_address(robot_name: str = None) -> int:
    """
    Get dribbler motor I2C address for the current robot
    
    Args:
        robot_name: Optional robot name override. If None, auto-detects.
    
    Returns:
        I2C address for dribbler motor
    """
    if robot_name is None:
        robot_name = get_robot_name()
    
    dribbler_addresses = {
        'f7': 29,  # storm
        'm7': 30   # necron
    }
    
    address = dribbler_addresses.get(robot_name, 30)  # Default to m7
    logger.info(f"Robot: {robot_name} - Dribbler address: {address}")
    return address


def get_robot_config_overrides(robot_name: str = None) -> Dict:
    """
    Get robot-specific configuration overrides
    
    Args:
        robot_name: Optional robot name override. If None, auto-detects.
    
    Returns:
        Dictionary of config overrides for this robot
    """
    if robot_name is None:
        robot_name = get_robot_name()
    
    # Motor addresses
    motor_addresses = get_motor_addresses(robot_name)
    dribbler_address = get_dribbler_address(robot_name)
    
    config = {
        'robot_name': robot_name,
        'motor_addresses': motor_addresses,
        'dribbler': {
            'address': dribbler_address
        }
    }
    
    logger.info(f"Robot config overrides for {robot_name}: motor_addresses={motor_addresses}, dribbler={dribbler_address}")
    return config


if __name__ == '__main__':
    # Test robot detection
    print("=" * 60)
    print("Robot Detection Test")
    print("=" * 60)
    
    robot = get_robot_name()
    print(f"\nDetected robot: {robot}")
    
    motor_addrs = get_motor_addresses()
    print(f"Motor addresses: {motor_addrs}")
    print(f"  [0] back_left:   0x{motor_addrs[0]:02X} ({motor_addrs[0]})")
    print(f"  [1] front_left:  0x{motor_addrs[1]:02X} ({motor_addrs[1]})")
    print(f"  [2] front_right: 0x{motor_addrs[2]:02X} ({motor_addrs[2]})")
    print(f"  [3] back_right:  0x{motor_addrs[3]:02X} ({motor_addrs[3]})")
    
    dribbler_addr = get_dribbler_address()
    print(f"\nDribbler address: 0x{dribbler_addr:02X} ({dribbler_addr})")
    
    config = get_robot_config_overrides()
    print(f"\nFull config overrides:")
    import json
    print(json.dumps(config, indent=2))
