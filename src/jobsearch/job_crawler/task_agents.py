from jobsearch.job_crawler.tools import Crawl4AITool
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
import os
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.output_parsers import PydanticOutputParser
from jobsearch.job_crawler.models import CareersPageResult, JobListingsResult
from pathlib import Path
from pydantic import BaseModel


class CrawlerAgent:
    """
    Base class for agents which use a single web crawling tool to perform a contained task
    """

    def __init__(
        self,
        prompt_path: Path,
        output_model: BaseModel,
    ):
        self.parser = PydanticOutputParser(pydantic_object=output_model)
        self.tools = [Crawl4AITool()]
        self.llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
        )
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_template),
                ("user", "{input}"),
            ]
        ).partial(
            format_instructions=self.parser.get_format_instructions(),
        )

        self.agent = create_tool_calling_agent(
            self.llm,
            self.tools,
            prompt=self.prompt,
        )
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=False,
            max_iterations=3,
            handle_parsing_errors=True,
        )


class CareersPageFinderAgent(CrawlerAgent):
    """
    A single purpose agent that finds the careers page for a company, given a company homepage URL.
    """

    def __init__(self):
        super().__init__(
            prompt_path=Path(
                os.path.join(
                    os.path.dirname(__file__), "prompts/careers_page_finder_prompt.txt"
                )
            ),
            output_model=CareersPageResult,
        )

    def find_careers_page(self, url: str) -> CareersPageResult:
        """
        Find the careers page for a company.
        """
        response = self.agent_executor.invoke(
            {
                "input": f"""
                Your task is to find the careers page URL for a given company homepage URL: {url}.
                """
            }
        )
        outcome = response["output"]
        if isinstance(outcome, CareersPageResult):
            return outcome.get_result()
        else:
            if outcome == "Agent stopped due to max iterations.":
                return "NO_CAREERS_PAGE_FOUND"
            else:
                raise ValueError(f"Unexpected outcome: {outcome}")


class JobInfoExtractorAgent(CrawlerAgent):
    """
    A single purpose agent that finds the job listings for a company, given a careers page URL.
    """

    def __init__(self):
        super().__init__(
            prompt_path=Path(
                os.path.join(
                    os.path.dirname(__file__), "prompts/job_info_extractor_prompt.txt"
                )
            ),
            output_model=JobListingsResult,
        )

    def extract_job_info(
        self, url: str, job_titles: list[str] | None = None
    ) -> JobListingsResult:
        """
        Extract job info from a company's careers page.
        """
        response = self.agent_executor.invoke(
            {
                "input": f"""
                Your task is to extract job info from a company's careers page: {url}.
                """,
                "job_titles": job_titles,
            }
        )

        outcome = response["output"]
        if isinstance(outcome, JobListingsResult):
            return outcome
        else:
            if outcome == "Agent stopped due to max iterations.":
                return JobListingsResult(job_listings=[])
            else:
                raise ValueError(f"Unexpected outcome: {outcome}")
