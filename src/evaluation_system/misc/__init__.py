import logging

logging.basicConfig(
    format="%(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger: logging.Logger = logging.getLogger("freva")
