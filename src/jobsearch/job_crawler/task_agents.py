from .tools import Crawl4AITool
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.schema import AgentAction, AgentFinish
from langchain.agents.format_scratchpad.log import format_log_to_str
from langchain_core.tools.render import render_text_description
from langchain_core.tools import BaseTool
from typing import Sequence
import os


def find_tool_name(tools: Sequence[BaseTool], tool_name: str) -> BaseTool:
    for tool in tools:
        if tool.name == tool_name:
            return tool
    raise ValueError(f"Tool with name {tool_name} not found")


class CareersPageFinderAgent:
    def __init__(self):
        self.tools = [Crawl4AITool()]
        self.llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            stop=["\nObservation", "\nNO_CAREERS_PAGE_FOUND"],
        )
        self.prompt = PromptTemplate.from_file(
            os.path.join(
                os.path.dirname(__file__), "prompts/careers_page_finder_prompt.txt"
            ),
            input_variables=["tools", "tool_names", "agent_scratchpad", "input"],
        ).partial(
            tools=render_text_description(self.tools),
            tool_names=[t.name for t in self.tools],
        )

        self.agent = (
            {
                "input": lambda x: x.get("input"),
                "agent_scratchpad": lambda x: format_log_to_str(
                    x.get("agent_scratchpad")
                ),
            }
            | self.prompt
            | self.llm
            | ReActSingleInputOutputParser()
        )

    def find_careers_page(self, url: str) -> dict:
        """
        Find the careers page for a company.
        """
        intermediate_steps = []

        while True:
            response = self.agent.invoke(
                {
                    "input": f"""
                    Your task is to find the careers page URL for a given company homepage URL: {url}.
                    """,
                    "agent_scratchpad": intermediate_steps,
                }
            )

            if isinstance(response, AgentAction):
                tool_name = response.tool
                tool_input = response.tool_input
                tool_result = find_tool_name(self.tools, tool_name).invoke(tool_input)
                intermediate_steps.append((response, str(tool_result)))
            else:
                return response.return_values["output"]
