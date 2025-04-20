#!/usr/bin/env python3
"""
Test script for the Groq job matcher implementation.
This script demonstrates how to use the Groq job matcher to evaluate job listings.

To run this script:
1. Create a .env file in the project root with GROQ_API_KEY=your_key
2. Run with: python -m test.test_job_matcher.scripts.test_groq_matcher
"""

import os
import json
import logging
from pprint import pprint
from pathlib import Path
from dotenv import load_dotenv

from jobsearch.job_matcher import GroqJobMatcher

# Load environment variables from .env file at the root level
# Find the project root directory (where the .env file should be)
project_root = Path(__file__).parent.parent.parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample candidate profile
CANDIDATE_PROFILE = {
    "name": "Alex Smith",
    "years_experience": 5,
    "skills": [
        "Python",
        "Machine Learning",
        "Data Science",
        "SQL",
        "Docker",
        "Git"
    ],
    "education": [
        {
            "degree": "MSc",
            "field": "Computer Science",
            "institution": "University of Technology",
            "year": 2019
        },
        {
            "degree": "BSc",
            "field": "Mathematics",
            "institution": "State University",
            "year": 2017
        }
    ],
    "desired_roles": [
        "Data Scientist",
        "Machine Learning Engineer",
        "AI Researcher"
    ],
    "desired_location": "Remote",
    "desired_salary": 120000
}

# Sample candidate interests
CANDIDATE_INTERESTS = [
    "Artificial Intelligence",
    "Sustainability",
    "Healthcare",
    "Climate Tech"
]

# Sample job listings
SAMPLE_JOBS = [
    {
        "title": "Senior Machine Learning Engineer",
        "company": "TechCorp",
        "location": "Remote",
        "description": """
        We're looking for a Senior ML Engineer with 5+ years of experience to join our team.
        
        Requirements:
        - Strong Python programming skills
        - Experience with machine learning frameworks (PyTorch, TensorFlow)
        - Experience deploying ML models to production
        - BS/MS/PhD in Computer Science, Mathematics, or related field
        
        Responsibilities:
        - Design and implement machine learning models for our product
        - Work with data scientists to optimize models and improve accuracy
        - Deploy and monitor models in production
        - Stay up-to-date with latest research in AI/ML
        
        We offer competitive salary and benefits.
        """,
        "url": "https://example.com/jobs/123",
        "source": "LinkedInScraper"
    },
    {
        "title": "Climate Data Scientist",
        "company": "GreenFuture",
        "location": "San Francisco, CA (Hybrid)",
        "description": """
        GreenFuture is a climate tech startup using AI to help companies reduce their carbon footprint.
        
        We're looking for a Data Scientist with:
        - 3+ years experience in data science
        - Strong Python skills
        - Experience with time series data
        - Passion for climate solutions
        - MS in Data Science, Statistics, or related field
        
        You'll be working on:
        - Analyzing climate data and energy usage patterns
        - Creating predictive models for energy consumption
        - Developing recommendations for carbon reduction
        
        Join us in making a difference!
        """,
        "url": "https://example.com/jobs/456",
        "source": "ClimatebaseScraper"
    },
    {
        "title": "Frontend Developer",
        "company": "WebSolutions",
        "location": "New York, NY",
        "description": """
        We need a skilled frontend developer with:
        - 3+ years experience with React and JavaScript
        - Experience with modern CSS and responsive design
        - Knowledge of frontend build tools
        
        The role focuses on building user interfaces for our web applications.
        """,
        "url": "https://example.com/jobs/789",
        "source": "GoogleJobSearcher"
    }
]

def main():
    """Run the Groq job matcher test"""
    print("Testing Groq Job Matcher")
    print("-" * 50)
    
    # Check if .env file exists
    if dotenv_path.exists():
        print(f"Loaded environment from: {dotenv_path}")
    else:
        print(f"No .env file found at: {dotenv_path}")
        print("API key will need to be set via environment variable or passed directly.")
    
    # Get API key from environment (loaded from .env if available)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable not found.")
        print("Please set it in your .env file or environment variables.")
        return
    
    # Initialize the job matcher with API key from .env
    job_matcher = GroqJobMatcher(
        candidate_profile=CANDIDATE_PROFILE,
        candidate_interests=CANDIDATE_INTERESTS,
        api_key=api_key
    )
    
    print(f"Initialized matcher for candidate: {CANDIDATE_PROFILE['name']}")
    print(f"Using Groq model: {job_matcher.model}")
    print("-" * 50)
    
    # Process jobs
    print("Processing job listings...")
    try:
        results = job_matcher.process_jobs(SAMPLE_JOBS)
        
        print(f"\nFound {len(results)} matching jobs:")
        
        # Print the results
        for i, job in enumerate(results, 1):
            print(f"\nJob {i}: {job['title']} at {job['company']}")
            print(f"Overall match score: {job.get('overall_score', 'N/A')}/10")
            
            # Print the detailed scores if available
            if 'experience_match_score' in job:
                print(f"Experience match: {job['experience_match_score']}/10")
            if 'interest_match_score' in job:
                print(f"Interest match: {job['interest_match_score']}/10")
            if 'interview_probability' in job:
                print(f"Interview probability: {job['interview_probability']}/10")
            
            # Print match reasons
            if 'match_reasons' in job:
                print("\nMatch reasons:")
                for reason in job['match_reasons']:
                    print(f"- {reason}")
            
            # Print summary
            if 'summary' in job:
                print(f"\nSummary: {job['summary']}")
            
            # Check for errors
            if 'ai_analysis_error' in job:
                print(f"\nError during analysis: {job['ai_analysis_error']}")
            
            print("-" * 50)
        
        # Save the results to a file in the project root
        results_path = project_root / 'test_results.json'
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {results_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 