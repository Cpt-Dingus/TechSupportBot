"""Helper for generating a standard logger.
"""

import logging

from utils.helpers import get_env_value


def get_logger(name):
    """Gathers a logger object based on project standards.

    parameters:
        name (str): the name for the logger.
    """
    try:
        debug = int(get_env_value("DEBUG"))
    except (ValueError, NameError):
        debug = 0

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)

    logger = logging.getLogger(name)

    return logger
