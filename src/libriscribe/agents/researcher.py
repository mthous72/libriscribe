# src/libriscribe/agents/researcher.py
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils import prompts_context as prompts
from libriscribe.utils.file_utils import write_markdown_file
from libriscribe.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ResearcherAgent(Agent):
    """Conducts web research."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("ResearcherAgent", llm_client, event_callback)

    def execute(self, query: str, output_path: str) -> None:
        """Performs web research and saves the results to a Markdown file."""
        try:
            from libriscribe.knowledge_base import ProjectKnowledgeBase

            output_file = Path(output_path)
            project_dir = output_file.parent
            project_data_path = project_dir / "project_data.json"
            language = "English"

            if project_data_path.exists():
                try:
                    project_kb = ProjectKnowledgeBase.load_from_file(str(project_data_path))
                    if project_kb and hasattr(project_kb, 'language'):
                        language = project_kb.language
                except Exception as e:
                    self.logger.warning(f"Could not load project data for language detection: {e}")

            self.emit("log", {"level": "info", "message": f"Researching: {query}..."})
            prompt = prompts.RESEARCH_PROMPT.format(query=query, language=language)
            llm_summary = self.llm_client.generate_content(prompt, max_tokens=1000)

            search_results = self.scrape_google_search(query)
            scraped_content = ""
            for result in search_results:
                scraped_content += f"### [{result['title']}]({result['url']})\n\n"
                scraped_content += f"{result['snippet']}\n\n"

            final_report = f"# Research Report: {query}\n\n## AI-Generated Summary\n\n{llm_summary}\n\n## Web Search Results\n\n{scraped_content}"
            write_markdown_file(output_path, final_report)

        except Exception as e:
            self.logger.exception(f"Error during research for query '{query}': {e}")
            self.emit("log", {"level": "error", "message": f"Failed to perform research for '{query}': {e}"})

    def scrape_google_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Scrapes Google Search results for a given query."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            url = f"https://www.google.com/search?q={query}&num={num_results}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for g in soup.find_all('div', class_='tF2Cxc'):
                try:
                    anchor = g.find('a')
                    link = anchor['href']
                    title = g.find('h3').text
                    snippet = g.find('div', class_='VwiC3b').text
                    results.append({'title': title, 'url': link, 'snippet': snippet})
                except Exception as e:
                    self.logger.warning(f"Error parsing a search result: {e}")
                    continue

            return results
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during Google Search scraping: {e}")
            return []
        except Exception as e:
             self.logger.exception(f"An unexpected error occurred during google scraping {e}")
             return []
