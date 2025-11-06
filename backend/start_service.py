"""
Quarterly Theory Service Launcher
Purpose: Load configuration and start the quarterly theory analysis service
Author: AI Assistant
Created: 2025-10-29
"""

import asyncio
import configparser
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from quarterly_service import QuarterlyTheoryService
import logging

def load_config(config_path: str = 'config.ini') -> dict:
    """Load configuration from INI file"""
    config = configparser.ConfigParser()
    
    # Check if config exists
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        print("Please create config.ini from config_template.ini")
        sys.exit(1)
        
    config.read(config_path)
    
    # Convert to dictionary structure
    config_dict = {
        'database': {
            'host': config.get('database', 'host'),
            'port': config.getint('database', 'port'),
            'database': config.get('database', 'database'),
            'user': config.get('database', 'user'),
            'password': config.get('database', 'password')
        },
        'redis': {
            'host': config.get('redis', 'host'),
            'port': config.getint('redis', 'port'),
            'db': config.getint('redis', 'db')
        },
        'service': {
            'symbol': config.get('service', 'symbol'),
            'update_interval': config.getint('service', 'update_interval'),
            'log_level': config.get('service', 'log_level'),
            'log_file': config.get('service', 'log_file')
        }
    }
    
    return config_dict

def setup_logging(config: dict):
    """Setup logging configuration"""
    log_level = config['service']['log_level']
    log_file = config['service']['log_file']
    
    # Create logs directory if needed
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

async def main():
    """Main entry point"""
    print("=" * 60)
    print("Quarterly Theory Analysis Service")
    print("=" * 60)
    
    # Load configuration
    print("\n[1/3] Loading configuration...")
    try:
        config = load_config()
        print(f"✓ Configuration loaded")
        print(f"  - Database: {config['database']['host']}:{config['database']['port']}")
        print(f"  - Redis: {config['redis']['host']}:{config['redis']['port']}")
        print(f"  - Symbol: {config['service']['symbol']}")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)
    
    # Setup logging
    print("\n[2/3] Setting up logging...")
    try:
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Logging configured")
        print(f"✓ Logging initialized")
        print(f"  - Log file: {config['service']['log_file']}")
    except Exception as e:
        print(f"✗ Logging error: {e}")
        sys.exit(1)
    
    # Create and start service
    print("\n[3/3] Starting service...")
    try:
        service = QuarterlyTheoryService(
            config['database'],
            config['redis']
        )
        print("✓ Service initialized")
        print("\n" + "=" * 60)
        print("Service running. Press Ctrl+C to stop.")
        print("=" * 60 + "\n")
        
        await service.start_service()
        
    except KeyboardInterrupt:
        logger.info("\n\nService interrupted by user")
        print("\n\n" + "=" * 60)
        print("Service stopped by user")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        print(f"\n✗ Service error: {e}")
        sys.exit(1)
    finally:
        if 'service' in locals():
            service.close()
            print("Cleanup complete")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
