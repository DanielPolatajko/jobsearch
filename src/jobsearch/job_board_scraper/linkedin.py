from bs4 import BeautifulSoup
import requests
import time
from typing import List, Dict, Any, Optional
from jobsearch.job_board_scraper.base import JobScraper

class LinkedInScraper(JobScraper):
    """Scrapes LinkedIn for job postings"""
    
    def __init__(self, keywords: List[str], locations: Optional[List[str]] = None):
        super().__init__(keywords)
        self.locations = locations or []
    
    def search(self, limit: int = 10) -> List[Dict[str, Any]]:
        jobs = []
        
        # If no locations provided, perform search with just keywords
        search_combinations = []
        if not self.locations:
            search_combinations = [(keyword, None) for keyword in self.keywords]
        else:
            # Create combinations of keywords and locations
            for keyword in self.keywords:
                for location in self.locations:
                    search_combinations.append((keyword, location))
        
        for keyword, location in search_combinations:
            location_text = f" in {location}" if location else ""
            self.logger.info(f"Searching LinkedIn for: {keyword}{location_text}")
            
            try:
                # Build search URL (LinkedIn's public jobs page)
                search_term = keyword.replace(" ", "%20")
                url = f"https://www.linkedin.com/jobs/search/?keywords={search_term}"
                
                # Add location parameter if provided
                if location:
                    location_param = location.replace(" ", "%20")
                    url += f"&location={location_param}"
                
                # Make request
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"Failed to fetch LinkedIn jobs: {response.status_code}")
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.select(".job-search-card")
                
                for card in job_cards:
                    try:
                        title_elem = card.select_one(".base-search-card__title")
                        company_elem = card.select_one(".base-search-card__subtitle")
                        location_elem = card.select_one(".job-search-card__location")
                        link_elem = card.select_one("a.base-card__full-link")
                        
                        job = {
                            "title": title_elem.text.strip() if title_elem else "",
                            "company": company_elem.text.strip() if company_elem else "",
                            "location": location_elem.text.strip() if location_elem else "",
                            "url": link_elem.get("href") if link_elem else "",
                            "description": "",  # Need to fetch job page for description
                        }
                        
                        # Only add if we have minimum viable information
                        if job["title"] and job["url"]:
                            jobs.append(self._standardize_job(job))
                    except Exception as e:
                        self.logger.error(f"Error parsing job card: {e}")
                
                # Add delay to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error in LinkedIn search: {e}")
        
        # Remove duplicates by URL
        unique_jobs = []
        seen_urls = set()
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        return unique_jobs[:limit]