#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 인증 및 보안
==================

이 파일은 FastAPI에서 인증과 보안을 구현하는 방법을
상세히 설명하고 실용적인 예제를 제공합니다.

주요 보안 기능:
1. JWT 토큰 인증
2. OAuth2 인증
3. 비밀번호 해싱
4. 세션 관리
5. CORS 설정
6. 요청 제한
7. 입력 검증
8. SQL 인젝션 방지
9. XSS 방지
10. CSRF 보호
"""

import asyncio
import logging
import secrets
import hashlib
import hmac
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    Request,
    Response,
    BackgroundTasks,
    Form,
    Cookie,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field, validator, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import uvicorn


# ============================================================================
# 1. 로깅 설정
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 2. 보안 설정
# ============================================================================

# JWT 설정
SECRET_KEY = "your-secret-key-change-in-production"  # 실제 운영에서는 환경변수 사용
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 보안 헤더 설정
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


# ============================================================================
# 3. 보안 미들웨어
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 추가 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 보안 헤더 추가
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """속도 제한 미들웨어"""

    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = datetime.now()

        # 1분 이전 요청 기록 제거
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time
                for req_time in self.requests[client_ip]
                if (now - req_time).total_seconds() < 60
            ]
        else:
            self.requests[client_ip] = []

        # 요청 수 확인
        if len(self.requests[client_ip]) >= self.calls_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"message": "Too Many Requests", "retry_after": 60},
            )

        # 요청 기록 추가
        self.requests[client_ip].append(now)

        response = await call_next(request)
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF 보호 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        # CSRF 토큰 생성 (GET 요청에만)
        if request.method == "GET":
            csrf_token = secrets.token_urlsafe(32)
            # 세션에 CSRF 토큰 저장 (실제로는 세션 스토어 사용)
            request.state.csrf_token = csrf_token

        # POST, PUT, DELETE 요청에 대해 CSRF 토큰 검증
        elif request.method in ["POST", "PUT", "DELETE"]:
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"message": "CSRF token missing"},
                )
            # 실제로는 세션에서 토큰 검증

        response = await call_next(request)
        return response


# ============================================================================
# 4. 인증 관련 유틸리티 함수
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """리프레시 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """토큰 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    """CSRF 토큰 생성"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """API 키 해싱"""
    return hashlib.sha256(api_key.encode()).hexdigest()


# ============================================================================
# 5. 사용자 모델 및 데이터 저장소
# ============================================================================


class User(BaseModel):
    """사용자 모델"""

    id: int
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    role: str = "user"
    created_at: datetime
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    """사용자 생성 모델"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @validator("password")
    def validate_password(cls, v):
        """비밀번호 강도 검증"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호는 대문자를 포함해야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호는 소문자를 포함해야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호는 숫자를 포함해야 합니다")
        return v


class UserLogin(BaseModel):
    """사용자 로그인 모델"""

    username: str
    password: str


class Token(BaseModel):
    """토큰 모델"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """토큰 데이터 모델"""

    username: Optional[str] = None


class PasswordChange(BaseModel):
    """비밀번호 변경 모델"""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @validator("new_password")
    def validate_new_password(cls, v):
        """새 비밀번호 강도 검증"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호는 대문자를 포함해야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호는 소문자를 포함해야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호는 숫자를 포함해야 합니다")
        return v


class APIKey(BaseModel):
    """API 키 모델"""

    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(default_factory=list)


class APIKeyResponse(BaseModel):
    """API 키 응답 모델"""

    key_id: str
    api_key: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


# 인메모리 데이터 저장소 (실제로는 데이터베이스 사용)
users_db: Dict[int, User] = {}
user_counter = 1
api_keys_db: Dict[str, dict] = {}
sessions_db: Dict[str, dict] = {}


# ============================================================================
# 6. 인증 의존성
# ============================================================================


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """현재 사용자 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    # 사용자 조회
    user = None
    for u in users_db.values():
        if u.username == username:
            user = u
            break

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """활성 사용자 조회"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """인증된 사용자 조회"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User not verified"
        )
    return current_user


async def require_role(required_role: str):
    """특정 역할이 필요한 의존성 팩토리"""

    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return current_user

    return role_checker


# ============================================================================
# 7. API 키 인증
# ============================================================================


def verify_api_key(api_key: str) -> Optional[dict]:
    """API 키 검증"""
    hashed_key = hash_api_key(api_key)
    return api_keys_db.get(hashed_key)


async def get_api_key_user(api_key: str = Depends(HTTPBearer())) -> dict:
    """API 키로 인증된 사용자 조회"""
    key_data = verify_api_key(api_key.credentials)
    if key_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return key_data


# ============================================================================
# 8. 세션 관리
# ============================================================================


def create_session(user_id: int) -> str:
    """세션 생성"""
    session_id = secrets.token_urlsafe(32)
    sessions_db[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "last_activity": datetime.now(),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """세션 조회"""
    return sessions_db.get(session_id)


def update_session_activity(session_id: str):
    """세션 활동 업데이트"""
    if session_id in sessions_db:
        sessions_db[session_id]["last_activity"] = datetime.now()


def delete_session(session_id: str):
    """세션 삭제"""
    if session_id in sessions_db:
        del sessions_db[session_id]


# ============================================================================
# 9. FastAPI 애플리케이션 설정
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info("🔐 FastAPI 인증 및 보안 애플리케이션 시작")

    # 초기 관리자 사용자 생성
    admin_user = User(
        id=user_counter,
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        is_active=True,
        is_verified=True,
        role="admin",
        created_at=datetime.now(),
    )
    users_db[user_counter] = admin_user

    yield

    # 종료 시 실행
    logger.info("🛑 FastAPI 인증 및 보안 애플리케이션 종료")


app = FastAPI(
    title="FastAPI 인증 및 보안 예제",
    description="FastAPI에서 인증과 보안을 구현하는 방법을 보여주는 예제",
    version="1.0.0",
    lifespan=lifespan,
)

# 미들웨어 추가
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=100)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-in-production")

# UTF-8 인코딩 미들웨어 추가
from fastapi import Request
from fastapi.responses import Response


@app.middleware("http")
async def add_utf8_encoding(request: Request, call_next):
    """UTF-8 인코딩 헤더 추가"""
    response = await call_next(request)
    if "content-type" not in response.headers:
        response.headers["content-type"] = "application/json; charset=utf-8"
    elif "charset" not in response.headers.get("content-type", ""):
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            response.headers["content-type"] = f"{content_type}; charset=utf-8"
    return response


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
    ],  # 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 신뢰할 수 있는 호스트 설정
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)


# ============================================================================
# 10. 인증 관련 API
# ============================================================================


@app.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """사용자 등록"""
    global user_counter

    # 사용자명 중복 검사
    for existing_user in users_db.values():
        if existing_user.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # 새 사용자 생성
    new_user = User(
        id=user_counter,
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        is_active=True,
        is_verified=False,  # 이메일 인증 필요
        role="user",
        created_at=datetime.now(),
    )

    users_db[user_counter] = new_user
    user_counter += 1

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
    }


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """사용자 로그인"""
    # 사용자 조회
    user = None
    for u in users_db.values():
        if u.username == form_data.username:
            user = u
            break

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # 로그인 시간 업데이트
    user.last_login = datetime.now()

    # 토큰 생성
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str = Form(...)):
    """토큰 갱신"""
    payload = verify_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # 새 토큰 생성
    access_token = create_access_token(data={"sub": username})
    new_refresh_token = create_refresh_token(data={"sub": username})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@app.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """사용자 로그아웃"""
    # 실제로는 토큰을 블랙리스트에 추가하거나 세션을 삭제
    return {"message": "Successfully logged out"}


# ============================================================================
# 11. 사용자 관리 API
# ============================================================================


@app.get("/me", response_model=dict)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """현재 사용자 정보 조회"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "role": current_user.role,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
    }


@app.put("/me", response_model=dict)
async def update_current_user(
    username: Optional[str] = None,
    email: Optional[EmailStr] = None,
    current_user: User = Depends(get_current_active_user),
):
    """현재 사용자 정보 업데이트"""
    if username:
        # 사용자명 중복 검사
        for u in users_db.values():
            if u.username == username and u.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )
        current_user.username = username

    if email:
        # 이메일 중복 검사
        for u in users_db.values():
            if u.email == email and u.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already taken",
                )
        current_user.email = email

    return {
        "message": "User updated successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
    }


@app.post("/change-password", response_model=dict)
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
):
    """비밀번호 변경"""
    # 현재 비밀번호 확인
    if not verify_password(
        password_change.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # 새 비밀번호 설정
    current_user.hashed_password = get_password_hash(password_change.new_password)

    return {"message": "Password changed successfully"}


# ============================================================================
# 12. 관리자 API
# ============================================================================


@app.get("/admin/users", response_model=List[dict])
async def get_all_users(admin_user: User = Depends(require_role("admin"))):
    """모든 사용자 조회 (관리자만)"""
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }
        for user in users_db.values()
    ]


@app.put("/admin/users/{user_id}/verify", response_model=dict)
async def verify_user(user_id: int, admin_user: User = Depends(require_role("admin"))):
    """사용자 인증 (관리자만)"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user = users_db[user_id]
    user.is_verified = True

    return {"message": f"User {user.username} has been verified"}


@app.put("/admin/users/{user_id}/role", response_model=dict)
async def change_user_role(
    user_id: int, new_role: str, admin_user: User = Depends(require_role("admin"))
):
    """사용자 역할 변경 (관리자만)"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if new_role not in ["user", "moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role"
        )

    user = users_db[user_id]
    user.role = new_role

    return {"message": f"User {user.username} role changed to {new_role}"}


# ============================================================================
# 13. API 키 관리
# ============================================================================


@app.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key: APIKey, current_user: User = Depends(get_current_active_user)
):
    """API 키 생성"""
    # API 키 생성
    key_value = secrets.token_urlsafe(32)
    key_id = secrets.token_urlsafe(16)

    # API 키 저장
    api_keys_db[hash_api_key(key_value)] = {
        "key_id": key_id,
        "name": api_key.name,
        "user_id": current_user.id,
        "permissions": api_key.permissions,
        "created_at": datetime.now(),
        "expires_at": None,
    }

    return APIKeyResponse(
        key_id=key_id,
        api_key=key_value,
        name=api_key.name,
        permissions=api_key.permissions,
        created_at=datetime.now(),
        expires_at=None,
    )


@app.get("/api-keys", response_model=List[dict])
async def get_api_keys(current_user: User = Depends(get_current_active_user)):
    """API 키 목록 조회"""
    user_api_keys = []
    for key_data in api_keys_db.values():
        if key_data["user_id"] == current_user.id:
            user_api_keys.append(
                {
                    "key_id": key_data["key_id"],
                    "name": key_data["name"],
                    "permissions": key_data["permissions"],
                    "created_at": key_data["created_at"],
                    "expires_at": key_data["expires_at"],
                }
            )

    return user_api_keys


@app.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str, current_user: User = Depends(get_current_active_user)
):
    """API 키 삭제"""
    # API 키 찾기
    for hashed_key, key_data in api_keys_db.items():
        if key_data["key_id"] == key_id and key_data["user_id"] == current_user.id:
            del api_keys_db[hashed_key]
            return {"message": "API key deleted successfully"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
    )


# ============================================================================
# 14. 세션 관리 API
# ============================================================================


@app.post("/sessions", response_model=dict)
async def create_session(
    username: str = Form(...), password: str = Form(...), response: Response = None
):
    """세션 생성 (쿠키 기반)"""
    # 사용자 인증
    user = None
    for u in users_db.values():
        if u.username == username:
            user = u
            break

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # 세션 생성
    session_id = create_session(user.id)

    # 쿠키 설정
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,  # HTTPS에서만 전송
        samesite="strict",
    )

    return {"message": "Session created successfully"}


@app.get("/sessions/me", response_model=dict)
async def get_session_user(session_id: str = Cookie(None)):
    """세션 사용자 조회"""
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No session found"
        )

    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )

    # 세션 활동 업데이트
    update_session_activity(session_id)

    user = users_db[session["user_id"]]
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


@app.delete("/sessions")
async def delete_session_endpoint(
    session_id: str = Cookie(None), response: Response = None
):
    """세션 삭제"""
    if session_id:
        delete_session(session_id)
        response.delete_cookie("session_id")

    return {"message": "Session deleted successfully"}


# ============================================================================
# 15. 보안 테스트 API
# ============================================================================


@app.get("/security-test")
async def security_test(current_user: User = Depends(get_current_active_user)):
    """보안 테스트 엔드포인트"""
    return {
        "message": "Security test passed",
        "user": current_user.username,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/admin-test")
async def admin_test(admin_user: User = Depends(require_role("admin"))):
    """관리자 테스트 엔드포인트"""
    return {
        "message": "Admin access granted",
        "admin": admin_user.username,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api-key-test")
async def api_key_test(api_user: dict = Depends(get_api_key_user)):
    """API 키 테스트 엔드포인트"""
    return {
        "message": "API key authentication successful",
        "key_name": api_user["name"],
        "permissions": api_user["permissions"],
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# 16. 에러 핸들링
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """값 오류 처리"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid input",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat(),
        },
    )


# ============================================================================
# 17. 메인 실행 함수
# ============================================================================


def run_auth_server():
    """인증 서버 실행"""
    print("=" * 60)
    print("FastAPI 인증 및 보안 서버 시작")
    print("=" * 60)
    print("🔐 보안 기능:")
    print("1. JWT 토큰 인증")
    print("2. OAuth2 인증")
    print("3. 비밀번호 해싱")
    print("4. 세션 관리")
    print("5. API 키 인증")
    print("6. CORS 설정")
    print("7. 요청 제한")
    print("8. 보안 헤더")
    print("9. CSRF 보호")
    print("=" * 60)
    print("🌐 서버 주소:")
    print("   - API 문서: http://localhost:8003/docs")
    print("   - 테스트 계정: admin / AdminPassword123!")
    print("=" * 60)

    uvicorn.run(
        "06_fastapi_auth_security:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_auth_server()
