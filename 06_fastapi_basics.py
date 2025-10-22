#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 기초부터 고급까지
========================

이 파일은 FastAPI를 사용한 웹 API 개발에 대한
기초부터 고급 사용법까지 상세히 설명하고 예제를 제공합니다.

FastAPI란?
- Python 3.7+ 기반의 현대적이고 빠른 웹 프레임워크
- 자동 API 문서 생성 (Swagger UI, ReDoc)
- 타입 힌트 기반 자동 검증
- 비동기 지원으로 높은 성능
- OpenAPI 표준 준수

주요 특징:
- 자동 문서 생성
- 타입 안전성
- 비동기 지원
- 높은 성능
- 직관적인 API 설계
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import asyncio
import json
from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Query,
    Body,
    Header,
    Cookie,
    Form,
    File,
    UploadFile,
)
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator, EmailStr
import uvicorn


# ============================================================================
# 1. 기본 FastAPI 애플리케이션
# ============================================================================

# FastAPI 인스턴스 생성
app = FastAPI(
    title="FastAPI 학습 예제",
    description="FastAPI 기초부터 고급까지 학습하는 예제 API",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 경로
    redoc_url="/redoc",  # ReDoc 경로
)

# CORS 미들웨어 추가 (크로스 오리진 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ============================================================================
# 2. Pydantic 모델 정의
# ============================================================================


class UserRole(str, Enum):
    """사용자 역할 열거형"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserBase(BaseModel):
    """사용자 기본 모델"""

    name: str = Field(..., min_length=2, max_length=50, description="사용자 이름")
    email: EmailStr = Field(..., description="이메일 주소")
    age: int = Field(..., ge=0, le=120, description="나이")
    is_active: bool = Field(True, description="활성 상태")


class UserCreate(UserBase):
    """사용자 생성 모델"""

    password: str = Field(..., min_length=8, description="비밀번호")
    role: UserRole = Field(UserRole.USER, description="사용자 역할")

    @validator("password")
    def validate_password(cls, v):
        """비밀번호 검증"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호는 대문자를 포함해야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호는 소문자를 포함해야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호는 숫자를 포함해야 합니다")
        return v


class UserUpdate(BaseModel):
    """사용자 업데이트 모델"""

    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """사용자 응답 모델"""

    id: int = Field(..., description="사용자 ID")
    role: UserRole = Field(..., description="사용자 역할")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: Optional[datetime] = Field(None, description="수정 시간")

    class Config:
        """Pydantic 설정"""

        orm_mode = True  # ORM 모델과 호환
        json_encoders = {datetime: lambda v: v.isoformat()}


class ItemBase(BaseModel):
    """아이템 기본 모델"""

    name: str = Field(..., min_length=1, max_length=100, description="아이템 이름")
    description: Optional[str] = Field(None, max_length=500, description="설명")
    price: float = Field(..., gt=0, description="가격")
    category: str = Field(..., description="카테고리")
    tags: List[str] = Field(default_factory=list, description="태그 목록")


class ItemCreate(ItemBase):
    """아이템 생성 모델"""

    pass


class ItemUpdate(BaseModel):
    """아이템 업데이트 모델"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ItemResponse(ItemBase):
    """아이템 응답 모델"""

    id: int = Field(..., description="아이템 ID")
    owner_id: int = Field(..., description="소유자 ID")
    created_at: datetime = Field(..., description="생성 시간")
    is_available: bool = Field(True, description="사용 가능 여부")

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MessageResponse(BaseModel):
    """메시지 응답 모델"""

    message: str = Field(..., description="응답 메시지")
    status: str = Field(..., description="상태")
    data: Optional[Any] = Field(None, description="응답 데이터")


# ============================================================================
# 3. 인메모리 데이터 저장소 (실제 프로젝트에서는 데이터베이스 사용)
# ============================================================================

# 사용자 데이터 저장소
users_db: Dict[int, UserResponse] = {}
user_counter = 1

# 아이템 데이터 저장소
items_db: Dict[int, ItemResponse] = {}
item_counter = 1


# 초기 데이터 생성
def create_initial_data():
    """초기 데이터 생성"""
    global user_counter, item_counter

    # 초기 사용자 생성
    admin_user = UserResponse(
        id=user_counter,
        name="관리자",
        email="admin@example.com",
        age=30,
        is_active=True,
        role=UserRole.ADMIN,
        created_at=datetime.now(),
        updated_at=None,
    )
    users_db[user_counter] = admin_user
    user_counter += 1

    # 초기 아이템 생성
    sample_item = ItemResponse(
        id=item_counter,
        name="샘플 아이템",
        description="FastAPI 학습용 샘플 아이템입니다.",
        price=10000.0,
        category="학습용",
        tags=["fastapi", "python", "웹개발"],
        owner_id=1,
        created_at=datetime.now(),
        is_available=True,
    )
    items_db[item_counter] = sample_item
    item_counter += 1


# ============================================================================
# 4. 기본 라우트 정의
# ============================================================================


@app.get("/", response_model=MessageResponse)
async def root():
    """루트 엔드포인트"""
    return MessageResponse(
        message="FastAPI 학습 예제에 오신 것을 환영합니다!",
        status="success",
        data={"docs": "/docs", "redoc": "/redoc", "version": "1.0.0"},
    )


@app.get("/health", response_model=MessageResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return MessageResponse(
        message="서버가 정상적으로 작동 중입니다.",
        status="healthy",
        data={"timestamp": datetime.now().isoformat(), "uptime": "running"},
    )


# ============================================================================
# 5. 사용자 관련 API
# ============================================================================


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """새 사용자 생성"""
    global user_counter

    # 이메일 중복 검사
    for existing_user in users_db.values():
        if existing_user.email == user.email:
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    # 새 사용자 생성
    new_user = UserResponse(
        id=user_counter,
        name=user.name,
        email=user.email,
        age=user.age,
        is_active=user.is_active,
        role=user.role,
        created_at=datetime.now(),
        updated_at=None,
    )

    users_db[user_counter] = new_user
    user_counter += 1

    return new_user


@app.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 항목 수"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    role: Optional[UserRole] = Query(None, description="역할 필터"),
):
    """사용자 목록 조회"""
    filtered_users = list(users_db.values())

    # 필터 적용
    if is_active is not None:
        filtered_users = [u for u in filtered_users if u.is_active == is_active]

    if role is not None:
        filtered_users = [u for u in filtered_users if u.role == role]

    # 페이지네이션 적용
    start = skip
    end = skip + limit
    paginated_users = filtered_users[start:end]

    return paginated_users


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int = Path(..., gt=0, description="사용자 ID")):
    """특정 사용자 조회"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return users_db[user_id]


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int = Path(..., gt=0, description="사용자 ID"),
    user_update: UserUpdate = Body(..., description="업데이트할 사용자 정보"),
):
    """사용자 정보 업데이트"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    existing_user = users_db[user_id]

    # 업데이트할 필드만 적용
    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_user, field, value)

    existing_user.updated_at = datetime.now()

    return existing_user


@app.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: int = Path(..., gt=0, description="사용자 ID")):
    """사용자 삭제"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    del users_db[user_id]

    return MessageResponse(
        message=f"사용자 ID {user_id}가 삭제되었습니다.", status="success"
    )


# ============================================================================
# 6. 아이템 관련 API
# ============================================================================


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    item: ItemCreate, owner_id: int = Body(..., description="소유자 ID")
):
    """새 아이템 생성"""
    global item_counter

    # 소유자 존재 확인
    if owner_id not in users_db:
        raise HTTPException(status_code=404, detail="소유자를 찾을 수 없습니다.")

    # 새 아이템 생성
    new_item = ItemResponse(
        id=item_counter,
        name=item.name,
        description=item.description,
        price=item.price,
        category=item.category,
        tags=item.tags,
        owner_id=owner_id,
        created_at=datetime.now(),
        is_available=True,
    )

    items_db[item_counter] = new_item
    item_counter += 1

    return new_item


@app.get("/items", response_model=List[ItemResponse])
async def get_items(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 항목 수"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    min_price: Optional[float] = Query(None, ge=0, description="최소 가격"),
    max_price: Optional[float] = Query(None, ge=0, description="최대 가격"),
    is_available: Optional[bool] = Query(None, description="사용 가능 여부"),
):
    """아이템 목록 조회"""
    filtered_items = list(items_db.values())

    # 필터 적용
    if category:
        filtered_items = [i for i in filtered_items if i.category == category]

    if min_price is not None:
        filtered_items = [i for i in filtered_items if i.price >= min_price]

    if max_price is not None:
        filtered_items = [i for i in filtered_items if i.price <= max_price]

    if is_available is not None:
        filtered_items = [i for i in filtered_items if i.is_available == is_available]

    # 페이지네이션 적용
    start = skip
    end = skip + limit
    paginated_items = filtered_items[start:end]

    return paginated_items


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int = Path(..., gt=0, description="아이템 ID")):
    """특정 아이템 조회"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")

    return items_db[item_id]


@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int = Path(..., gt=0, description="아이템 ID"),
    item_update: ItemUpdate = Body(..., description="업데이트할 아이템 정보"),
):
    """아이템 정보 업데이트"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")

    existing_item = items_db[item_id]

    # 업데이트할 필드만 적용
    update_data = item_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_item, field, value)

    return existing_item


@app.delete("/items/{item_id}", response_model=MessageResponse)
async def delete_item(item_id: int = Path(..., gt=0, description="아이템 ID")):
    """아이템 삭제"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")

    del items_db[item_id]

    return MessageResponse(
        message=f"아이템 ID {item_id}가 삭제되었습니다.", status="success"
    )


# ============================================================================
# 7. 고급 기능 예제
# ============================================================================


@app.get("/users/{user_id}/items", response_model=List[ItemResponse])
async def get_user_items(
    user_id: int = Path(..., gt=0, description="사용자 ID"),
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 항목 수"),
):
    """특정 사용자의 아이템 목록 조회"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user_items = [item for item in items_db.values() if item.owner_id == user_id]

    # 페이지네이션 적용
    start = skip
    end = skip + limit
    paginated_items = user_items[start:end]

    return paginated_items


@app.get("/search", response_model=List[UserResponse | ItemResponse])
async def search(
    q: str = Query(..., min_length=1, description="검색어"),
    type: str = Query("all", regex="^(all|users|items)$", description="검색 타입"),
):
    """통합 검색 (Python 3.10 match-case 사용)"""
    results = []

    # Python 3.10 match-case 문법 사용
    match type:
        case "users":
            # 사용자 검색
            for user in users_db.values():
                if q.lower() in user.name.lower() or q.lower() in user.email.lower():
                    results.append(user)
        case "items":
            # 아이템 검색
            for item in items_db.values():
                if (
                    q.lower() in item.name.lower()
                    or q.lower() in item.description.lower()
                    or q.lower() in item.category.lower()
                    or any(q.lower() in tag.lower() for tag in item.tags)
                ):
                    results.append(item)
        case "all":
            # 전체 검색
            for user in users_db.values():
                if q.lower() in user.name.lower() or q.lower() in user.email.lower():
                    results.append(user)
            for item in items_db.values():
                if (
                    q.lower() in item.name.lower()
                    or q.lower() in item.description.lower()
                    or q.lower() in item.category.lower()
                    or any(q.lower() in tag.lower() for tag in item.tags)
                ):
                    results.append(item)
        case _:
            # 기본값 처리
            results = []

    return results


# ============================================================================
# 8. 파일 업로드 예제
# ============================================================================


@app.post("/upload", response_model=MessageResponse)
async def upload_file(
    file: UploadFile = File(..., description="업로드할 파일"),
    description: str = Form(..., description="파일 설명"),
):
    """파일 업로드"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    # 파일 크기 제한 (10MB)
    max_size = 10 * 1024 * 1024
    content = await file.read()

    if len(content) > max_size:
        raise HTTPException(
            status_code=413, detail="파일 크기가 너무 큽니다. (최대 10MB)"
        )

    # 파일 정보 반환 (실제로는 파일을 저장)
    return MessageResponse(
        message="파일이 성공적으로 업로드되었습니다.",
        status="success",
        data={
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "description": description,
        },
    )


# ============================================================================
# 9. 비동기 작업 예제
# ============================================================================


@app.post("/users/{user_id}/send-email", response_model=MessageResponse)
async def send_email_to_user(user_id: int = Path(..., gt=0, description="사용자 ID")):
    """사용자에게 이메일 전송 (비동기 작업 시뮬레이션)"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user = users_db[user_id]

    # 이메일 전송 시뮬레이션 (실제로는 이메일 서비스 사용)
    await asyncio.sleep(1)  # 비동기 작업 시뮬레이션

    return MessageResponse(
        message=f"{user.name}님에게 이메일이 전송되었습니다.",
        status="success",
        data={"recipient": user.email, "sent_at": datetime.now().isoformat()},
    )


# ============================================================================
# 10. 커스텀 응답 예제
# ============================================================================


@app.get("/custom-response", response_class=HTMLResponse)
async def custom_html_response():
    """커스텀 HTML 응답"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI 학습 예제</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { color: #2c3e50; border-bottom: 2px solid #3498db; }
            .content { margin-top: 20px; }
            .api-link { color: #3498db; text-decoration: none; }
            .api-link:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">FastAPI 학습 예제</h1>
            <div class="content">
                <h2>사용 가능한 API 엔드포인트:</h2>
                <ul>
                    <li><a href="/docs" class="api-link">Swagger UI 문서</a></li>
                    <li><a href="/redoc" class="api-link">ReDoc 문서</a></li>
                    <li><a href="/users" class="api-link">사용자 목록</a></li>
                    <li><a href="/items" class="api-link">아이템 목록</a></li>
                    <li><a href="/health" class="api-link">헬스 체크</a></li>
                </ul>
                <p>FastAPI의 자동 문서 생성 기능을 확인해보세요!</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ============================================================================
# 11. 에러 핸들링
# ============================================================================


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """ValueError 예외 처리"""
    return JSONResponse(
        status_code=400,
        content={
            "message": "잘못된 값이 입력되었습니다.",
            "detail": str(exc),
            "status": "error",
        },
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 에러 처리"""
    return JSONResponse(
        status_code=404,
        content={"message": "요청한 리소스를 찾을 수 없습니다.", "status": "error"},
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


# ============================================================================
# 12. 애플리케이션 시작/종료 이벤트
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print("🚀 FastAPI 애플리케이션이 시작되었습니다!")
    create_initial_data()
    print("📊 초기 데이터가 생성되었습니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("🛑 FastAPI 애플리케이션이 종료되었습니다.")


# ============================================================================
# 13. 메인 실행 함수
# ============================================================================


def run_server():
    """서버 실행"""
    print("=" * 60)
    print("FastAPI 학습 예제 서버 시작")
    print("=" * 60)
    print("📚 학습할 내용:")
    print("1. 기본 API 엔드포인트")
    print("2. Pydantic 모델과 타입 검증")
    print("3. 경로 매개변수와 쿼리 매개변수")
    print("4. 요청/응답 모델")
    print("5. 에러 핸들링")
    print("6. 파일 업로드")
    print("7. 비동기 작업")
    print("8. 커스텀 응답")
    print("=" * 60)
    print("🌐 서버 주소:")
    print("   - API 문서: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print("   - 기본 엔드포인트: http://localhost:8000/")
    print("=" * 60)

    uvicorn.run(
        "06_fastapi_basics:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드에서 자동 재시작
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
