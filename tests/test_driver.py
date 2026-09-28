import pytest
from deer.drivers import OllamaDriver, ChatMessage


@pytest.fixture
def driver():
    driver = OllamaDriver(model_name="gemma4:31b-cloud")
    return driver


def test_hecho(driver):

    messages: list[ChatMessage] = [
        {"role": "user", "content": "Hola mundo"},
    ]
    response = driver.generate(messages)

    pass
