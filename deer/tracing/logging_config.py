import logging

logger = logging.getLogger("DEER")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False


logger_llm = logging.getLogger("DEER-LLM")
if not logger_llm.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger_llm.addHandler(handler)
logger_llm.setLevel(logging.WARNING)
logger_llm.propagate = False
