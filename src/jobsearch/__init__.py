"""
jobsearch - A Python package for job search automation
"""

import logging

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # This ensures output to the terminal
    ],
)

__version__ = "0.1.0"

# You can add any other package initialization here
