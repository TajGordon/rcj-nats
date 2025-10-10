"""
Configuration Manager - Bot-specific configuration loading

This module provides utilities for loading and saving bot-specific configuration.
Each bot (storm, necron) has its own configuration section.

The bot identity is determined by:
1. Command-line argument (--robot storm/necron)
2. Environment variable (ROBOT_NAME)
3. Hostname (if it matches 'storm' or 'necron')
4. Default to 'storm'

Usage:
    from hypemage.config import get_robot_id, load_config, save_config
    
    robot_id = get_robot_id()  # Returns 'storm' or 'necron'
    config = load_config(robot_id)  # Loads config for this bot
    config['camera']['width'] = 800
    save_config(robot_id, config)  # Saves back to config.json
"""

import json
import os
import socket
from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy
from hypemage.logger import get_logger

logger = get_logger(__name__)

# Path to the central config file
CONFIG_PATH = Path(__file__).parent / "config.json"


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence
    
    Args:
        base: Base dictionary (defaults)
        override: Override dictionary (robot-specific)
    
    Returns:
        Merged dictionary
    """
    result = deepcopy(base)
    
    for key, value in override.items():
        if key.startswith('_'):  # Skip comment fields
            continue
            
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Override value
            result[key] = deepcopy(value)
    
    return result


def get_robot_id(override: Optional[str] = None) -> str:
    """
    Determine which robot this is (storm or necron)
    
    Priority:
    1. override parameter (e.g., from argparse)
    2. ROBOT_NAME environment variable
    3. Hostname (if it contains 'storm' or 'necron')
    4. Default to 'storm'
    
    Args:
        override: Explicit robot ID (from command-line arg)
    
    Returns:
        'storm' or 'necron'
    """
    # 1. Check override parameter
    if override:
        robot_id = override.lower()
        if robot_id in ['storm', 'necron']:
            logger.info(f"Robot ID from override: {robot_id}")
            return robot_id
    
    # 2. Check environment variable
    env_robot = os.environ.get('ROBOT_NAME', '').lower()
    if env_robot in ['storm', 'necron']:
        logger.info(f"Robot ID from ROBOT_NAME env: {env_robot}")
        return env_robot
    
    # 3. Check hostname
    try:
        hostname = socket.gethostname().lower()
        # f7 = Storm, m7 = Necron
        if 'f7' in hostname or 'storm' in hostname:
            logger.info(f"Robot ID from hostname: storm (hostname={hostname})")
            return 'storm'
        elif 'm7' in hostname or 'necron' in hostname:
            logger.info(f"Robot ID from hostname: necron (hostname={hostname})")
            return 'necron'
    except Exception as e:
        logger.warning(f"Failed to get hostname: {e}")
    
    # 4. Default to storm
    logger.info("Robot ID defaulting to: storm")
    return 'storm'


def load_config(robot_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a specific robot, merging with defaults
    
    Args:
        robot_id: Which robot to load config for ('storm' or 'necron')
                 If None, auto-detects using get_robot_id()
    
    Returns:
        Dictionary with configuration for this robot (defaults + robot-specific overrides)
    
    Raises:
        FileNotFoundError: If config.json doesn't exist
        KeyError: If robot_id not found in config
    """
    if robot_id is None:
        robot_id = get_robot_id()
    
    robot_id = robot_id.lower()
    
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            all_config = json.load(f)
        
        # Get defaults
        defaults = all_config.get('defaults', {})
        
        # Get robot-specific config
        if robot_id not in all_config:
            available = [k for k in all_config.keys() if not k.startswith('_') and k != 'defaults']
            raise KeyError(f"Robot '{robot_id}' not found in config. Available: {available}")
        
        robot_config = all_config[robot_id]
        
        # Merge defaults with robot-specific config
        merged_config = deep_merge(defaults, robot_config)
        
        logger.info(f"Loaded configuration for robot: {robot_id} (with defaults merged)")
        return merged_config
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def save_config(robot_id: str, config: Dict[str, Any], save_only_overrides: bool = False) -> None:
    """
    Save configuration for a specific robot
    
    Args:
        robot_id: Which robot to save config for ('storm' or 'necron')
        config: Configuration dictionary to save
        save_only_overrides: If True, only saves values that differ from defaults
                            If False, saves the full merged config
    
    Raises:
        FileNotFoundError: If config.json doesn't exist
    
    Note:
        By default, saves the full merged config (easier to understand).
        Use save_only_overrides=True for a cleaner config file with less duplication.
    """
    robot_id = robot_id.lower()
    
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    
    try:
        # Load full config
        with open(CONFIG_PATH, 'r') as f:
            all_config = json.load(f)
        
        # Update this robot's section
        all_config[robot_id] = config
        
        # Write back
        with open(CONFIG_PATH, 'w') as f:
            json.dump(all_config, f, indent=2)
        
        logger.info(f"Saved configuration for robot: {robot_id}")
    
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise


def update_config_section(robot_id: str, section_path: str, value: Any) -> None:
    """
    Update a specific section of the config (e.g., 'hsv_ranges.ball.lower')
    
    Args:
        robot_id: Which robot to update config for
        section_path: Dot-separated path (e.g., 'camera.width' or 'hsv_ranges.ball.lower')
        value: New value to set
    
    Example:
        update_config_section('storm', 'camera.width', 800)
        update_config_section('necron', 'hsv_ranges.ball.lower', [15, 120, 120])
    """
    config = load_config(robot_id)
    
    # Navigate to the target section
    keys = section_path.split('.')
    target = config
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]
    
    # Set the value
    target[keys[-1]] = value
    
    # Save back
    save_config(robot_id, config)
    logger.info(f"Updated {robot_id}.{section_path} = {value}")


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration structure (used for creating new bots)
    
    Returns:
        Dictionary with default config structure
    """
    return {
        "camera": {
            "width": 640,
            "height": 480,
            "format": "RGB888",
            "fps_target": 30
        },
        "hsv_ranges": {
            "ball": {
                "lower": [0, 180, 170],
                "upper": [50, 255, 255],
                "min_area": 0,
                "max_area": 500
            },
            "blue_goal": {
                "lower": [100, 150, 50],
                "upper": [120, 255, 255],
                "min_area": 500,
                "max_area": 1000
            },
            "yellow_goal": {
                "lower": [20, 100, 100],
                "upper": [40, 255, 255],
                "min_area": 500,
                "max_area": 1000
            }
        },
        "detection": {
            "proximity_threshold": 5000,
            "angle_tolerance": 15,
            "goal_center_tolerance": 0.15
        },
        "motors": {
            "i2c_address": "0x50",
            "max_speed": 255,
            "acceleration": 50
        },
        "motor_addresses": [26, 27, 29, 25],
        "motor_multipliers": [-1.0, -1.0, 1.0, 1.0]
    }
