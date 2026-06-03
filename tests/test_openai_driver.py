import json
import os
from unittest.mock import patch, MagicMock
import pytest
from pydantic import BaseModel
from deer.drivers.openai_driver import OpenAIDriver

class ResponseModel(BaseModel):
    answer: str

@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_openai_driver_init():
    driver = OpenAIDriver(model_name="gpt-4")
    assert driver.model_name == "gpt-4"
    assert driver.api_key == "test-key"
    assert driver.url == "https://api.openai.com/v1/chat/completions"

def test_openai_driver_init_no_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
            OpenAIDriver(model_name="gpt-4")

@patch("urllib.request.urlopen")
@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_generate_text(mock_urlopen):
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Hello world"}}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    driver = OpenAIDriver(model_name="gpt-4")
    result = driver.generate_text("Hi")

    assert result == "Hello world"
    # Check if correct URL and payload were sent
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "https://api.openai.com/v1/chat/completions"
    assert req.get_header("Authorization") == "Bearer test-key"
    
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["model"] == "gpt-4"
    assert payload["messages"] == [{"role": "user", "content": "Hi"}]

@patch("urllib.request.urlopen")
@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_generate_json(mock_urlopen):
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": '{"answer": "42"}'}}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    driver = OpenAIDriver(model_name="gpt-4")
    result = driver.generate_json("What is the answer?", response_model=ResponseModel)

    assert isinstance(result, ResponseModel)
    assert result.answer == "42"
    
    # Check if correct payload was sent
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["response_format"] == {"type": "json_object"}
