# main.py - The core orchestrator

import os
import json
import datetime
import dotenv
from jobsearch.job_board_scraper.linkedin import linkedin_job_search_tool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from jobsearch.orchestrator.prompts import BASE_PROMPT_TEMPLATE
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain import hub


class JobSearchAgent:
    def __init__(self, config_path: str = "config.json"):
        # Load configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)

        dotenv.load_dotenv()

        # Initialize components
        self.llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

        self.prompt = PromptTemplate(
            name="Job search agent base template",
            template=BASE_PROMPT_TEMPLATE,
            input_variables=["profile_json", "interests_json"],
        )

        self.react_prompt = hub.pull("jacob/tool-calling-agent")

        self.tools = [linkedin_job_search_tool]

        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.react_prompt,
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
        )

        self.job_database = {}  # Simple in-memory store, replace with proper DB

    def run_job_search(self):
        """Execute a complete job search cycle"""

        # Load job database from file
        if os.path.exists("job_database.json"):
            with open("job_database.json", "r") as f:
                self.job_database = json.load(f)

        print(f"Starting job search at {datetime.datetime.now()}")

        # Run the agent
        result = self.executor.invoke(
            {
                "input": self.prompt.format_prompt(
                    **{
                        "profile_json": self.config["candidate_profile"],
                        "interests_json": self.config["candidate_interests"],
                    }
                ),
                "{chat_history}": [],
            }
        )

        print(result)
        result = dict(result)

        # Write job database to file
        with open("job_database.json", "w") as f:
            json.dump(result, f)

        return result


# Allow running as script or importing as module
if __name__ == "__main__":
    agent = JobSearchAgent()
    jobs = agent.run_job_search()
    print(jobs)
    json.dump(jobs, open("jobs.json", "w"))
