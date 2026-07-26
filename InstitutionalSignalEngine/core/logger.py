"""
Logger module for the Institutional Signal Intelligence Engine.

Provides a centralized, thread-safe logging system using Python's built-in
logging module. It configures both console and rotating file handlers based
on the application configuration.
"""

import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

from config import config


class LoggerFactory:
    """
    Thread-safe singleton factory for creating and caching application loggers.
    
    Ensures that the root logger is configured exactly once with file and 
    console handlers, and that individual named loggers are cached to prevent
    duplicate creation or handler attachment.
    """
    
    _instance: "LoggerFactory" = None
    _creation_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "LoggerFactory":
        if cls._instance is None:
            with cls._creation_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
            
        with self._creation_lock:
            if self._initialized:
                return
                
            self._loggers: Dict[str, logging.Logger] = {}
            self._cache_lock: threading.Lock = threading.Lock()
            self._configure_root_logger()
            self._initialized = True

    def _configure_root_logger(self) -> None:
        """
        Configures the root logger with console and rotating file handlers
        based on the application configuration.
        """
        log_dir: Path = config.storage.base_path / config.storage.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file_path: Path = log_dir / config.logging.log_file_name
        log_level: int = getattr(logging, config.logging.log_level.value, logging.INFO)
        formatter: logging.Formatter = logging.Formatter(config.logging.log_format)

        # File Handler
        file_handler: RotatingFileHandler = RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=config.logging.max_bytes,
            backupCount=config.logging.backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)

        # Console Handler
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Root Logger Configuration
        root_logger: logging.Logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Prevent adding duplicate handlers if re-initialized
        if not root_logger.handlers:
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Retrieves a cached logger by name. If it does not exist, creates it,
        caches it, and returns it in a thread-safe manner.
        
        Args:
            name: The name of the logger (typically the module name).
            
        Returns:
            A configured logging.Logger instance.
        """
        if name in self._loggers:
            return self._loggers[name]
            
        with self._cache_lock:
            if name in self._loggers:
                return self._loggers[name]
                
            logger: logging.Logger = logging.getLogger(name)
            self._loggers[name] = logger
            return logger