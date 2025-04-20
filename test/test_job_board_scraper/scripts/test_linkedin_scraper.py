#!/usr/bin/env python3
"""
Test script for LinkedIn scraper
This script demonstrates how to use the LinkedIn scraper to search for jobs.
"""

import logging
from pprint import pprint

from jobsearch.job_board_scraper.linkedin import LinkedInScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to test the LinkedIn scraper"""
    
    # Define search keywords
    keywords = ["python developer", "data scientist"]
    
    # Initialize the scraper
    scraper = LinkedInScraper(keywords)
    
    # Print the keywords being searched
    print(f"Searching LinkedIn for: {', '.join(keywords)}")
    
    # Search for jobs
    try:
        jobs = scraper.search()
        
        # Print the results
        print(f"\nFound {len(jobs)} jobs:")
        for i, job in enumerate(jobs, 1):
            print(f"\nJob {i}:")
            pprint(job)
            print("-" * 50)
            
    except Exception as e:
        print(f"Error searching for jobs: {e}")

if __name__ == "__main__":
    main() 