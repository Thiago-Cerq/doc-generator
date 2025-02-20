from dotenv import load_dotenv
from textwrap import dedent
from crewai import Agent
from crewai import Agent, LLM
from tools import DocumentationToolset

load_dotenv()

ollama = LLM(
    model="ollama/llama3.3:latest",
    base_url="http://localhost:8000",
)


class CreatingDocsAgents():

    def linting_agent(self):
        return Agent(
            role="Linting Agent",
            goal=dedent("""Enhance code organization based on Python programming language best practices.
                            Comment the code explaning what each block of code is doing."""),
            tools=DocumentationToolset.tools(),
            backstory=dedent("""
                            You're a senior software engineer with 20 years of experience and 10 years of experience working with Python, so you are a
                             Python specialist. Your job is to read Python code and refactor it, making it more readable and pretty. Also, you have to
                             add comments to the code you are reading, explaining what each code block is doing. You refactorization is going to help
                             the company perform better and decrease the effort needed to work on legacy code.
                            """),
            verbose=True,
            llm=ollama
        )

    def search_documentation_agent(self):
        return Agent(
            role="Documentation Summarizer Specialist",
            goal=dedent("""Based on a Python code, you must gather the dependencies from the code and create queries to google search about those libraries.
                        When you have the documentation, you must summarize the most important points from the documentations."""),
            tools=DocumentationToolset.tools(),
            backstory=dedent("""
                            You're a senior software engineer with 20 years of experience. Your job is to summarize Python libraries and frameworks
                             documentation, extracting the most important points. Your summarization is going to be used to create documents for
                             our company's projects.
                            """),
            verbose=True,
            llm=ollama
        )

    def create_documentation_agent(self):
        return Agent(
            role="Documentation Writer Specialist",
            goal=dedent("""Create a code documentation from scratch based on the code, a documentation draft and dependencies' documentations"""),
            tools=DocumentationToolset.tools(),
            backstory=dedent("""
                            You're a senior software engineer with 20 years of experience and during all your career you've been responsible for writting
                             projects documentation, so you are a documentation writer specialist. Your job is to right the best documentation for a code
                             based on the code itself, the documentation of the libraries and frameworks used by the code and also a brief documentation draft
                             used as example.
                            """),
            verbose=True,
             llm=ollama
        )  