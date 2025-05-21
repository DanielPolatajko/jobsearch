#!/usr/bin/env python3
"""
Test script to verify the crawler logger is working properly.
"""

# Import the logger from crawler.py
from jobsearch.job_crawler.crawler import logger


def test_crawler_logger():
    """Test that the crawler logger outputs to the terminal"""
    logger.debug("This is a DEBUG message (should not appear)")
    logger.info("This is an INFO message (should appear)")
    logger.warning("This is a WARNING message (should appear)")
    logger.error("This is an ERROR message (should appear)")
    logger.critical("This is a CRITICAL message (should appear)")


if __name__ == "__main__":
    print("Testing crawler logger...")
    test_crawler_logger()
    print("If you can see log messages above, the logger is working correctly.")
