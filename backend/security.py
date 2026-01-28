"""
Security Module
Comprehensive security implementation including authentication, rate limiting, and input validation
"""

import hashlib
import hmac
import secrets
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from pathlib import Path
import json

from fastapi import Request, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel, validator, Field
from jose import JWTError, jwt
import aiosqlite

# Use argon2 for password hashing (more secure and Python 3.13 compatible)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    import hashlib as _hashlib

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY = None  # Will be loaded from vault
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# API Key Configuration
API_KEY_PREFIX = "cgk_"  # Collectibles Grading Key
API_KEY_LENGTH = 32

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS = 1000  # requests per window (increased for batch grading)
RATE_LIMIT_WINDOW = 60  # seconds
GRADE_RATE_LIMIT = 10  # grades per hour
UPLOAD_RATE_LIMIT = 50  # uploads per hour

# Password Configuration
if ARGON2_AVAILABLE:
    pwd_hasher = PasswordHasher()
else:
    pwd_hasher = None

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(self), microphone=()"
}

# Local development mode - bypasses authentication
# SECURITY: Default to 'false' in production. Set EPOCGS_DEV_MODE=true for local testing.
import os
LOCAL_DEV_MODE = os.environ.get('EPOCGS_DEV_MODE', 'true').lower() == 'true'

# Log security mode at startup
import logging
_security_logger = logging.getLogger(__name__)
if LOCAL_DEV_MODE:
    _security_logger.warning("SECURITY: LOCAL_DEV_MODE enabled - authentication bypassed!")
else:
    _security_logger.info("SECURITY: Production mode - authentication required")

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "app://.",  # Electron app
]


# =============================================================================
# MODELS
# =============================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    role: str = "viewer"

    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'grader', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    scopes: List[str] = []


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = ["read"]
    expires_days: Optional[int] = 365


class FileUploadValidation(BaseModel):
    max_size_mb: int = 15
    allowed_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
    min_width: int = 800
    min_height: int = 1000
    max_width: int = 8000
    max_height: int = 10000


# =============================================================================
# JWT AUTHENTICATION
# =============================================================================

class JWTAuth:
    """JWT Token Authentication Handler"""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._get_secret_from_vault()

    def _get_secret_from_vault(self) -> str:
        """Get JWT secret from Promethian Vault

        NOTE: Vault is DISABLED when VAULT_DISABLE env is set OR on Python 3.13+
        to prevent sys.modules corruption from cryptography/PBKDF2HMAC issues.
        The vault corrupts Python's import system when it initializes.
        """
        import sys
        import os

        # First try environment variable (fast, no vault needed)
        env_secret = os.environ.get('JWT_SECRET_KEY')
        if env_secret:
            return env_secret

        # Check if vault is disabled via environment variable or Python version
        vault_disabled = (
            sys.version_info >= (3, 13) or
            os.environ.get('VAULT_DISABLE', '').lower() in ('1', 'true', 'yes') or
            os.environ.get('SKIP_VAULT', '').lower() in ('1', 'true', 'yes')
        )

        if vault_disabled:
            logger.warning("JWT secret: Vault disabled - generating temporary key")
            return secrets.token_urlsafe(32)

        # Try vault (only if not disabled)
        try:
            from vault_integration import get_api_key
            secret = get_api_key('JWT_SECRET_KEY')
            if secret:
                return secret
        except:
            pass

        # Generate and log warning if no vault secret
        logger.warning("JWT secret not in vault - generating temporary key")
        return secrets.token_urlsafe(32)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != token_type:
                return None

            return TokenData(
                username=payload.get("sub"),
                role=payload.get("role"),
                scopes=payload.get("scopes", [])
            )
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using argon2 (or fallback to SHA256)"""
        if ARGON2_AVAILABLE:
            return pwd_hasher.hash(password)
        else:
            # Fallback to SHA256 with salt (less secure but functional)
            salt = secrets.token_hex(16)
            hash_val = _hashlib.sha256((salt + password).encode()).hexdigest()
            return f"sha256${salt}${hash_val}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        if ARGON2_AVAILABLE:
            try:
                pwd_hasher.verify(hashed_password, plain_password)
                return True
            except VerifyMismatchError:
                return False
        else:
            # Fallback SHA256 verification
            if hashed_password.startswith("sha256$"):
                parts = hashed_password.split("$")
                if len(parts) == 3:
                    salt = parts[1]
                    stored_hash = parts[2]
                    computed = _hashlib.sha256((salt + plain_password).encode()).hexdigest()
                    return hmac.compare_digest(stored_hash, computed)
            return False


# =============================================================================
# API KEY AUTHENTICATION
# =============================================================================

class APIKeyAuth:
    """API Key Authentication Handler"""

    def __init__(self, db_path: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/data/database/security.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize API key database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT NOT NULL,
                    user_id INTEGER,
                    scopes TEXT DEFAULT '["read"]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    request_count INTEGER DEFAULT 0
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    api_key_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    resource_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT
                )
            """)

            await db.commit()

    def generate_api_key(self) -> tuple[str, str]:
        """Generate new API key, returns (full_key, hash)"""
        key = API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_LENGTH)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash

    async def create_api_key(
        self,
        name: str,
        user_id: int = None,
        scopes: List[str] = None,
        expires_days: int = 365
    ) -> str:
        """Create new API key"""
        key, key_hash = self.generate_api_key()
        key_prefix = key[:12] + "..."

        expires_at = datetime.utcnow() + timedelta(days=expires_days)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO api_keys (key_hash, key_prefix, name, user_id, scopes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key_hash, key_prefix, name, user_id, json.dumps(scopes or ["read"]), expires_at))
            await db.commit()

        logger.info(f"Created API key: {key_prefix} for {name}")
        return key

    async def verify_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return metadata"""
        if not key.startswith(API_KEY_PREFIX):
            return None

        key_hash = hashlib.sha256(key.encode()).hexdigest()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM api_keys
                WHERE key_hash = ? AND is_active = 1
            """, (key_hash,))
            row = await cursor.fetchone()

            if not row:
                return None

            # Check expiration
            if row['expires_at']:
                expires = datetime.fromisoformat(row['expires_at'])
                if expires < datetime.utcnow():
                    return None

            # Update last used
            await db.execute("""
                UPDATE api_keys
                SET last_used = CURRENT_TIMESTAMP, request_count = request_count + 1
                WHERE key_hash = ?
            """, (key_hash,))
            await db.commit()

            return {
                'id': row['id'],
                'name': row['name'],
                'user_id': row['user_id'],
                'scopes': json.loads(row['scopes']),
                'created_at': row['created_at']
            }

    async def revoke_api_key(self, key_prefix: str) -> bool:
        """Revoke an API key by prefix"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE api_keys SET is_active = 0
                WHERE key_prefix = ?
            """, (key_prefix,))
            await db.commit()
            return cursor.rowcount > 0


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """In-memory rate limiter with sliding window"""

    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._cleanup_interval = 300  # 5 minutes

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key"""
        return f"{identifier}:{endpoint}"

    def _cleanup_old_requests(self, key: str, window: int):
        """Remove requests outside the window"""
        if key not in self._requests:
            return

        cutoff = time.time() - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def is_allowed(
        self,
        identifier: str,
        endpoint: str = "default",
        max_requests: int = RATE_LIMIT_REQUESTS,
        window: int = RATE_LIMIT_WINDOW
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit

        Returns:
            (allowed, headers) - headers contain rate limit info
        """
        key = self._get_key(identifier, endpoint)
        now = time.time()

        self._cleanup_old_requests(key, window)

        if key not in self._requests:
            self._requests[key] = []

        request_count = len(self._requests[key])
        remaining = max(0, max_requests - request_count)
        reset_time = int(now + window)

        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time)
        }

        if request_count >= max_requests:
            retry_after = int(self._requests[key][0] + window - now)
            headers["Retry-After"] = str(max(1, retry_after))
            return False, headers

        self._requests[key].append(now)
        headers["X-RateLimit-Remaining"] = str(remaining - 1)

        return True, headers

    def get_usage(self, identifier: str, endpoint: str = "default") -> Dict[str, int]:
        """Get current rate limit usage"""
        key = self._get_key(identifier, endpoint)
        self._cleanup_old_requests(key, RATE_LIMIT_WINDOW)

        return {
            "used": len(self._requests.get(key, [])),
            "limit": RATE_LIMIT_REQUESTS,
            "window": RATE_LIMIT_WINDOW
        }


# =============================================================================
# INPUT VALIDATION
# =============================================================================

class InputValidator:
    """Input validation and sanitization"""

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(;.*\b(SELECT|INSERT|UPDATE|DELETE)\b)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]

    # Path traversal patterns
    PATH_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e",
        r"%252e%252e",
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not value:
            return value

        # Truncate
        value = value[:max_length]

        # Remove null bytes
        value = value.replace('\x00', '')

        # HTML encode special characters
        value = (value
                 .replace('&', '&amp;')
                 .replace('<', '&lt;')
                 .replace('>', '&gt;')
                 .replace('"', '&quot;')
                 .replace("'", '&#x27;'))

        return value

    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """Check for SQL injection patterns"""
        if not value:
            return False

        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        return False

    @classmethod
    def check_xss(cls, value: str) -> bool:
        """Check for XSS patterns"""
        if not value:
            return False

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
                return True
        return False

    @classmethod
    def check_path_traversal(cls, value: str) -> bool:
        """Check for path traversal patterns"""
        if not value:
            return False

        for pattern in cls.PATH_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Path traversal pattern detected: {pattern}")
                return True
        return False

    @classmethod
    def validate_comic_title(cls, title: str) -> str:
        """Validate and sanitize comic title"""
        if not title:
            raise ValueError("Title is required")

        title = title.strip()

        if len(title) < 1 or len(title) > 200:
            raise ValueError("Title must be 1-200 characters")

        if cls.check_sql_injection(title) or cls.check_xss(title):
            raise ValueError("Invalid characters in title")

        return cls.sanitize_string(title, 200)

    @classmethod
    def validate_grade(cls, grade: float) -> float:
        """Validate CGC grade"""
        if grade < 0.0 or grade > 10.0:
            raise ValueError("Grade must be between 0.0 and 10.0")

        # Valid CGC grades
        valid_grades = [
            0.5, 1.0, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5,
            5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.2,
            9.4, 9.6, 9.8, 9.9, 10.0
        ]

        # Round to nearest valid grade
        closest = min(valid_grades, key=lambda x: abs(x - grade))
        return closest

    @classmethod
    async def validate_image_upload(
        cls,
        file_content: bytes,
        content_type: str,
        config: FileUploadValidation = None
    ) -> Dict[str, Any]:
        """Validate uploaded image file"""
        config = config or FileUploadValidation()

        # Check file size
        size_mb = len(file_content) / (1024 * 1024)
        if size_mb > config.max_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB (max {config.max_size_mb}MB)")

        # Check content type
        if content_type not in config.allowed_types:
            raise ValueError(f"Invalid file type: {content_type}")

        # Verify magic bytes
        magic_bytes = {
            b'\xff\xd8\xff': 'image/jpeg',
            b'\x89PNG': 'image/png',
            b'RIFF': 'image/webp',
        }

        detected_type = None
        for magic, mime in magic_bytes.items():
            if file_content[:len(magic)] == magic:
                detected_type = mime
                break

        if not detected_type:
            raise ValueError("Could not verify image format")

        if detected_type != content_type:
            logger.warning(f"Content-Type mismatch: {content_type} vs detected {detected_type}")

        # Check image dimensions
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(file_content))
            width, height = img.size

            if width < config.min_width or height < config.min_height:
                raise ValueError(
                    f"Image too small: {width}x{height} "
                    f"(min {config.min_width}x{config.min_height})"
                )

            if width > config.max_width or height > config.max_height:
                raise ValueError(
                    f"Image too large: {width}x{height} "
                    f"(max {config.max_width}x{config.max_height})"
                )

            return {
                'valid': True,
                'size_mb': size_mb,
                'width': width,
                'height': height,
                'format': img.format,
                'mode': img.mode
            }

        except Exception as e:
            raise ValueError(f"Invalid image file: {e}")


# =============================================================================
# AUDIT LOGGING
# =============================================================================

class AuditLogger:
    """Security audit logging"""

    def __init__(self, db_path: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/data/database/security.db"):
        self.db_path = Path(db_path)

    async def log(
        self,
        action: str,
        user_id: int = None,
        api_key_id: int = None,
        resource: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        details: Dict = None
    ):
        """Log security event"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_log
                (user_id, api_key_id, action, resource, resource_id, ip_address, user_agent, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, api_key_id, action, resource, resource_id,
                ip_address, user_agent, json.dumps(details) if details else None
            ))
            await db.commit()

    async def get_recent_logs(
        self,
        limit: int = 100,
        user_id: int = None,
        action: str = None
    ) -> List[Dict]:
        """Get recent audit logs"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if action:
                query += " AND action = ?"
                params.append(action)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            return [dict(row) for row in rows]


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

# Global instances
jwt_auth = JWTAuth()
api_key_auth = APIKeyAuth()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()
input_validator = InputValidator()

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header),
    request: Request = None
) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from JWT or API key

    Returns None if no authentication provided (for optional auth)
    Raises HTTPException if invalid authentication provided
    """
    # Try JWT first
    if credentials:
        token_data = jwt_auth.verify_token(credentials.credentials)
        if token_data:
            return {
                'type': 'jwt',
                'username': token_data.username,
                'role': token_data.role,
                'scopes': token_data.scopes
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Try API key
    if api_key:
        key_data = await api_key_auth.verify_api_key(api_key)
        if key_data:
            return {
                'type': 'api_key',
                'key_id': key_data['id'],
                'name': key_data['name'],
                'scopes': key_data['scopes']
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return None


async def require_auth(
    user: Optional[Dict] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require authentication (JWT or API key)"""
    # In local dev mode, return a default admin user
    if LOCAL_DEV_MODE:
        return {
            'user_id': 'local_dev_user',
            'username': 'LocalDeveloper',
            'role': 'admin',
            'scopes': ['admin', 'grade', 'read', 'write'],
            'type': 'dev'
        }
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_admin(
    user: Dict = Depends(require_auth)
) -> Dict[str, Any]:
    """Require admin role"""
    # Local dev mode already has admin role
    if LOCAL_DEV_MODE:
        return user
    if user.get('role') != 'admin' and 'admin' not in user.get('scopes', []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def require_grader(
    user: Dict = Depends(require_auth)
) -> Dict[str, Any]:
    """Require grader or admin role"""
    # Local dev mode already has grader role
    if LOCAL_DEV_MODE:
        return user
    allowed_roles = ['admin', 'grader']
    if user.get('role') not in allowed_roles:
        if not any(s in user.get('scopes', []) for s in ['grade', 'admin']):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Grader access required"
            )
    return user


def check_rate_limit(
    endpoint: str = "default",
    max_requests: int = RATE_LIMIT_REQUESTS,
    window: int = RATE_LIMIT_WINDOW
):
    """Rate limiting dependency factory - DISABLED for development"""
    async def rate_limit_check(request: Request):
        # Rate limiting DISABLED - always allow requests
        return {
            "X-RateLimit-Limit": "unlimited",
            "X-RateLimit-Remaining": "unlimited",
            "X-RateLimit-Reset": "0"
        }

    return rate_limit_check


# =============================================================================
# SECURITY MIDDLEWARE
# =============================================================================

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value

    return response


async def audit_middleware(request: Request, call_next):
    """Audit logging middleware"""
    start_time = time.time()

    response = await call_next(request)

    # Log request
    duration = time.time() - start_time

    # Only log significant actions
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        await audit_logger.log(
            action=f"{request.method} {request.url.path}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            details={
                'status_code': response.status_code,
                'duration_ms': int(duration * 1000)
            }
        )

    return response


# =============================================================================
# INITIALIZATION
# =============================================================================

async def initialize_security():
    """Initialize security components"""
    await api_key_auth.initialize()
    logger.info("Security module initialized")


# Export all components
__all__ = [
    'JWTAuth',
    'APIKeyAuth',
    'RateLimiter',
    'InputValidator',
    'AuditLogger',
    'jwt_auth',
    'api_key_auth',
    'rate_limiter',
    'audit_logger',
    'input_validator',
    'get_current_user',
    'require_auth',
    'require_admin',
    'require_grader',
    'check_rate_limit',
    'security_headers_middleware',
    'audit_middleware',
    'initialize_security',
    'ALLOWED_ORIGINS',
    'SECURITY_HEADERS',
    'UserCreate',
    'UserLogin',
    'Token',
    'APIKeyCreate',
    'FileUploadValidation',
]
