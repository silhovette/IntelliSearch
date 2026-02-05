"""
Global Logger Configuration for IntelliSearch

This module provides a centralized logging system that:
- Creates timestamped log files for each application run
- Provides consistent log formatting across all modules
- Supports different log levels for console and file output
- Automatically adds module names to log records
- Defines custom log levels shared across the application
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Custom log levels for IntelliSearch
# These levels are shared across all modules
TOOL_CALL_ERROR = 35  # Between ERROR(40) and WARNING(30)
MCP_COMMUNICATION = 25  # Between WARNING(30) and INFO(20)


class IntelliSearchLogger:
    """
    Global logger manager for IntelliSearch project.

    This class manages logging configuration and provides unified logger instances
    across all modules. It creates timestamped log files and ensures consistent
    formatting throughout the application.

    Attributes:
        log_dir: Directory to store log files
        session_start_time: Timestamp of the current session start
        log_file_path: Full path to the current session's log file
        _initialized: Whether the logger system has been initialized
        _custom_log_level: Custom log level (if any)

    Example:
        >>> from core.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.error("An error occurred", exc_info=True)
    """

    def __init__(
        self,
        log_dir: str = "log",
        console_level: int = logging.WARNING,
        file_level: int = logging.INFO,
        log_format: Optional[str] = None
    ):
        """
        Initialize the global logger manager.

        Args:
            log_dir: Directory to store log files (default: "log")
            console_level: Logging level for console output (default: WARNING)
            file_level: Logging level for file output (default: INFO)
            log_format: Custom log format string (optional)
        """
        self.log_dir = Path(log_dir)
        self.session_start_time = datetime.now()
        self.log_file_path: Optional[Path] = None
        self._initialized = False

        # Default log format
        self.log_format = log_format or (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.date_format = "%Y-%m-%d %H:%M:%S"

        self.console_level = console_level
        self.file_level = file_level

        # Register custom log levels
        self._register_custom_levels()

    def _create_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _register_custom_levels(self) -> None:
        """
        Register custom log levels for IntelliSearch.

        This method defines custom log levels that are shared across all modules:
        - TOOL_CALL_ERROR (35): For tool call errors
        - MCP_COMMUNICATION (25): For MCP protocol communication
        """
        logging.addLevelName(TOOL_CALL_ERROR, "TOOL_CALL_ERROR")
        logging.addLevelName(MCP_COMMUNICATION, "MCP_COMMUNICATION")

    def _generate_log_filename(self) -> str:
        """
        Generate a timestamped log filename.

        Returns:
            Filename with session start timestamp
        """
        return f"intellisearch_main.log"

    def _get_log_formatter(self) -> logging.Formatter:
        """
        Create a log formatter with the specified format.

        Returns:
            Configured logging formatter
        """
        return logging.Formatter(
            fmt=self.log_format,
            datefmt=self.date_format
        )

    def _setup_console_handler(self) -> logging.StreamHandler:
        """
        Create and configure console handler.

        Returns:
            Configured console stream handler
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(self._get_log_formatter())
        return console_handler

    def _setup_file_handler(self) -> logging.FileHandler:
        """
        Create and configure file handler.

        Returns:
            Configured file handler
        """
        self._create_log_directory()
        log_filename = self._generate_log_filename()
        self.log_file_path = self.log_dir / log_filename

        file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(self._get_log_formatter())
        return file_handler

    def initialize(self) -> None:
        """
        Initialize the global logging system.

        This method should be called once at application startup.
        It sets up the root logger with console and file handlers.

        Raises:
            OSError: If log file cannot be created
        """
        if self._initialized:
            return

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all levels

        # Remove any existing handlers
        root_logger.handlers.clear()

        # Add console handler
        console_handler = self._setup_console_handler()
        root_logger.addHandler(console_handler)

        # Add file handler
        file_handler = self._setup_file_handler()
        root_logger.addHandler(file_handler)

        # Prevent propagation to avoid duplicate logs
        root_logger.propagate = False

        self._initialized = True

        # Log initialization message
        init_logger = logging.getLogger(__name__)
        init_logger.info(f"Logging system initialized. Log file: {self.log_file_path}")

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.

        Args:
            name: Logger name, typically __name__ of the calling module

        Returns:
            Logger instance with configured handlers

        Example:
            >>> logger_manager = IntelliSearchLogger()
            >>> logger_manager.initialize()
            >>> logger = logger_manager.get_logger(__name__)
            >>> logger.info("Module initialized")
        """
        if not self._initialized:
            self.initialize()

        logger = logging.getLogger(name)

        # Set logger level to the lowest level among handlers
        logger.setLevel(min(self.console_level, self.file_level))

        return logger


# Global logger manager instance
_logger_manager: Optional[IntelliSearchLogger] = None


def setup_logging(
    log_dir: str = "log",
    console_level: int = logging.WARNING,
    file_level: int = logging.INFO,
    log_format: Optional[str] = None
) -> IntelliSearchLogger:
    """
    Setup the global logging system.

    This function should be called once at application startup to initialize
    the logging system with custom configuration. Custom log levels are
    automatically registered.

    Args:
        log_dir: Directory to store log files (default: "log")
        console_level: Logging level for console output (default: WARNING)
        file_level: Logging level for file output (default: INFO)
        log_format: Custom log format string (optional)

    Returns:
        The initialized IntelliSearchLogger instance

    Example:
        >>> from core.logger import setup_logging
        >>> setup_logging(
        ...     console_level=logging.INFO,
        ...     file_level=logging.DEBUG
        ... )
    """
    global _logger_manager

    _logger_manager = IntelliSearchLogger(
        log_dir=log_dir,
        console_level=console_level,
        file_level=file_level,
        log_format=log_format
    )

    _logger_manager.initialize()
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    This is the main interface for obtaining loggers throughout the application.
    If the logging system hasn't been initialized yet, it will be initialized
    with default settings.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Logger instance with configured handlers

    Example:
        >>> from core.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
        >>> logger.debug("Detailed debug information")
        >>> logger.error("An error occurred", exc_info=True)
    """
    global _logger_manager

    if _logger_manager is None:
        # Initialize with default settings if not already initialized
        setup_logging()

    return _logger_manager.get_logger(name)


def get_log_file_path() -> Optional[Path]:
    """
    Get the path to the current session's log file.

    Returns:
        Path to the log file, or None if logging hasn't been initialized

    Example:
        >>> from core.logger import get_log_file_path
        >>> log_path = get_log_file_path()
        >>> print(f"Logs are being written to: {log_path}")
    """
    global _logger_manager
    if _logger_manager is None:
        return None
    return _logger_manager.log_file_path


def get_session_start_time() -> Optional[datetime]:
    """
    Get the timestamp of the current logging session start.

    Returns:
        Session start time, or None if logging hasn't been initialized

    Example:
        >>> from core.logger import get_session_start_time
        >>> start_time = get_session_start_time()
        >>> print(f"Session started at: {start_time}")
    """
    global _logger_manager
    if _logger_manager is None:
        return None
    return _logger_manager.session_start_time


__all__ = [
    "IntelliSearchLogger",
    "setup_logging",
    "get_logger",
    "get_log_file_path",
    "get_session_start_time",
    "TOOL_CALL_ERROR",
    "MCP_COMMUNICATION",
]