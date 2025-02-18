# crawler/logger.py

import logging
import datetime
import os
from crawler.config import LOG_DIR

def setup_logger():
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
                if "Starting crawl with" in record.msg:
                    msg = "\n" + "="*80 + "\n" + msg + "\n" + "="*80
                elif "Attempting to crawl:" in record.msg:
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
        
        # Setup handlers
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Setup logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Prevent double logging
        logger.propagate = False
        
        logger.info(f'Logging to file: {log_file}')

        return logger