import asyncio
from typing import Any, Optional
import os
import logging
from datetime import datetime
import json
import re

from tavily import TavilyClient
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlResult,
    CrawlerRunConfig,
)

from dotenv import load_dotenv
from jobsearch.db.repository import (
    CompanyListPageRepository,
    SearchCacheRepository,
    CompanyRepository,
)

from jobsearch.job_crawler.task_agents import (
    CareersPageFinderAgent,
    JobInfoExtractorAgent,
)

# Fix the logger to use a proper name and configure handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CompanyCareerCrawler:
    """
    A class that:
    1. Searches for "best of" lists in a specific industry using Tavily
    2. Extracts company information from these lists using crawl4ai
    3. Finds company homepages
    4. Finds the careers pages from each company homepage
    5. Filters job listings by target roles
    """

    def __init__(
        self,
        industry: str,
        location: str | None = None,
        target_roles: str | list[str] | None = None,
        api_key: str | None = None,
        max_lists: int = 5,
    ):
        """
        Initialize the company career crawler.

        Args:
            industry: The industry to search for companies in
            location: The desired working location (city, state, country)
            target_roles: Target job roles/titles to filter for (e.g., "engineer", ["data scientist", "ML engineer"])
            api_key: Tavily API key (defaults to TAVILY_API_KEY env var)
            max_lists: Maximum number of "best of" lists to search for
        """
        self.industry = industry
        self.location = location

        # Convert target_roles to a set for easier lookup
        if target_roles:
            if isinstance(target_roles, str):
                self.target_roles = {target_roles.lower()}
            else:
                self.target_roles = {role.lower() for role in target_roles}
        else:
            self.target_roles = None

        self.max_lists = max_lists
        self.logger = logger

        # Set up Tavily client
        self.tavily_api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError(
                "Tavily API key is required. Set TAVILY_API_KEY environment variable or pass it as api_key"
            )
        self.tavily_client = TavilyClient(api_key=self.tavily_api_key)

        # Initialize results containers
        self.homepages = {}
        self.job_listings = {}

        self.company_repository = CompanyRepository()
        self.company_list_page_repository = CompanyListPageRepository()
        self.search_cache_repository = SearchCacheRepository()

        self.careers_page_finder_agent = CareersPageFinderAgent()
        self.job_info_extractor_agent = JobInfoExtractorAgent()

    def find_company_lists(self) -> list[dict[str, Any]]:
        """
        Search for "best of" list URLs for the specified industry using Tavily.
        If location is provided, search for location-specific lists.

        Returns:
            List of URLs to pages containing lists of top companies in the industry
        """
        location_str = f" in {self.location}" if self.location else ""
        self.logger.info(
            f"Searching for company lists in {self.industry} industry{location_str}"
        )

        try:
            # Different query variations to find "best of" lists
            queries = []

            # Create location-aware queries if location is provided
            if self.location:
                queries = [
                    f"best {self.industry} companies in {self.location}",
                    f"top {self.industry} companies {self.location} list",
                    f"leading {self.industry} companies in {self.location} {datetime.now().year}",
                    f"best {self.industry} startups in {self.location} to watch",
                    f"{self.location} {self.industry} market leaders list",
                ]
            else:
                queries = [
                    f"best companies in {self.industry} industry",
                    f"top {self.industry} companies list",
                    f"leading {self.industry} companies of {datetime.now().year}",
                    f"best {self.industry} startups to watch",
                    f"{self.industry} market leaders list",
                ]

            list_pages = []

            for query in queries:
                self.logger.info(f"Searching with query: {query}")

                response = self._tavily_search_with_cache(query)

                if response is None:
                    continue

                results = response.get("results", [])

                for result in results:
                    url = result.get("url", "")
                    title = result.get("title", "")

                    if (
                        self.company_list_page_repository.get_company_list_page_by_name_and_url(
                            title, url
                        )
                        is not None
                    ):
                        continue

                    # Check if this looks like a list page
                    # If location is specified, also check if title or URL contains location
                    if self._is_likely_list_page(title, url):
                        location_relevant = self._is_location_relevant(
                            title, url, self.location
                        )
                        list_page = {
                            "url": url,
                            "title": title,
                            "query": query,
                            "location_relevant": location_relevant,
                        }
                        list_pages.append(list_page)
                        self.company_list_page_repository.upsert_company_list_page(
                            title, url, query, location_relevant
                        )

            self.logger.info(f"Found {len(list_pages)} company list pages")
            return list_pages

        except Exception as e:
            self.logger.error(f"Error in Tavily company list search: {e}")
            return []

    def _tavily_search_with_cache(self, query: str) -> dict | None:
        search_cache = self.search_cache_repository.get_search_cache_by_query(query)
        if search_cache:
            self.logger.info(f"Search cache found for query: {query}")
            return None

        # Use Tavily search API to find company lists
        response = self.tavily_client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,  # We just need the URLs for now
            max_results=3,  # Limit results per query
        )

        self.search_cache_repository.create_search_cache(query, datetime.now())

        return response

    def _is_location_relevant(self, title: str, url: str, location: str) -> bool:
        """
        Check if a page is relevant to the specified location.

        Args:
            title: Page title
            url: Page URL
            location: Location to check relevance for

        Returns:
            True if the page is relevant to the location
        """
        # Normalize strings for comparison
        title_lower = title.lower()
        url_lower = url.lower()
        location_words = [w.strip(",") for w in location.lower().split()]

        # Check if location appears in title or URL
        if any(word in title_lower for word in location_words if len(word) > 2):
            return True

        if any(word in url_lower for word in location_words if len(word) > 2):
            return True

        # Check for common location patterns in URL
        location_patterns = [
            f"-in-{location.lower().replace(' ', '-')}",
            f"/{location.lower().replace(' ', '-')}",
        ]
        for pattern in location_patterns:
            if pattern in url_lower:
                return True

        # Check for some region-specific domains if location is a country
        country_tlds = {
            "united states": [".us", ".com"],
            "canada": [".ca"],
            "united kingdom": [".uk", ".co.uk"],
            "australia": [".au", ".com.au"],
            "germany": [".de"],
            "france": [".fr"],
            "india": [".in"],
            "japan": [".jp"],
            "china": [".cn"],
            "brazil": [".br"],
        }

        # Check if location matches any of our known countries
        for country, tlds in country_tlds.items():
            if country in location.lower():
                domain = self._extract_domain(url)
                if domain and any(domain.endswith(tld) for tld in tlds):
                    return True

        return False

    def extract_companies_from_lists(self) -> list[dict[str, Any]]:
        """
        Extract company information from the list URLs using crawl4ai.

        Returns:
            List of companies with their details
        """
        list_pages = self.company_list_page_repository.get_unscraped_company_list_pages(
            limit=self.max_lists
        )

        if not list_pages:
            self.logger.warning("No list URLs found. Run find_company_lists() first.")
            return []

        self.logger.info(f"Extracting companies from {len(list_pages)} list pages")

        try:
            for list_page in list_pages:
                url = list_page.url
                title = list_page.name

                self.logger.info(f"Crawling list page: {title}")

                # Create a crawler to extract the content of the list page
                documents = asyncio.run(self.crawl_webpage(url))

                self.company_list_page_repository.update_company_list_page_last_scraped(
                    list_page.id, last_scraped=datetime.now()
                )

                if not documents:
                    self.logger.warning(f"No content extracted from {url}")
                    continue

                # Process each document (typically just one for the page)
                for doc in documents:
                    content = doc.markdown
                    links = doc.links["external"]

                    links = [link["href"] for link in links]

                    # Extract company names and links from the content
                    companies_found = self._extract_companies_from_content(
                        content, links, title
                    )

                    # Add unique companies to our list
                    for company in companies_found:
                        self.company_repository.upsert_company(
                            company.get("name"),
                            company.get("homepage_url"),
                            None,
                            company.get("industry"),
                        )

            self.logger.info(
                f"Extracted {len(companies_found)} unique companies from list pages"
            )
            return companies_found

        except Exception as e:
            self.logger.error(f"Error extracting companies from lists: {e}")
            return []

    async def crawl_webpage(self, url: str) -> str:
        """
        Crawl a webpage and return the content.
        """
        browser_config = BrowserConfig(
            headless=True,
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler_config = CrawlerRunConfig(
                only_text=True,
                exclude_internal_links=True,
            )
            result: CrawlResult = await crawler.arun(url, config=crawler_config)
            return result

    def extract_homepages(self) -> dict[str, str]:
        """
        Extract homepage URLs for the found companies using crawl4ai.

        Returns:
            Dictionary mapping company names to their homepage URLs
        """
        companies_without_homepage_url = (
            self.company_repository.get_companies_with_no_urls(limit=self.max_lists)
        )

        max_searches = 5
        searches_used = 0
        try:
            for company in companies_without_homepage_url:
                company_name = company.name

                # If the company already has a homepage URL in its info, use that
                if company.homepage_url:
                    self.homepages[company_name] = company.homepage_url
                    self.logger.info(
                        f"Using provided homepage for {company_name}: {company.homepage_url}"
                    )
                    continue

                # Otherwise, search for the company homepage using Tavily
                # If location is specified, include it in the search
                location_str = f" {self.location}" if self.location else ""
                search_query = f"{company_name}{location_str} official website homepage"

                if searches_used >= max_searches:
                    self.logger.warning(
                        f"Max searches ({max_searches}) used. Skipping {company_name}"
                    )
                    continue

                response = self._tavily_search_with_cache(search_query)

                if response is None:
                    continue

                searches_used += 1

                results = response.get("results", [])

                # Find the most likely homepage URL from search results
                homepage_url = None
                for result in results:
                    url = result.get("url", "")

                    # Check if this URL looks like a company homepage
                    if self._is_likely_homepage(company_name, url):
                        homepage_url = url
                        break

                if homepage_url:
                    self.homepages[company_name] = homepage_url
                    self.logger.info(
                        f"Found homepage for {company_name}: {homepage_url}"
                    )
                    self.company_repository.update_company_homepage_url(
                        company.id, homepage_url
                    )
                else:
                    self.logger.warning(f"Could not find homepage for {company_name}")

            return self.homepages

        except Exception as e:
            self.logger.error(f"Error extracting homepages: {e}")
            return {}

    def find_career_pages(self) -> None:
        """
        Find career pages from the company homepages using an agent equipped with web crawling tools.
        """
        try:
            companies = self.company_repository.get_companies_with_homepage_url_but_no_careers_url(
                limit=self.max_lists
            )

            for company in companies:
                careers_page_url = self.careers_page_finder_agent.find_careers_page(
                    company.homepage_url
                )
                if careers_page_url == "NO_CAREERS_PAGE_FOUND":
                    self.logger.warning(
                        f"Could not find careers page for {company.name}"
                    )
                self.company_repository.update_company_careers_url(
                    company.id, careers_page_url
                )

        except Exception as e:
            self.logger.error(f"Error finding career pages: {e}")
            raise e

    def extract_job_listings(self) -> dict[str, list[dict[str, Any]]]:
        """
        Extract job listings from career pages and filter by target roles.

        Returns:
            Dictionary mapping company names to their job listings
        """
        try:
            careers_urls = self.company_repository.get_companies_with_careers_url(
                limit=self.max_lists
            )
            for company in careers_urls:
                job_listings = self.job_info_extractor_agent.extract_job_info(
                    company.careers_url, self.target_roles
                )
                # TODO: Save job listings to database

            return self.job_listings

        except Exception as e:
            self.logger.error(f"Error extracting job listings: {e}")
            return {}

    def _matches_target_role(self, job_title: str) -> bool:
        """
        Check if a job title matches any of the target roles.

        Args:
            job_title: The job title to check

        Returns:
            True if the job title matches any target role, or if no target roles are specified
        """
        if not self.target_roles:
            return True

        job_title_lower = job_title.lower()

        # Check for exact matches or substring matches
        for role in self.target_roles:
            # Split the role into words for matching
            role_words = role.split()

            # For multi-word roles, check if all words appear in the title
            if len(role_words) > 1:
                if all(word in job_title_lower for word in role_words):
                    return True
            # For single-word roles, check if it appears as a whole word
            elif re.search(r"\b" + re.escape(role) + r"\b", job_title_lower):
                return True

        return False

    def _extract_job_listings(
        self, content: str, links: list[str], page_url: str
    ) -> list[dict[str, Any]]:
        """
        Extract job listings from content and links.

        Args:
            content: The text content of the page
            links: List of links found on the page
            page_url: URL of the page being processed

        Returns:
            List of job listings with titles, locations, and URLs
        """
        job_listings = []

        # Extract job titles from links first (more reliable)
        job_link_patterns = [
            r"/careers?/.*/(.*?)\s*$",
            r"/jobs?/.*/(.*?)\s*$",
            r"/positions?/.*/(.*?)\s*$",
            r"/openings?/.*/(.*?)\s*$",
        ]

        base_url = "/".join(page_url.split("/")[:3])  # http(s)://domain.com

        # Process links to find job postings
        for link in links:
            link_lower = link.lower()

            # Handle relative links
            if link.startswith("/"):
                link = base_url + link

            # Check if this looks like a job posting link
            if any(
                kw in link_lower
                for kw in ["/job/", "/career", "/position", "/opening", "/apply"]
            ):
                # Extract job title from the URL if possible
                job_title = None

                for pattern in job_link_patterns:
                    match = re.search(pattern, link)
                    if match:
                        job_title = (
                            match.group(1).replace("-", " ").replace("_", " ").title()
                        )
                        break

                if not job_title:
                    # If title not found in URL, use the last part of the path
                    path_parts = link.split("/")
                    if len(path_parts) > 3:
                        job_title = (
                            path_parts[-1].replace("-", " ").replace("_", " ").title()
                        )

                # If still no title, use a generic one
                if not job_title or len(job_title) < 3:
                    job_title = "Job Opening"

                # Check if this job matches target roles, if specified
                if not self.target_roles or self._matches_target_role(job_title):
                    job = {
                        "title": job_title,
                        "url": link,
                        "source_url": page_url,
                    }

                    # Add location if specified
                    if self.location:
                        job["target_location"] = self.location

                    job_listings.append(job)

        # If no job listings found from links, try to extract from content
        if not job_listings:
            # Look for job titles in content
            job_title_patterns = [
                r"((?:Senior|Junior|Lead|Principal|Staff)?\s*(?:Software|Data|Machine Learning|ML|AI|Frontend|Backend|Fullstack|DevOps|Cloud|Product|Project|Program|Marketing|Sales|Business|UX|UI)?\s*(?:Engineer|Scientist|Developer|Manager|Designer|Analyst|Architect|Specialist|Director|VP)\s*(?:I|II|III|IV|V)?)",
                r"((?:Senior|Junior|Lead|Principal|Staff)?\s*(?:\w+)\s*(?:Engineer|Scientist|Developer|Manager|Designer|Analyst|Architect|Specialist|Director|VP)\s*(?:I|II|III|IV|V)?)",
            ]

            for pattern in job_title_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    job_title = match.strip()

                    # Check if this job matches target roles, if specified
                    if (
                        job_title
                        and len(job_title) > 5
                        and (
                            not self.target_roles
                            or self._matches_target_role(job_title)
                        )
                    ):
                        job = {
                            "title": job_title,
                            "url": page_url,  # Use the career page URL since we don't have a specific job URL
                            "source_url": page_url,
                            "extracted_from_content": True,
                        }

                        # Add location if specified
                        if self.location:
                            job["target_location"] = self.location

                        job_listings.append(job)

        # Deduplicate job listings by URL
        unique_jobs = {}
        for job in job_listings:
            if job["url"] not in unique_jobs:
                unique_jobs[job["url"]] = job

        return list(unique_jobs.values())

    def run_pipeline(self) -> dict[str, Any]:
        """
        Run the complete pipeline: find company lists, extract companies,
        extract homepages, find career pages, and extract job listings.

        Returns:
            Dictionary with all results
        """
        self.find_company_lists()
        self.extract_companies_from_lists()
        self.extract_homepages()
        self.find_career_pages()
        self.extract_job_listings()

        location_info = {"location": self.location} if self.location else {}
        role_info = (
            {"target_roles": list(self.target_roles)} if self.target_roles else {}
        )

        results = {
            "industry": self.industry,
            **location_info,
            **role_info,
            "company_lists": self.list_urls,
            "companies": self.companies,
            "homepages": self.homepages,
            "career_pages": self.career_pages,
            "job_listings": self.job_listings,
            "timestamp": datetime.now().isoformat(),
        }

        return results

    def save_results(self, filename: str = None) -> str:
        """
        Save the results to a JSON file.

        Args:
            filename: Name of the file to save to (default: industry_name_companies.json)

        Returns:
            Path to the saved file
        """
        if not filename:
            location_slug = (
                f"_{self.location.replace(' ', '_').lower()}" if self.location else ""
            )
            role_slug = ""
            if self.target_roles and len(self.target_roles) == 1:
                role = next(iter(self.target_roles))
                role_slug = f"_{role.replace(' ', '_').lower()}"

            filename = f"{self.industry.replace(' ', '_').lower()}{location_slug}{role_slug}_jobs.json"

        location_info = {"location": self.location} if self.location else {}
        role_info = (
            {"target_roles": list(self.target_roles)} if self.target_roles else {}
        )

        results = {
            "industry": self.industry,
            **location_info,
            **role_info,
            "company_lists": self.list_urls,
            "companies": self.companies,
            "homepages": self.homepages,
            "career_pages": self.career_pages,
            "job_listings": self.job_listings,
            "timestamp": datetime.now().isoformat(),
        }

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"Saved results to {filename}")
        return filename

    def _extract_companies_from_content(
        self, content: str, links: list[str], page_title: str
    ) -> list[dict[str, Any]]:
        """
        Extract company information from the content of a list page.

        Args:
            content: The text content of the page
            links: List of links found on the page
            page_title: Title of the list page

        Returns:
            List of company dictionaries with extracted information
        """
        companies = []

        # Look for common list markers and company patterns

        # 1. Try to find numbered lists (e.g., "1. Company Name")
        numbered_pattern = re.compile(r"(\d+)[\.:\)][\s]+([\w\s&\-\.,]+)")
        numbered_matches = numbered_pattern.findall(content)

        # 2. Try to find bold/header companies (rough approximation in plain text)
        section_pattern = re.compile(r"([A-Z][A-Za-z0-9\s&\-\.,]+)[\n\r]")
        section_matches = section_pattern.findall(content)

        # 3. Try to find links with company names
        company_links = []
        for link in links:
            domain = self._extract_domain(link)
            if domain:
                # Remove common non-company TLDs
                if not any(domain.endswith(tld) for tld in [".gov", ".edu", ".org"]):
                    company_name = self._domain_to_company_name(domain)
                    company_links.append((company_name, link))

        # Process and combine the results, starting with the most reliable sources

        # From numbered lists
        for number, name in numbered_matches:
            name = name.strip()
            if len(name) > 2 and len(name) < 50:  # Basic validation
                companies.append(
                    {
                        "name": name,
                        "source_list": page_title,
                        "list_rank": number,
                        "industry": self.industry,
                        "extraction_method": "numbered_list",
                    }
                )

        # From section headers
        for name in section_matches:
            name = name.strip()
            if (
                len(name) > 2
                and len(name) < 50
                and not any(c["name"] == name for c in companies)
            ):
                companies.append(
                    {
                        "name": name,
                        "source_list": page_title,
                        "industry": self.industry,
                        "extraction_method": "section_header",
                    }
                )

        # From links
        for name, link in company_links:
            if not any(c["name"].lower() == name.lower() for c in companies):
                companies.append(
                    {
                        "name": name,
                        "source_list": page_title,
                        "homepage_url": link,
                        "industry": self.industry,
                        "extraction_method": "link_analysis",
                    }
                )

        return companies

    def _is_likely_list_page(self, title: str, url: str) -> bool:
        """
        Check if a URL is likely to be a "best of" list page.

        Args:
            title: Page title
            url: Page URL

        Returns:
            True if the page appears to be a list page
        """
        title_lower = title.lower()
        url_lower = url.lower()

        # Keywords indicating a list page
        list_indicators = [
            "top",
            "best",
            "leading",
            "list",
            "companies",
            "startups",
            "businesses",
            "corporations",
            "rankings",
        ]

        # Check if the title contains list-like keywords
        if any(indicator in title_lower for indicator in list_indicators):
            if self.industry.lower() in title_lower:
                return True

        # Check for list-like URL patterns
        list_url_patterns = [
            "top-",
            "best-",
            "-list",
            "/list",
            "/top-",
            "/best-",
            "companies-to-watch",
            "rankings",
            "-companies",
        ]

        if any(pattern in url_lower for pattern in list_url_patterns):
            return True

        # Check for list-hosting websites
        list_hosting_sites = [
            "forbes.com",
            "techcrunch.com",
            "inc.com",
            "businessinsider.com",
            "fortune.com",
            "crunchbase.com",
        ]

        for site in list_hosting_sites:
            if site in url_lower:
                return True

        return False

    def _is_likely_homepage(self, company_name: str, url: str) -> bool:
        """
        Check if a URL is likely to be a company's homepage.

        Args:
            company_name: Name of the company
            url: URL to check

        Returns:
            True if the URL appears to be a company homepage
        """
        # Extract the domain from the URL
        domain = self._extract_domain(url)
        if not domain:
            return False

        # Convert company name to comparable format
        company_words = company_name.lower().split()

        # Check if domain contains company name words
        if any(word in domain.lower() for word in company_words if len(word) > 2):
            # Make sure it's not a subpage
            path = url.split(domain, 1)[-1]
            if path == "" or path == "/" or path.startswith("/?"):
                return True

        return False

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            # Handle URLs with or without protocol
            if "://" in url:
                domain = url.split("://", 1)[1].split("/", 1)[0]
            else:
                domain = url.split("/", 1)[0]

            return domain
        except:
            return None

    def _domain_to_company_name(self, domain: str) -> str:
        """Convert a domain to a company name"""
        # Remove TLD
        name = domain.split(".")[0]

        # Handle www prefix
        if name.startswith("www."):
            name = name[4:]

        # Convert hyphens to spaces
        name = name.replace("-", " ")

        # Capitalize words
        name = " ".join(word.capitalize() for word in name.split())

        return name


if __name__ == "__main__":
    load_dotenv()
    crawler = CompanyCareerCrawler(
        industry="climate tech",
        location="London, U.K.",
        target_roles=[
            "customer success manager",
            "partnerships manager",
            "account manager",
        ],
    )
    crawler.run_pipeline()
    crawler.save_results()
