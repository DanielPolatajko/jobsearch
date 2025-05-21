from typing import List, Dict, Any
from abc import ABC, abstractmethod
import logging
import json

class BaseJobMatcher(ABC):
    """Base class for job matcher implementations that use different LLM backends"""
    
    def __init__(self, candidate_profile: Dict[str, Any], 
                 candidate_interests: List[str]):
        self.candidate_profile = candidate_profile
        self.candidate_interests = candidate_interests
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw job listings and return matches"""
        
        # Check potential matches based on keywords and basic criteria
        potential_matches = self._filter_basic_criteria(raw_jobs)
        
        # Use AI to rank jobs based on fit with candidate profile
        ranked_jobs = self._rank_jobs_with_ai(potential_matches)
        
        # Return top matches
        return ranked_jobs
    
    def _filter_basic_criteria(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        TODO: basic filtering before resorting to AI
        """
        return jobs
    
    @abstractmethod
    def _rank_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use AI to analyze and rank jobs based on candidate fit.
        This method must be implemented by specific LLM client subclasses.
        """
        pass
    
    def _prepare_analysis_prompt(self, job: Dict[str, Any]) -> str:
        """Prepare the prompt for AI analysis"""
        profile_json = json.dumps(self.candidate_profile, indent=2)
        interests_json = json.dumps(self.candidate_interests, indent=2)
        
        prompt = f"""
        ## Task: Evaluate job fit for candidate
        
        ### Candidate Profile:
        ```json
        {profile_json}
        ```
        
        ### Candidate Interests:
        ```json
        {interests_json}
        ```
        
        ### Job Information:
        - Title: {job['title']}
        - Company: {job['company']}
        - Description: {job.get('description', 'No description provided')[:1000]}...
        
        ### Analysis Instructions:
        1. Evaluate how well this job matches the candidate's experience and skills (scale 1-10)
        2. Evaluate how well this job matches the candidate's interests (scale 1-10)
        3. Determine whether the candidate would likely receive a first-round interview based on qualifications
        4. Provide 2-3 key reasons why this job is a good match or not

        ### Additional Instructions:
        - You will be penalised for suggesting jobs that are not a good fit for the candidate, so be very strict in your assessment. Do not include jobs which are not a good fit in your output.
        
        ### Output Format:
        Return a JSON with the following structure:
        ```json
        {{
            "experience_match_score": 0-10,
            "interest_match_score": 0-10,
            "interview_probability": 0-10,
            "overall_score": 0-10,
            "match_reasons": ["reason1", "reason2"],
            "summary": "One sentence summary of fit"
        }}
        ```
        """
        return prompt
    
    def _extract_json_from_llm_response(self, ai_text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response text"""
        ai_json_str = ai_text.strip()
        
        # Extract JSON if it's wrapped in backticks
        if "```json" in ai_json_str:
            start = ai_json_str.find("```json") + 7
            end = ai_json_str.find("```", start)
            ai_json_str = ai_json_str[start:end].strip()
        elif "```" in ai_json_str:
            start = ai_json_str.find("```") + 3
            end = ai_json_str.find("```", start)
            ai_json_str = ai_json_str[start:end].strip()
        
        # Handle potential issues with JSON parsing
        try:
            return json.loads(ai_json_str)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON: {ai_json_str}")
            return {
                "experience_match_score": 0,
                "interest_match_score": 0,
                "interview_probability": 0,
                "overall_score": 0,
                "match_reasons": ["Error parsing AI response"],
                "summary": "Error in analysis"
            } 