# crawler/logger.py

import logging
import datetime
from crawler.config import LOG_DIR

class SingletonLogger:
    _instance = None
    _initialized = False

    @classmethod
    def get_logger(cls):
        if cls._instance is None:
            cls._instance = cls._setup_logger()
        return cls._instance

    @staticmethod
    def _setup_logger():
        """Setup logging to both console and file with timestamp."""
        # Create timestamp for log file
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = LOG_DIR / f'logs_{timestamp}.txt'
        
        # Custom formatter to handle grouping
        class GroupFormatter(logging.Formatter):
            def format(self, record):
                # Get the formatted message
                msg = super().format(record)
                
                # Add separators based on message content
                if "Attempting to crawl:" in record.msg:
                    msg = "\n" + "-"*40 + "\nCrawling New URL\n" + "-"*40 + "\n" + msg
                elif "Crawling Status:" in record.msg:
                    msg = "\n" + "-"*40 + "\nStatus Update\n" + msg
                elif "URLs remaining:" in record.msg:
                    msg = msg + "\n" + "-"*40 + "\n"  # Close the status group
                elif "Added" in record.msg and "new URLs to visit" in record.msg:
                    msg = msg + "\n"  # Just add a newline after adding URLs
                elif "Crawling complete" in record.msg:
                    msg = "\n" + "="*80 + "\n" + msg  # Final summary
                    
                return msg
        
        # Setup formatter
        formatter = GroupFormatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Setup logger
        logger = logging.getLogger('crawler')  # Use a specific name for our logger
        
        # Only add handlers if they haven't been added before
        if not logger.handlers:
            # Setup handlers
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            
            logger.setLevel(logging.INFO)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
            # Prevent double logging
            logger.propagate = False
            
            logger.info(f'Logging to file: {log_file}')
        
        return logger

def setup_logger():
    """Get or create the singleton logger instance."""
    return SingletonLogger.get_logger()