import json
import os
from unittest.mock import patch, MagicMock
import pytest
from pydantic import BaseModel
from deer.drivers.azure_driver import AzureOpenAIDriver

class ResponseModel(BaseModel):
    answer: str

@patch.dict(os.environ, {
    "AZURE_OPENAI_API_KEY": "test-key",
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"
})
def test_azure_driver_init():
    driver = AzureOpenAIDriver(model_name="gpt-4-deployment")
    assert driver.model_name == "gpt-4-deployment"
    assert driver.api_key == "test-key"
    assert driver.url == "https://test.openai.azure.com/openai/deployments/gpt-4-deployment/chat/completions?api-version=2024-02-15-preview"

def test_azure_driver_init_no_key():
    with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"}, clear=True):
        with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY environment variable is not set"):
            AzureOpenAIDriver(model_name="gpt-4")

def test_azure_driver_init_no_endpoint():
    with patch.dict(os.environ, {"AZURE_OPENAI_API_KEY": "test-key"}, clear=True):
        with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT environment variable is not set"):
            AzureOpenAIDriver(model_name="gpt-4")

@patch("urllib.request.urlopen")
@patch.dict(os.environ, {
    "AZURE_OPENAI_API_KEY": "test-key",
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"
})
def test_azure_generate_text(mock_urlopen):
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Hello from Azure"}}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    driver = AzureOpenAIDriver(model_name="gpt4-deploy")
    result = driver.generate_text("Hi Azure")

    assert result == "Hello from Azure"
    
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert "openai/deployments/gpt4-deploy/chat/completions" in req.full_url
    assert req.get_header("Api-key") == "test-key"
    
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["messages"] == [{"role": "user", "content": "Hi Azure"}]
