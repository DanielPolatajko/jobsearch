from typing import List, Dict, Any
import openai
import logging
import json

class JobMatcher:
    """Processes raw job listings and matches them to candidate profile"""
    
    def __init__(self, candidate_profile: Dict[str, Any], 
                 candidate_interests: List[str],
                 openai_api_key: str = None):
        self.candidate_profile = candidate_profile
        self.candidate_interests = candidate_interests
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set up OpenAI if API key provided
        if openai_api_key:
            openai.api_key = openai_api_key
    
    def process_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw job listings and return matches"""
        
        # Fetch full details for jobs that only have partial information
        enriched_jobs = self._enrich_job_details(raw_jobs)
        
        # Check potential matches based on keywords and basic criteria
        potential_matches = self._filter_basic_criteria(enriched_jobs)
        
        # Use AI to rank jobs based on fit with candidate profile
        ranked_jobs = self._rank_jobs_with_ai(potential_matches)
        
        # Return top matches
        return ranked_jobs
    
    def _enrich_job_details(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich job listings with full details if needed"""
        enriched_jobs = []
        
        for job in raw_jobs:
            # Skip jobs that already have good descriptions
            if len(job.get("description", "")) > 200:
                enriched_jobs.append(job)
                continue
                
            # For jobs with minimal descriptions, try to fetch more
            # Note: Implementation would depend on job source
            # This is a simplified placeholder
            try:
                if job["url"] and job["source"] == "LinkedInScraper":
                    # Example: could implement fetching full LinkedIn job description
                    # job = self._fetch_linkedin_details(job)
                    pass
                    
            except Exception as e:
                self.logger.error(f"Error enriching job details: {e}")
            
            enriched_jobs.append(job)
            
        return enriched_jobs
    
    def _filter_basic_criteria(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic filtering criteria"""
        matches = []
        
        # Extract requirements from candidate profile
        experience_years = self.candidate_profile.get("years_experience", 0)
        skills = self.candidate_profile.get("skills", [])
        education = self.candidate_profile.get("education", {})
        
        for job in jobs:
            score = 0
            reasons = []
            
            # Check for interest matches
            for interest in self.candidate_interests:
                if interest.lower() in job["title"].lower() or interest.lower() in job["description"].lower():
                    score += 2
                    reasons.append(f"Matches interest: {interest}")
            
            # Check for skill matches
            for skill in skills:
                if skill.lower() in job["description"].lower():
                    score += 1
                    reasons.append(f"Matches skill: {skill}")
            
            # Add job if it has a reasonable match score
            if score >= 2:
                job["initial_match_score"] = score
                job["match_reasons"] = reasons
                matches.append(job)
        
        return matches
    
    def _rank_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to analyze and rank jobs based on candidate fit"""
        if not jobs:
            return []
            
        try:
            # Create AI-ready data
            profile_json = json.dumps(self.candidate_profile, indent=2)
            interests_json = json.dumps(self.candidate_interests, indent=2)
            
            ranked_jobs = []
            
            for job in jobs:
                try:
                    # Prepare prompt for AI
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
                    - Description: {job['description'][:1000]}...
                    
                    ### Analysis Instructions:
                    1. Evaluate how well this job matches the candidate's experience and skills (scale 1-10)
                    2. Evaluate how well this job matches the candidate's interests (scale 1-10)
                    3. Determine whether the candidate would likely receive a first-round interview based on qualifications
                    4. Provide 2-3 key reasons why this job is a good match or not
                    
                    ### Output Format:
                    Return a JSON with the following structure:
                    ```json
                    {
                        "experience_match_score": 0-10,
                        "interest_match_score": 0-10,
                        "interview_probability": 0-10,
                        "overall_score": 0-10,
                        "match_reasons": ["reason1", "reason2"],
                        "summary": "One sentence summary of fit"
                    }
                    ```
                    """
                    
                    # Call AI API
                    response = openai.ChatCompletion.create(
                        model="gpt-4",  # Use appropriate model
                        messages=[
                            {"role": "system", "content": "You are a job matching assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.5,
                        max_tokens=800
                    )
                    
                    # Parse AI response
                    ai_text = response.choices[0].message.content
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
                    
                    ai_analysis = json.loads(ai_json_str)
                    
                    # Add AI analysis to job
                    job.update(ai_analysis)
                    ranked_jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing job with AI: {e}")
                    # Still include the job with a note about the error
                    job["ai_analysis_error"] = str(e)
                    ranked_jobs.append(job)
            
            # Sort by overall score (descending)
            ranked_jobs.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            return ranked_jobs
            
        except Exception as e:
            self.logger.error(f"Error in AI ranking process: {e}")
            # Return original jobs if AI ranking fails
            return jobs