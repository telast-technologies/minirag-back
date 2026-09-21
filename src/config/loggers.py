import logging

# setup and configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)


class Logger:
    """
    Logging utility wrapper for application-wide logging.

    Provides convenient methods for different log levels.
    """

    def __init__(self, name):
        """
        Initialize logger with a name.

        Args:
            name (str): Name for the logger, typically __name__ of the module.
        """
        self.logger = logging.getLogger(name)

    def info(self, message):
        """
        Log an informational message.

        Args:
            message (str): The message to log.
        """
        self.logger.info(message)

    def error(self, message):
        """
        Log an error message.

        Args:
            message (str): The message to log.
        """
        self.logger.error(message)

    def debug(self, message):
        """
        Log a debug message.

        Args:
            message (str): The message to log.
        """
        self.logger.debug(message)

    def warning(self, message):
        """
        Log a warning message.

        Args:
            message (str): The message to log.
        """
        self.logger.warning(message)

    def critical(self, message):
        """
        Log a critical message.

        Args:
            message (str): The message to log.
        """
        self.logger.critical(message)

    def exception(self, message):
        """
        Log an exception with traceback.

        Args:
            message (str): The message to log.
        """
        self.logger.exception(message)
