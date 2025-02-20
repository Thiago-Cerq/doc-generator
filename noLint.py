import os 
from langchain_ollama import ChatOllama
from crewai import Agent, Task, Crew, Process
from crewai import Agent, LLM
from agents import CreatingDocsAgents 
from tasks import CreatingDocsTasks

os.environ['OPENAI_API_KEY'] = "NA"  

ollama = LLM(
    model="ollama/llama3.2:latest",
    base_url="http://localhost:11434"
)

def main():

    tasks = CreatingDocsTasks()
    agents = CreatingDocsAgents()

    create_documentation_agent = agents.create_documentation_agent()
    search_documentation_agent = agents.search_documentation_agent()

    code_path = "./dados/agente.py"
    draft_path = "./dados/index.md"

    search_documentation_task = tasks.search_documentation_task(search_documentation_agent, code_path, draft_path)
    create_documentation_task = tasks.create_documentation_task(create_documentation_agent, code_path, draft_path)

    create_documentation_task.context = [search_documentation_task]

    crew = Crew(
        agents=[create_documentation_agent, search_documentation_agent],
        tasks=[search_documentation_task, create_documentation_task]
    )

    result = crew.kickoff()
    
    file = open("output.md", "w")
    file.write(result.raw)
    file.close()

    file = open("new_main.py", "w")
    file.write(search_documentation_task.output.raw)
    file.close()

if __name__ == "__main__":
    main()
