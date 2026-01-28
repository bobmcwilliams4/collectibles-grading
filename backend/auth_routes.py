"""
Authentication Routes
API endpoints for user authentication and API key management
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from security import (
    jwt_auth, api_key_auth, audit_logger,
    require_auth, require_admin, check_rate_limit,
    UserCreate, UserLogin, Token, APIKeyCreate,
    RATE_LIMIT_REQUESTS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# MODELS
# =============================================================================

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: str
    last_login: Optional[str]


class APIKeyResponse(BaseModel):
    key: str  # Only returned on creation
    name: str
    prefix: str
    scopes: List[str]
    expires_at: str


class APIKeyListItem(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: List[str]
    created_at: str
    last_used: Optional[str]
    request_count: int


# =============================================================================
# USER AUTHENTICATION
# =============================================================================

@router.post("/register", response_model=UserResponse)
async def register_user(
    user: UserCreate,
    request: Request,
    _: dict = Depends(check_rate_limit("register", 5, 3600))  # 5 per hour
):
    """
    Register a new user account

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Strong password (8+ chars, upper, lower, digit)
    - **role**: User role (viewer, grader, admin) - admin requires existing admin
    """
    import aiosqlite

    # Hash password
    password_hash = jwt_auth.hash_password(user.password)

    try:
        async with aiosqlite.connect(api_key_auth.db_path) as db:
            # Check if username exists
            cursor = await db.execute(
                "SELECT id FROM users WHERE username = ?",
                (user.username,)
            )
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )

            # Check if email exists
            cursor = await db.execute(
                "SELECT id FROM users WHERE email = ?",
                (user.email,)
            )
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            # Insert user
            cursor = await db.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (user.username, user.email, password_hash, user.role))

            await db.commit()
            user_id = cursor.lastrowid

            # Audit log
            await audit_logger.log(
                action="user_registered",
                user_id=user_id,
                ip_address=request.client.host if request.client else None,
                details={"username": user.username, "role": user.role}
            )

            return UserResponse(
                id=user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                created_at=datetime.utcnow().isoformat(),
                last_login=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    _: dict = Depends(check_rate_limit("login", 10, 300))  # 10 per 5 minutes
):
    """
    Authenticate user and get JWT tokens

    Returns access token (1 hour) and refresh token (7 days)
    """
    import aiosqlite

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (credentials.username,)
        )
        user = await cursor.fetchone()

        if not user or not jwt_auth.verify_password(credentials.password, user['password_hash']):
            # Audit failed login
            await audit_logger.log(
                action="login_failed",
                ip_address=request.client.host if request.client else None,
                details={"username": credentials.username}
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Update last login
        await db.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user['id'],)
        )
        await db.commit()

        # Create tokens
        token_data = {
            "sub": user['username'],
            "role": user['role'],
            "scopes": _get_role_scopes(user['role'])
        }

        access_token = jwt_auth.create_access_token(token_data)
        refresh_token = jwt_auth.create_refresh_token(token_data)

        # Audit successful login
        await audit_logger.log(
            action="login_success",
            user_id=user['id'],
            ip_address=request.client.host if request.client else None
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    request: Request
):
    """
    Refresh access token using refresh token
    """
    token_data = jwt_auth.verify_token(refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Create new tokens
    new_token_data = {
        "sub": token_data.username,
        "role": token_data.role,
        "scopes": token_data.scopes
    }

    new_access_token = jwt_auth.create_access_token(new_token_data)
    new_refresh_token = jwt_auth.create_refresh_token(new_token_data)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=3600
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: dict = Depends(require_auth)
):
    """Get current authenticated user info"""
    import aiosqlite

    if user.get('type') == 'api_key':
        return {
            "id": 0,
            "username": f"API Key: {user.get('name')}",
            "email": "",
            "role": "api_key",
            "created_at": "",
            "last_login": None
        }

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE username = ?",
            (user['username'],)
        )
        db_user = await cursor.fetchone()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=db_user['id'],
            username=db_user['username'],
            email=db_user['email'],
            role=db_user['role'],
            created_at=db_user['created_at'],
            last_login=db_user['last_login']
        )


@router.post("/logout")
async def logout(
    request: Request,
    user: dict = Depends(require_auth)
):
    """
    Logout user (client should discard tokens)

    Note: JWT tokens cannot be truly invalidated server-side without
    maintaining a blacklist. Client should discard tokens.
    """
    await audit_logger.log(
        action="logout",
        ip_address=request.client.host if request.client else None,
        details={"username": user.get('username')}
    )

    return {"message": "Logged out successfully"}


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_request: APIKeyCreate,
    request: Request,
    user: dict = Depends(require_auth)
):
    """
    Create a new API key

    - **name**: Descriptive name for the key
    - **scopes**: Permissions (read, write, grade, admin)
    - **expires_days**: Days until expiration (default 365)

    Returns the full API key - save it securely, it cannot be retrieved again!
    """
    from datetime import timedelta

    # Get user ID if JWT auth
    user_id = None
    if user.get('type') == 'jwt':
        import aiosqlite
        async with aiosqlite.connect(api_key_auth.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE username = ?",
                (user['username'],)
            )
            row = await cursor.fetchone()
            if row:
                user_id = row[0]

    # Create key
    api_key = await api_key_auth.create_api_key(
        name=key_request.name,
        user_id=user_id,
        scopes=key_request.scopes,
        expires_days=key_request.expires_days or 365
    )

    expires_at = datetime.utcnow() + timedelta(days=key_request.expires_days or 365)

    # Audit log
    await audit_logger.log(
        action="api_key_created",
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
        details={"name": key_request.name, "scopes": key_request.scopes}
    )

    return APIKeyResponse(
        key=api_key,
        name=key_request.name,
        prefix=api_key[:12] + "...",
        scopes=key_request.scopes,
        expires_at=expires_at.isoformat()
    )


@router.get("/api-keys", response_model=List[APIKeyListItem])
async def list_api_keys(
    user: dict = Depends(require_auth)
):
    """List all API keys for current user"""
    import aiosqlite

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Get user ID
        user_id = None
        if user.get('type') == 'jwt':
            cursor = await db.execute(
                "SELECT id FROM users WHERE username = ?",
                (user['username'],)
            )
            row = await cursor.fetchone()
            if row:
                user_id = row[0]

        # Get keys
        if user.get('role') == 'admin':
            cursor = await db.execute(
                "SELECT * FROM api_keys WHERE is_active = 1 ORDER BY created_at DESC"
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC",
                (user_id,)
            )

        rows = await cursor.fetchall()

        return [
            APIKeyListItem(
                id=row['id'],
                name=row['name'],
                prefix=row['key_prefix'],
                scopes=eval(row['scopes']) if row['scopes'] else [],
                created_at=row['created_at'],
                last_used=row['last_used'],
                request_count=row['request_count']
            )
            for row in rows
        ]


@router.delete("/api-keys/{key_prefix}")
async def revoke_api_key(
    key_prefix: str,
    request: Request,
    user: dict = Depends(require_auth)
):
    """Revoke an API key by its prefix"""
    success = await api_key_auth.revoke_api_key(key_prefix)

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    await audit_logger.log(
        action="api_key_revoked",
        ip_address=request.client.host if request.client else None,
        details={"key_prefix": key_prefix}
    )

    return {"message": "API key revoked"}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    user: dict = Depends(require_admin)
):
    """List all users (admin only)"""
    import aiosqlite

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()

        return [
            UserResponse(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                role=row['role'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )
            for row in rows
        ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Update user role (admin only)"""
    import aiosqlite

    if role not in ['admin', 'grader', 'viewer']:
        raise HTTPException(status_code=400, detail="Invalid role")

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        cursor = await db.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id)
        )
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

    await audit_logger.log(
        action="user_role_updated",
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
        details={"new_role": role}
    )

    return {"message": f"User role updated to {role}"}


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Deactivate user account (admin only)"""
    import aiosqlite

    async with aiosqlite.connect(api_key_auth.db_path) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
        await db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

    await audit_logger.log(
        action="user_deactivated",
        user_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    return {"message": "User deactivated"}


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 100,
    action: str = None,
    admin: dict = Depends(require_admin)
):
    """Get audit log (admin only)"""
    logs = await audit_logger.get_recent_logs(limit=limit, action=action)
    return {"logs": logs}


@router.get("/rate-limits")
async def get_rate_limit_info(
    request: Request,
    user: dict = Depends(require_auth)
):
    """Get current rate limit status"""
    from security import rate_limiter

    client_ip = request.client.host if request.client else "unknown"

    return {
        "default": rate_limiter.get_usage(client_ip, "default"),
        "grade": rate_limiter.get_usage(client_ip, "grade"),
        "upload": rate_limiter.get_usage(client_ip, "upload")
    }


# =============================================================================
# HELPERS
# =============================================================================

def _get_role_scopes(role: str) -> List[str]:
    """Get scopes for a role"""
    scopes = {
        'viewer': ['read'],
        'grader': ['read', 'write', 'grade'],
        'admin': ['read', 'write', 'grade', 'admin']
    }
    return scopes.get(role, ['read'])
