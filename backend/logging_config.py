"""
Advanced Logging Configuration
Comprehensive logging with rotation, formatting, and multiple outputs
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import traceback
from enum import Enum


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# Custom JSON formatter
class JSONFormatter(logging.Formatter):
    """Format log records as JSON for machine parsing"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                'message'
            ):
                log_entry[key] = value

        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console output for better readability"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format the record
        formatted = super().format(record)

        # Apply color
        return f"{color}{formatted}{reset}"


class ContextFilter(logging.Filter):
    """Add contextual information to log records"""

    _context = threading.local()

    @classmethod
    def set_context(cls, **kwargs):
        """Set context for current thread"""
        for key, value in kwargs.items():
            setattr(cls._context, key, value)

    @classmethod
    def clear_context(cls):
        """Clear context for current thread"""
        cls._context.__dict__.clear()

    def filter(self, record: logging.LogRecord) -> bool:
        # Add context to record
        for key, value in self._context.__dict__.items():
            setattr(record, key, value)
        return True


class PerformanceLogger:
    """Log performance metrics"""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
        self.metadata = {}

    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        log_data = {
            'operation': self.operation,
            'elapsed_ms': elapsed,
            **self.metadata
        }

        if exc_type:
            log_data['error'] = str(exc_val)
            self.logger.error(f"Performance: {self.operation}", extra=log_data)
        else:
            self.logger.info(f"Performance: {self.operation}", extra=log_data)

        return False

    def add_metadata(self, **kwargs):
        """Add metadata to performance log"""
        self.metadata.update(kwargs)


class LoggingManager:
    """
    Centralized Logging Configuration

    Features:
    - Multiple output handlers (console, file, JSON)
    - Log rotation with size and time limits
    - Colored console output
    - JSON format for log aggregation
    - Performance logging
    - Context injection
    - Log level filtering per module
    """

    def __init__(
        self,
        log_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/logs",
        app_name: str = "collectibles_grading",
        default_level: LogLevel = LogLevel.INFO,
        console_level: LogLevel = LogLevel.INFO,
        file_level: LogLevel = LogLevel.DEBUG,
        json_logging: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 10
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.app_name = app_name
        self.default_level = default_level
        self.console_level = console_level
        self.file_level = file_level
        self.json_logging = json_logging
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Module-specific log levels
        self._module_levels: Dict[str, LogLevel] = {}

        # Performance loggers
        self._perf_loggers: Dict[str, logging.Logger] = {}

        # Initialize
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging system"""
        # Get root logger for app
        self.root_logger = logging.getLogger(self.app_name)
        self.root_logger.setLevel(logging.DEBUG)  # Capture all, filter per handler

        # Clear existing handlers
        self.root_logger.handlers.clear()

        # Add context filter
        self.context_filter = ContextFilter()
        self.root_logger.addFilter(self.context_filter)

        # Console handler
        self._add_console_handler()

        # File handlers
        self._add_file_handlers()

        # JSON handler for structured logging
        if self.json_logging:
            self._add_json_handler()

        # Set up library loggers to be less verbose
        self._configure_library_loggers()

        logging.info(f"Logging initialized: {self.log_dir}")

    def _add_console_handler(self):
        """Add colored console handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level.value)

        # Colored format for console
        console_format = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)

        self.root_logger.addHandler(console_handler)

    def _add_file_handlers(self):
        """Add rotating file handlers"""
        # Main log file
        main_log = self.log_dir / f"{self.app_name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(self.file_level.value)

        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        main_handler.setFormatter(file_format)

        self.root_logger.addHandler(main_handler)

        # Error-only log file
        error_log = self.log_dir / f"{self.app_name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)

        self.root_logger.addHandler(error_handler)

    def _add_json_handler(self):
        """Add JSON format handler for log aggregation"""
        json_log = self.log_dir / f"{self.app_name}_json.log"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())

        self.root_logger.addHandler(json_handler)

    def _configure_library_loggers(self):
        """Configure third-party library loggers"""
        noisy_loggers = [
            'urllib3',
            'httpx',
            'httpcore',
            'asyncio',
            'aiohttp',
            'PIL',
            'cv2'
        ]

        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific module

        Args:
            name: Module name (usually __name__)

        Returns:
            Logger instance
        """
        logger = logging.getLogger(f"{self.app_name}.{name}")

        # Apply module-specific level if configured
        if name in self._module_levels:
            logger.setLevel(self._module_levels[name].value)

        return logger

    def set_module_level(self, module: str, level: LogLevel):
        """Set log level for a specific module"""
        self._module_levels[module] = level

        logger = logging.getLogger(f"{self.app_name}.{module}")
        logger.setLevel(level.value)

    def set_context(self, **kwargs):
        """Set context for current thread"""
        ContextFilter.set_context(**kwargs)

    def clear_context(self):
        """Clear context for current thread"""
        ContextFilter.clear_context()

    def performance(self, operation: str) -> PerformanceLogger:
        """
        Create a performance logger context manager

        Usage:
            with logging_manager.performance("grade_comic") as perf:
                perf.add_metadata(comic_id=123)
                result = await grade_comic(...)
        """
        perf_logger = self._perf_loggers.get('performance')
        if not perf_logger:
            perf_logger = self.get_logger('performance')
            self._perf_loggers['performance'] = perf_logger

        return PerformanceLogger(perf_logger, operation)

    def log_api_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        elapsed_ms: float,
        request_id: str = None
    ):
        """Log API request"""
        api_logger = self.get_logger('api')

        log_data = {
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'elapsed_ms': elapsed_ms
        }

        if request_id:
            log_data['request_id'] = request_id

        level = logging.INFO if status_code < 400 else logging.ERROR

        api_logger.log(
            level,
            f"{method} {endpoint} - {status_code} ({elapsed_ms:.2f}ms)",
            extra=log_data
        )

    def log_grading_result(
        self,
        comic_id: str,
        grade: float,
        confidence: float,
        providers: list,
        elapsed_ms: float
    ):
        """Log grading result"""
        grading_logger = self.get_logger('grading')

        grading_logger.info(
            f"Graded comic {comic_id}: {grade} (confidence: {confidence:.2%})",
            extra={
                'comic_id': comic_id,
                'grade': grade,
                'confidence': confidence,
                'providers': providers,
                'elapsed_ms': elapsed_ms
            }
        )

    def log_pricing_result(
        self,
        comic_id: str,
        estimated_value: float,
        sources: list,
        elapsed_ms: float
    ):
        """Log pricing result"""
        pricing_logger = self.get_logger('pricing')

        pricing_logger.info(
            f"Priced comic {comic_id}: ${estimated_value:.2f}",
            extra={
                'comic_id': comic_id,
                'estimated_value': estimated_value,
                'sources': sources,
                'elapsed_ms': elapsed_ms
            }
        )

    def log_error(
        self,
        error: Exception,
        context: str = None,
        **kwargs
    ):
        """Log error with context"""
        error_logger = self.get_logger('errors')

        error_logger.error(
            f"Error{f' in {context}' if context else ''}: {error}",
            exc_info=True,
            extra={
                'error_type': type(error).__name__,
                'context': context,
                **kwargs
            }
        )

    def get_recent_logs(
        self,
        level: LogLevel = LogLevel.INFO,
        limit: int = 100
    ) -> list:
        """Get recent log entries from JSON log"""
        json_log = self.log_dir / f"{self.app_name}_json.log"

        if not json_log.exists():
            return []

        logs = []
        try:
            with open(json_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        log_level = getattr(logging, entry.get('level', 'INFO'))
                        if log_level >= level.value:
                            logs.append(entry)
                    except json.JSONDecodeError:
                        continue

            # Return most recent
            return logs[-limit:]

        except Exception as e:
            logging.error(f"Failed to read logs: {e}")
            return []

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for recent timeframe"""
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        errors = []

        json_log = self.log_dir / f"{self.app_name}_json.log"
        if json_log.exists():
            with open(json_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('level') in ('ERROR', 'CRITICAL'):
                            timestamp = datetime.fromisoformat(entry['timestamp'])
                            if timestamp >= cutoff:
                                errors.append(entry)
                    except:
                        continue

        # Categorize errors
        by_type = {}
        for error in errors:
            error_type = error.get('exception', {}).get('type', 'Unknown')
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(error)

        return {
            'total_errors': len(errors),
            'hours': hours,
            'by_type': {k: len(v) for k, v in by_type.items()},
            'recent_errors': errors[-10:]
        }


# Global instance
_logging_manager: Optional[LoggingManager] = None


def setup_logging(**kwargs) -> LoggingManager:
    """Initialize logging system"""
    global _logging_manager
    _logging_manager = LoggingManager(**kwargs)
    return _logging_manager


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger"""
    if _logging_manager:
        return _logging_manager.get_logger(name or 'main')
    return logging.getLogger(name)


def get_logging_manager() -> Optional[LoggingManager]:
    """Get logging manager instance"""
    return _logging_manager


# Convenience functions
def log_performance(operation: str):
    """Performance logging context manager"""
    if _logging_manager:
        return _logging_manager.performance(operation)
    # Fallback
    return PerformanceLogger(logging.getLogger(), operation)
