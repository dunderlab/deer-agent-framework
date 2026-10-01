import urllib.error
import urllib.request
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case

# NOTE: Intentionally untested: thin wrappers over urllib, they need a live server.


@dataclass
class HTTPClient(ToolProvider):

    @tool(
        tests=[
            # Test: Connection failure with an invalid domain
            # This validates that the 'Exception' block catches the failure and returns status 0
            Case(
                {"url": "http://this.domain.does.not.exist.test"},
                {"status": 0, "body": "", "message": str},
            ),
        ]
    )
    def http_request(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: str | None = None,
    ) -> Return(status=int, body=str, message=str):
        """Sends an HTTP request (GET, POST, PUT, DELETE...) to a URL and returns the response status and body text. HTTP error statuses (404, 500...) are returned normally, not as failures. Status 0 means the connection itself failed."""
        encoded_data = data.encode("utf-8") if data is not None else None

        req = urllib.request.Request(
            url, data=encoded_data, headers=headers or {}, method=method.upper()
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return {
                    "status": response.status,
                    "body": response.read().decode("utf-8", errors="replace"),
                    "message": "Request successful.",
                }
        except urllib.error.HTTPError as e:
            return {
                "status": e.code,
                "body": e.read().decode("utf-8", errors="replace"),
                "message": f"HTTP Error: {e.reason}",
            }
        except Exception as e:
            return {"status": 0, "body": "", "message": f"Connection Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"url": "http://127.0.0.1:1/x", "destination_path": "../outside.txt"},
                raises=Exception,
            )
        ],
    )
    def download_file(
        self, url: str, destination_path: str
    ) -> Return(success=bool, path=str, message=str):
        """Downloads a remote file into destination_path inside the jail, creating missing parent directories. OVERWRITES an existing file. Fails on connection errors and HTTP error statuses."""
        safe_path = self.jailed_path(
            destination_path
        )  # outside the try, like the other providers

        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, safe_path)
            return {
                "success": True,
                "path": destination_path,  # relative path: do not leak the jail location
                "message": f"File downloaded to {destination_path}",
            }
        except Exception as e:
            return {"success": False, "path": "", "message": f"Download failed: {e}"}

    @tool(
        tests=[
            # Test: URL unreachable
            Case(
                {"url": "http://this.domain.does.not.exist.test"},
                {"available": False, "status": 0, "message": str},
            ),
        ]
    )
    def check_url(self, url: str) -> Return(available=bool, status=int, message=str):
        """Sends a HEAD request to check whether a URL responds. 'available' is True whenever the server answers, even with an error status such as 404 or 500; it is False only if the connection fails."""
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return {
                    "available": True,
                    "status": response.status,
                    "message": "URL is reachable.",
                }
        except urllib.error.HTTPError as e:
            return {
                "available": True,
                "status": e.code,
                "message": f"URL reachable but returned HTTP {e.code}",
            }
        except Exception as e:
            return {"available": False, "status": 0, "message": f"URL unreachable: {e}"}
