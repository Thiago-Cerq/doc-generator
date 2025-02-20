from textwrap import dedent
from crewai import Task

class CreatingDocsTasks():

    def linting_task(self, agent, code_path):
        return Task(
            description=dedent(
                f"""
                    Read code in Python and refactor using programming best practices for Python Language.
                    Add comments to the code briefly but understandably explaning what each block of code is doing.

                    Path to code: {code_path}
                """
            ),
            expected_output=dedent(f"""
                                    Only the refactored code with comments. Should not add anything else to the output.
                                    """
            ),
            agent=agent,
            async_execution=True
        )
    
    def search_documentation_task(self, agent, code_path, draft_path):
        return Task(
            description=dedent(
                f"""
                    Search on the internet for documentation explaning about Python libraries and frameworks based on the code and a documentation draft, if needed.
                    It must receive as input the path to the code file and the path to the draft file
                     and create queries to google search to get the best documentation for the libraries
                    or specific functions that you need information for.

                    Code path: {code_path}
                    Draft path: {draft_path}
                """
            ),
            expected_output=dedent(f"""
                                    Summarized documentation text about the libraries that were queried point the most important points
                                    based on the queries. Plain text.
                                    """
            ),
            agent=agent,
            async_execution=True
        )
    
    def create_documentation_task(self, agent, code_path, draft_path):
        return Task(
            description=dedent(
                f"""
                    Create documentation for the following code based on the code itself, the documentation draft provided and the documentation
                    about the libraries used in the code, if needed.
                    This documentation must be comprehensive and detailed, explaning inputs, outputs, processes and the goal of every
                    function in the code.

                    Code path: {code_path}
                    Documentation draft: {draft_path}
                """
            ),
            expected_output=dedent(f"""
                                    Documentation text about the code provided. The generated text is going to be saved on a file, so do not
                                   add anything besides the documentation text.
                                    """
            ),
            agent=agent,
            async_execution=False
        )