from langchain.tools import BaseTool
from asyncio import run
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CrawlResult

from pydantic import BaseModel, Field
from typing import Type


class Crawl4AIToolInput(BaseModel):
    url: str = Field(description="The URL to crawl")


class Crawl4AITool(BaseTool):
    """
    Tool to crawl a webpage and return the content.
    """

    name: str = "crawl4ai"
    description: str = """
    Crawl a webpage and return the content.
    Useful if you need to get the content of a webpage given a URL.
    Example use cases include finding links on a page, or getting the content of a page to extract information.
    Input should be a valid URL.
    Note that this tool will return the entire content of the webpage in markdown format, as well as a list of links extracted from the webpage.
    You can use the links as an input to the tool again to crawl the links and get the content of the linked pages.
    """
    args_schema: Type[BaseModel] = Crawl4AIToolInput

    def _run(self, url: str) -> str:
        return run(self._arun(url))

    async def _arun(self, url: str) -> str:
        browser_config = BrowserConfig(
            headless=True,
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler_config = CrawlerRunConfig(
                only_text=True,
                exclude_internal_links=True,
            )
            result: CrawlResult = await crawler.arun(url, config=crawler_config)
            return f"""
            WEB PAGE IN MARKDOWN FORMAT:
            {result.markdown}

            LIST OF LINKS EXTRACTED FROM THE WEB PAGE:
            {result.links}
            """
