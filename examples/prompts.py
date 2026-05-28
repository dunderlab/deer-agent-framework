SIMPLE_FILE_CREATION_PROMPT = (
    "Write exactly 'Secret Code 789' to a file named 'secret.txt'. Do not include any other text, headers, or explanations inside the file.",
)

PYTHON_PROJECT_PROMPT = (
    """
Generate the complete structure of a project named 'pynguino' designed to log data from an external API.
You must create the following files and directories with functional placeholder code:
	1.	pyproject.toml: Basic project configuration using Poetry or Setuptools.
	2.	requirements.txt: Must include numpy, requests, and pandas.
	3.	tests/: A directory with at least one placeholder test file using pytest or unittest.
	4.	pynguino/: Main module containing the following submodules (each in its own .py file with placeholder functions and type hinting):
•	core: Main logging logic.
•	utils: Utility functions (date formatting, string manipulation, etc.).
•	api: Connection or handling of external API data.
Please display the final folder structure as a text tree format and then the content of each file clearly labeled.
""",
)

SEQUENTIAL_FILE_EDITION_PROMPT = (
    """Create a file named example.py. Inside it, write a basic Python script that prints the message 'Hello world' to the console when executed. Make sure to include only the corresponding code without any additional explanations.""",
    """Take the example.py file you created in the previous step. Modify it to encapsulate the 'Hello world' print statement inside a function named main(). At the end of the file, add the standard if __name__ == '__main__': block to invoke the main() function. Return the full and updated content of the file.""",
    """
Modify the example.py file from the previous step once again. Refactor the main function to meet the following requirements:

1. Add a parameter named name to the main function with a default value of "world".
2. Change the print statement to greet dynamically using that parameter (e.g., 'Hello, {name}').
3. Add a brief docstring (documentation comment) inside the function explaining what it does.
4. Inside the if __name__ == '__main__': block, make sure to call the function twice consecutively: first without passing any arguments, and then passing your own name as a string (e.g., main("Agent")).

Return the full modified file.
""",
)
