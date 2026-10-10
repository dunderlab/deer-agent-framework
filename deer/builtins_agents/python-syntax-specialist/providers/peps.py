from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return
import urllib.request
import urllib.error


class PEPProvider(ToolProvider):

    @tool(modifies_state=False)
    def pep_inquiry(self, pep: int) -> Return(pep=int, content=str, message=str):
        """Fetch the raw text content of any Python Enhancement Proposal (PEP) directly from the official GitHub repository, bypassing local memory limitations."""
        url = f"https://raw.githubusercontent.com/python/peps/refs/heads/main/peps/pep-{str(pep).rjust(4, '0')}.rst"
        try:
            with urllib.request.urlopen(url) as response:
                html_content = response.read().decode("utf-8")
                return {
                    "pep": pep,
                    "content": html_content,
                    "message": "",
                }

        except urllib.error.HTTPError as e:
            return {
                "pep": pep,
                "content": "",
                "message": f"HTTP error occurred: {e.code} - {e.reason}",
            }
        except urllib.error.URLError as e:
            return {
                "pep": pep,
                "content": "",
                "message": f"Failed to reach the server: {e.reason}",
            }
        except Exception as e:
            return {
                "pep": pep,
                "content": "",
                "message": f"An unexpected error occurred: {e}",
            }
