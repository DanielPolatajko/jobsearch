from typing import List, Dict, Any
import requests
import json
from jobsearch.job_matcher.base import BaseJobMatcher

class HuggingFaceJobMatcher(BaseJobMatcher):
    """Job matcher implementation using Hugging Face's Inference API (free tier)"""
    
    def __init__(self, candidate_profile: Dict[str, Any],
                 candidate_interests: List[str],
                 api_key: str = "",
                 model: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        """
        Initialize the Hugging Face job matcher
        
        Args:
            candidate_profile: Dictionary containing candidate profile information
            candidate_interests: List of candidate interests as strings
            api_key: Hugging Face API token (optional for some models)
            model: Hugging Face model to use (default: mistralai/Mistral-7B-Instruct-v0.2)
        """
        super().__init__(candidate_profile, candidate_interests)
        self.api_key = api_key
        self.model = model
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
    
    def _rank_jobs_with_ai(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Hugging Face's Inference API to analyze and rank jobs based on candidate fit"""
        if not jobs:
            return []
            
        try:
            ranked_jobs = []
            
            for job in jobs:
                try:
                    # Prepare prompt for the model
                    prompt = self._format_prompt_for_model(job)
                    
                    # Call Hugging Face API
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    # Add authorization if API key is provided
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    # Prepare the payload based on the model
                    if "mistral" in self.model.lower():
                        payload = self._prepare_mistral_payload(prompt)
                    elif "llama" in self.model.lower():
                        payload = self._prepare_llama_payload(prompt)
                    else:
                        payload = self._prepare_default_payload(prompt)
                    
                    # Make the API request
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Hugging Face API error: {response.status_code} {response.text}")
                    
                    # Parse response based on model
                    response_data = response.json()
                    ai_text = self._extract_text_from_response(response_data)
                    ai_analysis = self._extract_json_from_llm_response(ai_text)
                    
                    # Add AI analysis to job
                    job.update(ai_analysis)
                    ranked_jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing job with Hugging Face: {e}")
                    # Still include the job with a note about the error
                    job["ai_analysis_error"] = str(e)
                    ranked_jobs.append(job)
            
            # Sort by overall score (descending)
            ranked_jobs.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            return ranked_jobs
            
        except Exception as e:
            self.logger.error(f"Error in Hugging Face ranking process: {e}")
            # Return original jobs if ranking fails
            return jobs
    
    def _format_prompt_for_model(self, job: Dict[str, Any]) -> str:
        """Format the prompt based on the model being used"""
        base_prompt = self._prepare_analysis_prompt(job)
        
        # Format for Mistral models
        if "mistral" in self.model.lower():
            formatted_prompt = f"<s>[INST] {base_prompt} [/INST]"
        # Format for Llama models
        elif "llama" in self.model.lower():
            formatted_prompt = f"<s>[INST] {base_prompt} [/INST]"
        # Default format for other models
        else:
            formatted_prompt = base_prompt
            
        return formatted_prompt
    
    def _prepare_mistral_payload(self, prompt: str) -> Dict[str, Any]:
        """Prepare payload for Mistral models"""
        return {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.5,
                "return_full_text": False
            }
        }
    
    def _prepare_llama_payload(self, prompt: str) -> Dict[str, Any]:
        """Prepare payload for Llama models"""
        return {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.5,
                "return_full_text": False
            }
        }
    
    def _prepare_default_payload(self, prompt: str) -> Dict[str, Any]:
        """Prepare default payload for other models"""
        return {
            "inputs": prompt,
            "parameters": {
                "max_length": 1024,
                "temperature": 0.5
            }
        }
    
    def _extract_text_from_response(self, response_data: Any) -> str:
        """Extract the text response from various Hugging Face model responses"""
        try:
            # List response format (common for many models)
            if isinstance(response_data, list) and len(response_data) > 0:
                if "generated_text" in response_data[0]:
                    return response_data[0]["generated_text"]
                elif isinstance(response_data[0], str):
                    return response_data[0]
            
            # Dict response format (some models)
            elif isinstance(response_data, dict):
                if "generated_text" in response_data:
                    return response_data["generated_text"]
            
            # String response (raw format)
            elif isinstance(response_data, str):
                return response_data
                
            # Unknown format - convert to string
            return str(response_data)
            
        except Exception as e:
            self.logger.error(f"Error extracting text from response: {e}")
            return "" 