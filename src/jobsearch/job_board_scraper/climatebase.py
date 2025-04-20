from bs4 import BeautifulSoup
import requests
import time
from typing import List, Dict, Any
from jobsearch.job_board_scraper.base import JobDetails

class ClimatebaseScraper(JobDetails):
    """Scrapes Climatebase for climate-related jobs"""
    
    def search(self) -> List[Dict[str, Any]]:
        jobs = []
        
        for keyword in self.keywords:
            self.logger.info(f"Searching Climatebase for: {keyword}")
            
            try:
                # Build search URL
                search_term = keyword.replace(" ", "+")
                url = f"https://climatebase.org/jobs?l=&q={search_term}&p=0&remote=false"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"Failed to fetch Climatebase jobs: {response.status_code}")
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.select(".job-card")
                
                for card in job_cards:
                    try:
                        title_elem = card.select_one(".job-title")
                        company_elem = card.select_one(".organization-name")
                        location_elem = card.select_one(".job-location")
                        link_elem = card.select_one("a.job-card-link")
                        
                        # Get partial description if available
                        desc_elem = card.select_one(".job-description-preview")
                        
                        job = {
                            "title": title_elem.text.strip() if title_elem else "",
                            "company": company_elem.text.strip() if company_elem else "",
                            "location": location_elem.text.strip() if location_elem else "",
                            "url": "https://climatebase.org" + link_elem.get("href") if link_elem else "",
                            "description": desc_elem.text.strip() if desc_elem else "",
                        }
                        
                        if job["title"] and job["url"]:
                            jobs.append(self._standardize_job(job))
                    except Exception as e:
                        self.logger.error(f"Error parsing Climatebase job card: {e}")
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error in Climatebase search: {e}")
        
        return jobs