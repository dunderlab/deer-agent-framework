import pytest
from deer.drivers import OllamaDriver
from deer.models import ChatMessage, Role


@pytest.fixture
def driver():
    driver = OllamaDriver(model_name="gemma4:31b-cloud")
    return driver


def test_driver(driver):
    messages: list[ChatMessage] = [
        ChatMessage(role=Role.USER, content="Hola mundo"),
    ]
    response = driver.generate(messages)
    assert response is not None, "The model did not respond"
    assert len(response) > 0, "The model returned an empty response"
