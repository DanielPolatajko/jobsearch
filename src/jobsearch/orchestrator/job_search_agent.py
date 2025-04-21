# main.py - The core orchestrator

import os
import json
import datetime
import dotenv
from jobsearch.job_board_scraper import LinkedInScraper
from jobsearch.job_matcher import GroqJobMatcher

class JobSearchAgent:
    def __init__(self, config_path: str = "config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        dotenv.load_dotenv()
        
        # Initialize components
        self.job_sources = [
            LinkedInScraper(
                keywords=self.config["search_keywords"],
                locations=self.config.get("location_preferences", [])
            )
        ]
        
        self.matcher = GroqJobMatcher(
            candidate_profile=self.config["candidate_profile"],
            candidate_interests=self.config["candidate_interests"],
            api_key=os.environ.get("GROQ_API_KEY")
        )
        
        self.job_database = {}  # Simple in-memory store, replace with proper DB
    
    def run_job_search(self):
        """Execute a complete job search cycle"""
        print(f"Starting job search at {datetime.datetime.now()}")
        
        # 1. Collect raw job listings from all sources
        raw_jobs = []
        for source in self.job_sources:
            try:
                jobs = source.search()
                raw_jobs.extend(jobs)
                print(f"Retrieved {len(jobs)} jobs from {source.__class__.__name__}")
            except Exception as e:
                print(f"Error retrieving jobs from {source.__class__.__name__}: {e}")
        
        # 2. Process and filter jobs
        matching_jobs = self.matcher.process_jobs(raw_jobs)
        print(f"Found {len(matching_jobs)} matching jobs after processing")
        
        # 3. Store new jobs
        new_jobs = []
        for job in matching_jobs:
            job_id = job["url"]  # Using URL as a unique identifier
            if job_id not in self.job_database:
                self.job_database[job_id] = job
                new_jobs.append(job)
        
        return new_jobs


# Allow running as script or importing as module
if __name__ == "__main__":
    agent = JobSearchAgent()
    jobs = agent.run_job_search()
    print(jobs)
    json.dump(jobs, open("jobs.json", "w"))