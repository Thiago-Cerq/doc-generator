from textwrap import dedent
from langchain.agents import tool
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import os
import validators


class DocumentationToolset:

    # @tool
    # def docs_search(query: str) -> str:
    #     """"Search for documentation on web based on the query. Receives a well-written query to be asked on Google Search"""

    #     search_result = search(query, num_results=1)
    #     docs_url = next(search_result)

    #     documentation = DocumentationToolset._get_text_from_url(docs_url)

    #     return documentation

    @tool
    def docs_search(query: str) -> str:
        """Search for documentation on the web based on the query."""
        try:
            search_results = list(search(query, num_results=1))  

            if not search_results:
                return "No results found for the query."

            docs_url = search_results[0]  #

            if not validators.url(docs_url):
                return f"Invalid URL returned: {docs_url}"

            documentation = DocumentationToolset._get_text_from_url(docs_url)

            return documentation
        except Exception as e:
            return f"Error in docs_search: {str(e)}"
    

    def _get_text_from_url(url):
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            text = soup.get_text()

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text
        else:
            return f"Erro ao acessar a página: {response.status_code}"

    @tool
    def read_file(path: str) -> str:
        """Read a file from a given path and returns the content as a string"""

        file = open(path, "r")
        lines = file.readlines()
        content = ''.join(lines)

        return content
    
        """"Receives the content to be written to a file and the path where the file should be saved. Writes the content to a file and save it in the path."""
        
        file = open(path_to_save, 'w')
        file.writelines(content)
        file.close()


    def tools():
        return [
            DocumentationToolset.docs_search,
            DocumentationToolset.read_file,
        ]