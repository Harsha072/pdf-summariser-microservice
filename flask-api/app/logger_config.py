import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure logging with timestamp in filename
timestamp = datetime.now().strftime('%Y%m%d')
log_file_path = os.path.join(logs_dir, f'app_{timestamp}.log')

def setup_logger(name):
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Prevent duplicate handlers
        logger.setLevel(logging.INFO)
        
        # File handler (rotating log files)
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Format for logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
if __name__ == "__main__":
    test_logger = setup_logger("test")
    test_logger.info("Test info message")
    test_logger.error("Test error message")
    print(f"Check logs at: {log_file_path}")