from typing import List, Dict, Any
import requests
import json
from jobsearch.job_matcher.base import BaseJobMatcher

class ClaudeJobMatcher(BaseJobMatcher):
    """Job matcher implementation using Anthropic's Claude API"""
    
    def __init__(self, candidate_profile: Dict[str, Any],
                 candidate_interests: List[str],
                 api_key: str,
                 model: str = "claude-3-haiku-20240307"):
        """
        Initialize the Claude job matcher
        
        Args:
            candidate_profile: Dictionary containing candidate profile information
            candidate_interests: List of candidate interests as strings
            api_key: Anthropic API key
            model: Claude model to use (default: claude-3-haiku-20240307)
        """
        super().__init__(candidate_profile, candidate_interests)
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    def _rank_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Claude to analyze and rank jobs based on candidate fit"""
        if not jobs:
            return []
            
        try:
            ranked_jobs = []
            
            for job in jobs:
                try:
                    # Prepare prompt for Claude
                    prompt = self._prepare_analysis_prompt(job)
                    
                    # Call Claude API
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01"
                    }
                    
                    payload = {
                        "model": self.model,
                        "max_tokens": 1000,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "system": "You are a job matching assistant specialized in evaluating job fit for candidates."
                    }
                    
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Claude API error: {response.status_code} {response.text}")
                    
                    # Parse Claude response
                    response_data = response.json()
                    ai_text = response_data.get("content", [{}])[0].get("text", "")
                    ai_analysis = self._extract_json_from_llm_response(ai_text)
                    
                    # Add AI analysis to job
                    job.update(ai_analysis)
                    ranked_jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing job with Claude: {e}")
                    # Still include the job with a note about the error
                    job["ai_analysis_error"] = str(e)
                    ranked_jobs.append(job)
            
            # Sort by overall score (descending)
            ranked_jobs.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            return ranked_jobs
            
        except Exception as e:
            self.logger.error(f"Error in Claude ranking process: {e}")
            # Return original jobs if Claude ranking fails
            return jobs 