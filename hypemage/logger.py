"""
Logging System for Robot

Provides structured logging with:
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- File output for headless operation
- Colored console output for development (yellow warnings, red errors)
- Automatic log rotation
- Performance-optimized (minimal overhead in production)

Usage:
    from hypemage.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Robot started")
    logger.debug("Detailed debug info")
    logger.error("Something went wrong!")
"""

import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

try:
    import colorlog
    _HAS_COLORLOG = True
except ImportError:
    _HAS_COLORLOG = False


class RobotLogger:
    """Singleton logger manager for the robot"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = Path.home() / "robot_logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Get log level from environment or default to INFO
        log_level_str = os.environ.get('ROBOT_LOG_LEVEL', 'INFO')
        self.log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # Determine if we're running headless (no terminal)
        self.headless = not sys.stdout.isatty()
        
        # Configure root logger
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure the logging system"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Colored formatter for console (if colorlog available)
        if _HAS_COLORLOG:
            colored_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            colored_formatter = simple_formatter
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # File handler (always on, rotates daily)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / 'robot.log',
            when='midnight',
            interval=1,
            backupCount=7,  # Keep 7 days of logs
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler (only if not headless or if explicitly enabled)
        # Uses colored formatter if available
        if not self.headless or os.environ.get('ROBOT_CONSOLE_LOG', '0') == '1':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(colored_formatter)  # Use colored formatter
            root_logger.addHandler(console_handler)
        
        # Error file handler (separate file for errors)
        error_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / 'robot_errors.log',
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Log startup info
        root_logger.info("="*60)
        root_logger.info("Robot logging initialized")
        root_logger.info(f"Log level: {logging.getLevelName(self.log_level)}")
        root_logger.info(f"Headless mode: {self.headless}")
        root_logger.info(f"Console colors: {_HAS_COLORLOG}")
        root_logger.info(f"Log directory: {self.log_dir}")
        root_logger.info("="*60)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific module"""
        return logging.getLogger(name)


# Singleton instance
_logger_manager = RobotLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Starting motor controller")
    """
    return _logger_manager.get_logger(name)


def set_log_level(level: str):
    """
    Change log level at runtime
    
    Args:
        level: Log level string ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)
    logging.info(f"Log level changed to {level}")


def get_log_dir() -> Path:
    """Get the log directory path"""
    return _logger_manager.log_dir


# Performance utilities
class LogThrottle:
    """
    Throttle log messages to prevent spam in tight loops
    
    Example:
        throttle = LogThrottle(interval=1.0)  # Max once per second
        
        while True:
            if throttle.should_log():
                logger.debug("Loop iteration")
    """
    
    def __init__(self, interval: float = 1.0):
        """
        Args:
            interval: Minimum time between log messages (seconds)
        """
        self.interval = interval
        self.last_log_time = 0.0
    
    def should_log(self) -> bool:
        """Check if enough time has passed to log again"""
        current_time = time.time()
        if current_time - self.last_log_time >= self.interval:
            self.last_log_time = current_time
            return True
        return False


if __name__ == '__main__':
    # Test logging system
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test throttling
    throttle = LogThrottle(interval=0.5)
    for i in range(100):
        if throttle.should_log():
            logger.info(f"Loop iteration {i}")
        time.sleep(0.1)
    
    print(f"\nLogs saved to: {get_log_dir()}")
