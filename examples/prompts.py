SIMPLE_FILE_CREATION_PROMPT = (
    "Write exactly 'Secret Code 789' to a file named 'secret.txt'. Do not include any other text, headers, or explanations inside the file.",
)

PYTHON_PROJECT_PROMPT = (
    """
Generate the complete structure of a Python project named 'pynguino' designed to log and process data from an external API.

Technical Constraints:
- NO real logic implementation. All functions and classes MUST be skeletons (placeholders) using 'pass' or default return values (e.g., return [], return None).
- All Python files must include full Type Hinting (Python 3.10+) and descriptive docstrings.
- Adhere strictly to PEP 8 naming conventions and package structure.

Required Deliverables:
1. Folder Structure: Displayed in a clear text tree format.
2. pyproject.toml: Base configuration using Poetry, including numpy, requests, and pandas as dependencies.
3. requirements.txt: Standard dependency list (numpy, requests, pandas).
4. tests/: A directory containing 'test_core.py' with at least two base test cases using pytest.
5. pynguino/: Main package (including __init__.py) with the following modules:
   - api.py: An 'APIClient' class with placeholder methods for authentication and data fetching.
   - core.py: Main orchestration and logging logic.
   - utils.py: Utility functions for ISO date formatting and string sanitization.

Output Format:
Display the directory tree first, followed by the content of each file. Each file must be clearly labeled with its full relative path and wrapped in Markdown code blocks.
""".strip(),
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
