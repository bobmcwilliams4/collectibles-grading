"""
Collectibles Grading Backend
AI-Powered Comic Book Grading System
Integrated with Promethian Vault for secure API key management
"""

__version__ = "1.0.0"
__author__ = "ECHO_PRIME"

from .models import (
    ComicBase,
    ComicCreate,
    ComicFull,
    Defect,
    AIGradeResult,
    ConsensusGrade,
    PriceData,
    ConsensusPricing
)

from .database import DatabaseManager, get_db
from .ai_consensus import ConsensusGrader
from .pricing_engine import PricingEngine
from .batch_processor import BatchProcessor, BatchImporter
from .analytics import AnalyticsEngine, get_analytics_engine
from .cache_manager import CacheManager, cache_manager, cached
from .logging_config import setup_logging, get_logger
# VAULT DISABLED - corrupts sys.modules on GS343 Gateway profile
# from .vault_integration import VaultIntegration, get_vault, get_api_key, initialize_vault
from .config_loader import ConfigLoader, get_config_loader, load_ai_config, initialize_config

__all__ = [
    # Models
    'ComicBase',
    'ComicCreate',
    'ComicFull',
    'Defect',
    'AIGradeResult',
    'ConsensusGrade',
    'PriceData',
    'ConsensusPricing',

    # Database
    'DatabaseManager',
    'get_db',

    # AI Grading
    'ConsensusGrader',

    # Pricing
    'PricingEngine',

    # Batch Processing
    'BatchProcessor',
    'BatchImporter',

    # Analytics
    'AnalyticsEngine',
    'get_analytics_engine',

    # Caching
    'CacheManager',
    'cache_manager',
    'cached',

    # Logging
    'setup_logging',
    'get_logger',

    # Vault Integration - DISABLED
    # 'VaultIntegration',
    # 'get_vault',
    # 'get_api_key',
    # 'initialize_vault',

    # Configuration
    'ConfigLoader',
    'get_config_loader',
    'load_ai_config',
    'initialize_config',
]
