from typing import List, Dict, Any
import json
import os
import logging
import groq
from jobsearch.job_matcher.base import BaseJobMatcher
from tqdm import tqdm

class GroqJobMatcher(BaseJobMatcher):
    """
    Job matcher implementation using Groq's API (free tier).
    Groq offers high performance LLM inference with a generous free tier.
    """
    
    def __init__(self, candidate_profile: Dict[str, Any],
                 candidate_interests: List[str],
                 api_key: str | None = None,
                 model: str = "llama3-8b-8192"):
        """
        Initialize the Groq job matcher
        
        Args:
            candidate_profile: Dictionary containing candidate profile information
            candidate_interests: List of candidate interests as strings
            api_key: Groq API key (if None, will look for GROQ_API_KEY environment variable)
            model: Groq model to use (default: llama3-8b-8192)
                Available models: llama3-8b-8192, llama3-70b-8192, mixtral-8x7b-32768, gemma-7b-it
        """
        super().__init__(candidate_profile, candidate_interests)
        
        # Get API key from environment variable if not provided
        if api_key is None:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key is None:
                raise ValueError("No API key provided and GROQ_API_KEY environment variable not found")
                
        self.api_key = api_key
        self.model = model
        # Initialize the Groq client
        self.client = groq.Client(api_key=api_key)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _rank_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Groq's API to analyze and rank jobs based on candidate fit"""
        if not jobs:
            return []
            
        try:
            ranked_jobs = []
            
            for job in tqdm(jobs):
                try:
                    # Prepare prompt for the model
                    base_prompt = self._prepare_analysis_prompt(job)
                    
                    # Call the Groq API using the client
                    self.logger.info(f"Sending request to Groq API for job: {job['title']}")
                    
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system", 
                                "content": "You are a job matching assistant specialized in evaluating job fit for candidates."
                            },
                            {
                                "role": "user", 
                                "content": base_prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=1024
                    )
                    
                    # Extract text from response
                    ai_text = response.choices[0].message.content
                    
                    # Extract the JSON from the response text
                    ai_analysis = self._extract_json_from_llm_response(ai_text)
                    
                    # Add AI analysis to job
                    job.update(ai_analysis)
                    ranked_jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing job with Groq: {e}")
                    # Still include the job with a note about the error
                    job["ai_analysis_error"] = str(e)
                    ranked_jobs.append(job)
            
            # Sort by overall score (descending)
            ranked_jobs.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            return ranked_jobs
            
        except Exception as e:
            self.logger.error(f"Error in Groq ranking process: {e}")
            # Return original jobs if ranking fails
            return jobs 