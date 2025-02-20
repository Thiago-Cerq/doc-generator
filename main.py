from dotenv import load_dotenv
import os
import google.generativeai as genai
from langchain_ollama import ChatOllama
from crewai import Agent, Task, Crew, Process
from agents import CreatingDocsAgents
from tasks import CreatingDocsTasks
from langchain_google_genai import ChatGoogleGenerativeAI
from litellm import completion
from crewai import Agent, LLM


load_dotenv()


ollama = LLM(
    model="ollama/llama3.3:latest",
    base_url="http://localhost:8000",
)




def main():
    tasks = CreatingDocsTasks()
    agents = CreatingDocsAgents()

    linting_agent = agents.linting_agent()
    create_documentation_agent = agents.create_documentation_agent()
    search_documentation_agent = agents.search_documentation_agent()

    code_path = "./dados/agente.py"
    draft_path = "./dados/index.md"

    linting_task = tasks.linting_task(linting_agent, code_path)
    search_documentation_task = tasks.search_documentation_task(search_documentation_agent, code_path, draft_path)
    create_documentation_task = tasks.create_documentation_task(create_documentation_agent, code_path, draft_path)

    create_documentation_task.context = [linting_task, search_documentation_task]

    crew = Crew(
        agents=[linting_agent, create_documentation_agent, search_documentation_agent],
        tasks=[linting_task, search_documentation_task, create_documentation_task]
    )

    result = crew.kickoff()

    with open("output.md", "w") as file:
        file.write(result.raw)

    with open("new_main.py", "w") as file:
        file.write(linting_task.output.raw)

if __name__ == "__main__":
    main()
