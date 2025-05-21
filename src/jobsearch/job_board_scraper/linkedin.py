from bs4 import BeautifulSoup
import requests
import time
from typing import List, Dict, Any, Optional
from jobsearch.job_board_scraper.base import JobScraper
from jobsearch.job_board_scraper.models import (
    LinkedInJobSearchParameters,
    LinkedInExperienceLevel,
    LinkedInIndustry,
    LinkedInJobType,
)
import urllib.parse
import random
from langchain_core.tools import StructuredTool
from tqdm import tqdm
import json


class LinkedInScraper(JobScraper):
    """Scrapes LinkedIn for job postings"""

    def __init__(self, parameters: LinkedInJobSearchParameters):
        super().__init__([parameters.job_title])
        self.parameters = parameters
        # User agent list to rotate and avoid detection
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        ]

    def _query_builder(self, job_search_parameters: LinkedInJobSearchParameters) -> str:
        """Build a query string based on job search parameters"""
        query_parts = []

        if job_search_parameters.job_title:
            query_parts.append(
                f"keywords={urllib.parse.quote(job_search_parameters.job_title)}"
            )

        if job_search_parameters.location:
            query_parts.append(
                f"location={urllib.parse.quote(job_search_parameters.location)}"
            )

        if job_search_parameters.experience_level:
            query_parts.append(f"f_E={job_search_parameters.experience_level.value}")

        if job_search_parameters.industries:
            query_parts.append(
                f"f_I={'%2C'.join([str(industry.value) for industry in job_search_parameters.industries])}"
            )

        if (
            hasattr(job_search_parameters, "job_type")
            and job_search_parameters.job_type
        ):
            query_parts.append(f"f_JT={job_search_parameters.job_type}")

        return "&".join(query_parts)

    def _get_random_user_agent(self) -> str:
        """Return a random user agent from the list"""
        return random.choice(self.user_agents)

    def _fetch_job_description(self, job_url: str) -> str:
        """Fetch the detailed job description from the job page"""
        try:
            # Add delay before request to avoid rate limiting
            time.sleep(random.uniform(1.0, 3.0))

            # Make request with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
            }

            response = requests.get(job_url, headers=headers)

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to fetch job description: {response.status_code}"
                )
                return "Description not available"

            # Parse HTML and extract job description
            soup = BeautifulSoup(response.text, "html.parser")

            # LinkedIn typically has job descriptions in these sections
            description_div = soup.select_one("div.show-more-less-html__markup")

            if description_div:
                # Clean up the description
                desc_text = description_div.get_text(separator="\n", strip=True)
                return desc_text

            # Fallback to alternative selectors if the primary one doesn't work
            alternative_selectors = [
                "div.description__text",
                "section.description",
                # Add more potential selectors here as LinkedIn may change its structure
            ]

            for selector in alternative_selectors:
                alt_div = soup.select_one(selector)
                if alt_div:
                    return alt_div.get_text(separator="\n", strip=True)

            return "Description not available - could not locate on page"

        except Exception as e:
            self.logger.error(f"Error fetching job description: {e}")
            return f"Error fetching description: {str(e)}"

    def search(self, limit: int = 10) -> List[Dict[str, Any]]:
        jobs = []

        self.logger.info(f"Searching LinkedIn with parameters: {self.parameters}")

        try:
            # Build search URL (LinkedIn's public jobs page)
            query_string = self._query_builder(self.parameters)
            url = f"https://www.linkedin.com/jobs/search/?{query_string}"

            self.logger.info(f"Using URL: {url}")

            # Make request with random user agent
            headers = {"User-Agent": self._get_random_user_agent()}
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to fetch LinkedIn jobs: {response.status_code}"
                )
                raise Exception(
                    f"Failed to fetch LinkedIn jobs: {response.status_code} + {response.text}"
                )

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.select(".job-search-card")

            self.logger.info(f"Found {len(job_cards)} job cards")

            job_count = 0

            for card in tqdm(job_cards):
                try:
                    title_elem = card.select_one(".base-search-card__title")
                    company_elem = card.select_one(".base-search-card__subtitle")
                    location_elem = card.select_one(".job-search-card__location")
                    link_elem = card.select_one("a.base-card__full-link")

                    # Get the job URL
                    job_url = link_elem.get("href") if link_elem else ""

                    job = {
                        "title": title_elem.text.strip() if title_elem else "",
                        "company": company_elem.text.strip() if company_elem else "",
                        "location": location_elem.text.strip() if location_elem else "",
                        "url": job_url,
                        "search_parameters": str(
                            self.parameters
                        ),  # Store the parameters used
                    }

                    # Only continue if we have the minimum viable information
                    if job["title"] and job["url"]:
                        # Fetch the detailed job description
                        self.logger.info(
                            f"Fetching description for: {job['title']} at {job['company']}"
                        )
                        job["description"] = self._fetch_job_description(job_url)

                        jobs.append(self._standardize_job(job))
                        job_count += 1

                    if job_count >= limit:
                        break

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


def linkedin_job_search_tool_callable(
    location: str,
    job_title: str,
    experience_level: int,
    industries: list[int],
    job_type: str,
) -> list[dict]:
    """
    Process LinkedIn job search with proper conversion of parameters.
    This handles both direct calls and calls via the LangChain tool.
    """
    # Convert raw values to enum instances
    try:
        # Convert experience_level to enum
        exp_level = experience_level
        if isinstance(experience_level, int):
            exp_level = LinkedInExperienceLevel(experience_level)

        # Convert industries to enum list
        ind_list = []
        for industry in industries:
            if isinstance(industry, int):
                ind_list.append(LinkedInIndustry(industry))
            else:
                ind_list.append(industry)

        # Convert job_type to enum
        j_type = job_type
        if isinstance(job_type, str):
            j_type = LinkedInJobType(job_type)

        # Create parameters object
        parameters = LinkedInJobSearchParameters(
            job_title=job_title,
            location=location,
            experience_level=exp_level,
            industries=ind_list,
            job_type=j_type,
        )

        # Create scraper and search
        scraper = LinkedInScraper(parameters)
        results = scraper.search()
        # Convert to simpler dict format for JSON serialization
        simplified_results = []
        for job in results:
            simplified_results.append(
                {
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "url": job["url"],
                    "description": job["description"][:500] + "..."
                    if len(job["description"]) > 500
                    else job["description"],
                }
            )
        return simplified_results

    except Exception as e:
        import traceback

        print(f"Error in LinkedIn job search tool: {e}")
        print(traceback.format_exc())
        return [{"error": f"Failed to search LinkedIn: {str(e)}"}]


linkedin_job_search_tool = StructuredTool(
    name="linkedin_job_search",
    description="""
    Tool to search for jobs on LinkedIn based on your specified criteria. You must provide all of the following parameters:
    
    - location: The location to search for jobs (e.g., "London, United Kingdom", "New York", "Remote")
    - job_title: The job title to search for (e.g., "Software Engineer", "Product Manager")
    - experience_level: The experience level required (use 3 for ASSOCIATE or 4 for MID_SENIOR)
    - industries: List of industry IDs to search in. Available industries are:
      * 3252: CLIMATE_DATA_AND_ANALYTICS
      * 86: ENVIRONMENTAL_SERVICES
    - job_type: The type of job. Use "F" for FULL_TIME
    
    Example input: 
    {
        "location": "London, United Kingdom",
        "job_title": "Product Manager",
        "experience_level": 4,
        "industries": [3252, 86],
        "job_type": "F"
    }
    """,
    func=linkedin_job_search_tool_callable,
    args_schema=LinkedInJobSearchParameters,
)
