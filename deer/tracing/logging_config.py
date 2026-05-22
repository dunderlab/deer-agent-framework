import logging

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

logger = logging.getLogger("DEER")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.WARNING)
logger.propagate = False


logger_llm = logging.getLogger("DEER-LLM")
if not logger_llm.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger_llm.addHandler(handler)
logger_llm.setLevel(logging.WARNING)
logger_llm.propagate = False
