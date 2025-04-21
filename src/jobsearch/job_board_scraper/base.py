from typing import List, Dict, Any
from abc import ABC, abstractmethod
import logging

class JobScraper(ABC):
    """Abstract base class for job details"""
    
    def __init__(self, keywords: List[str]):
        self.keywords = keywords
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def search(self) -> List[Dict[str, Any]]:
        """Search for jobs and return a list of job dictionaries"""
        pass
    
    def _standardize_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize job data format"""
        standard_job = {
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "location": job_data.get("location", ""),
            "description": job_data.get("description", ""),
            "url": job_data.get("url", ""),
            "salary": job_data.get("salary", "Not specified"),
            "date_posted": job_data.get("date_posted", ""),
            "source": self.__class__.__name__
        }
        return standard_job