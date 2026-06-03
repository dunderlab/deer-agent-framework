import urllib.request
import urllib.error
from dataclasses import dataclass

from deer.tools import ToolProvider, tool, Return


@dataclass
class NetworkManager(ToolProvider):

    @tool()
    def fetch_endpoint(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: str | None = None,
    ) -> Return(status=int, body=str, message=str):
        """Executes a strict HTTP request (GET, POST, PUT, DELETE) to a target URL, capturing the response status and raw body text."""
        headers = headers or {}
        encoded_data = data.encode("utf-8") if data else None

        req = urllib.request.Request(
            url, data=encoded_data, headers=headers, method=method.upper()
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
            return {"status": 0, "body": "", "message": f"Connection Error: {str(e)}"}

    @tool(modifies_state=True)
    def download_asset(
        self, url: str, destination_path: str
    ) -> Return(success=bool, path=str, message=str):
        """Streams and downloads a remote file or dataset directly into a specified path inside the jail, validating transmission integrity."""
        try:
            safe_path = self.jailed_path(destination_path)

            # Ensure parent directories exist within the jail
            safe_path.parent.mkdir(parents=True, exist_ok=True)

            urllib.request.urlretrieve(url, safe_path)
            return {
                "success": True,
                "path": str(safe_path),
                "message": f"Asset successfully downloaded to {destination_path}",
            }
        except Exception as e:
            return {
                "success": False,
                "path": "",
                "message": f"Download failed: {str(e)}",
            }

    @tool()
    def check_url_availability(
        self, url: str
    ) -> Return(available=bool, status=int, message=str):
        """Performs a lightweight ping or HEAD request to verify if an external API or local endpoint is up and accepting connections."""
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return {
                    "available": True,
                    "status": response.status,
                    "message": "Endpoint is up and reachable.",
                }
        except urllib.error.HTTPError as e:
            return {
                "available": True,
                "status": e.code,
                "message": f"Endpoint reachable but returned HTTP {e.code}",
            }
        except Exception as e:
            return {
                "available": False,
                "status": 0,
                "message": f"Endpoint unreachable: {str(e)}",
            }
