#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI와 데이터베이스 연동
========================

이 파일은 FastAPI와 다양한 데이터베이스의 연동 방법을
상세히 설명하고 실용적인 예제를 제공합니다.

지원하는 데이터베이스:
1. SQLite (개발/테스트용)
2. PostgreSQL (프로덕션용)
3. MySQL (대안 프로덕션용)
4. MongoDB (NoSQL)
5. Redis (캐시/세션)

주요 기능:
- SQLAlchemy ORM
- 비동기 데이터베이스 작업
- 데이터베이스 마이그레이션
- 연결 풀링
- 트랜잭션 관리
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, date
from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, EmailStr
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Float,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import uvicorn

# MongoDB 관련 (선택적)
try:
    from motor.motor_asyncio import AsyncIOMotorClient

    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# Redis 관련 (선택적)
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ============================================================================
# 1. 로깅 설정
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 2. 데이터베이스 설정
# ============================================================================

# SQLite 설정 (개발용)
SQLITE_DATABASE_URL = "sqlite:///./fastapi_database.db"
SQLITE_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./fastapi_async_database.db"

# PostgreSQL 설정 (프로덕션용)
POSTGRES_DATABASE_URL = "postgresql://user:password@localhost/fastapi_db"
POSTGRES_ASYNC_DATABASE_URL = "postgresql+asyncpg://user:password@localhost/fastapi_db"

# MySQL 설정 (대안)
MYSQL_DATABASE_URL = "mysql+pymysql://user:password@localhost/fastapi_db"
MYSQL_ASYNC_DATABASE_URL = "mysql+aiomysql://user:password@localhost/fastapi_db"

# MongoDB 설정
MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DATABASE = "fastapi_db"

# Redis 설정
REDIS_URL = "redis://localhost:6379"


# ============================================================================
# 3. SQLAlchemy 모델 정의
# ============================================================================

Base = declarative_base()


class User(Base):
    """사용자 모델"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship(
        "Comment", back_populates="author", cascade="all, delete-orphan"
    )


class Post(Base):
    """게시글 모델"""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 외래키
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 관계 설정
    author = relationship("User", back_populates="posts")
    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )


class Comment(Base):
    """댓글 모델"""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 외래키
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    # 관계 설정
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")


class Product(Base):
    """상품 모델"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# 4. 데이터베이스 엔진 및 세션 설정
# ============================================================================

# 동기 데이터베이스 엔진 (SQLite)
engine = create_engine(
    SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}  # SQLite 전용
)

# 비동기 데이터베이스 엔진 (SQLite)
async_engine = create_async_engine(
    SQLITE_ASYNC_DATABASE_URL, echo=True  # SQL 쿼리 로깅
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


# ============================================================================
# 5. 데이터베이스 의존성
# ============================================================================


def get_db():
    """동기 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """비동기 데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============================================================================
# 6. MongoDB 설정 (선택적)
# ============================================================================

if MONGODB_AVAILABLE:

    class MongoDBManager:
        """MongoDB 관리자"""

        def __init__(self):
            self.client = None
            self.database = None

        async def connect(self):
            """MongoDB 연결"""
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.database = self.client[MONGODB_DATABASE]
            logger.info("MongoDB 연결됨")

        async def disconnect(self):
            """MongoDB 연결 해제"""
            if self.client:
                self.client.close()
                logger.info("MongoDB 연결 해제됨")

        def get_collection(self, collection_name: str):
            """컬렉션 가져오기"""
            return self.database[collection_name]

    mongodb_manager = MongoDBManager()


# ============================================================================
# 7. Redis 설정 (선택적)
# ============================================================================

if REDIS_AVAILABLE:

    class RedisManager:
        """Redis 관리자"""

        def __init__(self):
            self.redis = None

        async def connect(self):
            """Redis 연결"""
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            logger.info("Redis 연결됨")

        async def disconnect(self):
            """Redis 연결 해제"""
            if self.redis:
                await self.redis.close()
                logger.info("Redis 연결 해제됨")

        async def get(self, key: str):
            """값 가져오기"""
            return await self.redis.get(key)

        async def set(self, key: str, value: str, expire: int = None):
            """값 설정"""
            return await self.redis.set(key, value, ex=expire)

        async def delete(self, key: str):
            """값 삭제"""
            return await self.redis.delete(key)

    redis_manager = RedisManager()


# ============================================================================
# 8. Pydantic 모델 정의
# ============================================================================


class UserBase(BaseModel):
    """사용자 기본 모델"""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=120)


class UserCreate(UserBase):
    """사용자 생성 모델"""

    pass


class UserUpdate(BaseModel):
    """사용자 업데이트 모델"""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """사용자 응답 모델"""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    """게시글 기본 모델"""

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    published: bool = False


class PostCreate(PostBase):
    """게시글 생성 모델"""

    pass


class PostUpdate(BaseModel):
    """게시글 업데이트 모델"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None


class PostResponse(PostBase):
    """게시글 응답 모델"""

    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostWithAuthor(PostResponse):
    """작성자 정보가 포함된 게시글 응답 모델"""

    author: UserResponse


class CommentBase(BaseModel):
    """댓글 기본 모델"""

    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """댓글 생성 모델"""

    pass


class CommentResponse(CommentBase):
    """댓글 응답 모델"""

    id: int
    author_id: int
    post_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CommentWithAuthor(CommentResponse):
    """작성자 정보가 포함된 댓글 응답 모델"""

    author: UserResponse


class ProductBase(BaseModel):
    """상품 기본 모델"""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=100)
    stock_quantity: int = Field(0, ge=0)


class ProductCreate(ProductBase):
    """상품 생성 모델"""

    pass


class ProductUpdate(BaseModel):
    """상품 업데이트 모델"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None


class ProductResponse(ProductBase):
    """상품 응답 모델"""

    id: int
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# 9. 데이터베이스 CRUD 작업
# ============================================================================


class UserCRUD:
    """사용자 CRUD 작업"""

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """사용자 생성"""
        db_user = User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        """사용자 조회"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """사용자 목록 조회"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update_user(
        db: Session, user_id: int, user_update: UserUpdate
    ) -> Optional[User]:
        """사용자 업데이트"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            update_data = user_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)
            db_user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_user)
        return db_user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """사용자 삭제"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False


class PostCRUD:
    """게시글 CRUD 작업"""

    @staticmethod
    def create_post(db: Session, post: PostCreate, author_id: int) -> Post:
        """게시글 생성"""
        db_post = Post(**post.dict(), author_id=author_id)
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        return db_post

    @staticmethod
    def get_post(db: Session, post_id: int) -> Optional[Post]:
        """게시글 조회"""
        return db.query(Post).filter(Post.id == post_id).first()

    @staticmethod
    def get_posts(
        db: Session, skip: int = 0, limit: int = 100, published_only: bool = True
    ) -> List[Post]:
        """게시글 목록 조회"""
        query = db.query(Post)
        if published_only:
            query = query.filter(Post.published == True)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_user_posts(
        db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Post]:
        """사용자의 게시글 조회"""
        return (
            db.query(Post)
            .filter(Post.author_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_post(
        db: Session, post_id: int, post_update: PostUpdate
    ) -> Optional[Post]:
        """게시글 업데이트"""
        db_post = db.query(Post).filter(Post.id == post_id).first()
        if db_post:
            update_data = post_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_post, field, value)
            db_post.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_post)
        return db_post

    @staticmethod
    def delete_post(db: Session, post_id: int) -> bool:
        """게시글 삭제"""
        db_post = db.query(Post).filter(Post.id == post_id).first()
        if db_post:
            db.delete(db_post)
            db.commit()
            return True
        return False


class CommentCRUD:
    """댓글 CRUD 작업"""

    @staticmethod
    def create_comment(
        db: Session, comment: CommentCreate, author_id: int, post_id: int
    ) -> Comment:
        """댓글 생성"""
        db_comment = Comment(**comment.dict(), author_id=author_id, post_id=post_id)
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment

    @staticmethod
    def get_comments(
        db: Session, post_id: int, skip: int = 0, limit: int = 100
    ) -> List[Comment]:
        """게시글의 댓글 조회"""
        return (
            db.query(Comment)
            .filter(Comment.post_id == post_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def delete_comment(db: Session, comment_id: int) -> bool:
        """댓글 삭제"""
        db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if db_comment:
            db.delete(db_comment)
            db.commit()
            return True
        return False


class ProductCRUD:
    """상품 CRUD 작업"""

    @staticmethod
    def create_product(db: Session, product: ProductCreate) -> Product:
        """상품 생성"""
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        """상품 조회"""
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def get_products(
        db: Session, skip: int = 0, limit: int = 100, category: Optional[str] = None
    ) -> List[Product]:
        """상품 목록 조회"""
        query = db.query(Product)
        if category:
            query = query.filter(Product.category == category)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_product(
        db: Session, product_id: int, product_update: ProductUpdate
    ) -> Optional[Product]:
        """상품 업데이트"""
        db_product = db.query(Product).filter(Product.id == product_id).first()
        if db_product:
            update_data = product_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_product, field, value)
            db_product.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_product)
        return db_product

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """상품 삭제"""
        db_product = db.query(Product).filter(Product.id == product_id).first()
        if db_product:
            db.delete(db_product)
            db.commit()
            return True
        return False


# ============================================================================
# 10. 비동기 CRUD 작업
# ============================================================================


class AsyncUserCRUD:
    """비동기 사용자 CRUD 작업"""

    @staticmethod
    async def create_user(db: AsyncSession, user: UserCreate) -> User:
        """사용자 생성"""
        db_user = User(**user.dict())
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
        """사용자 조회"""
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_users(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """사용자 목록 조회"""
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def update_user(
        db: AsyncSession, user_id: int, user_update: UserUpdate
    ) -> Optional[User]:
        """사용자 업데이트"""
        result = await db.execute(select(User).filter(User.id == user_id))
        db_user = result.scalar_one_or_none()

        if db_user:
            update_data = user_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)
            db_user.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(db_user)
        return db_user


# ============================================================================
# 11. FastAPI 애플리케이션 설정
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info("🚀 FastAPI 데이터베이스 연동 애플리케이션 시작")

    # 데이터베이스 테이블 생성
    Base.metadata.create_all(bind=engine)
    logger.info("📊 데이터베이스 테이블 생성됨")

    # MongoDB 연결 (선택적)
    if MONGODB_AVAILABLE:
        await mongodb_manager.connect()

    # Redis 연결 (선택적)
    if REDIS_AVAILABLE:
        await redis_manager.connect()

    yield

    # 종료 시 실행
    if MONGODB_AVAILABLE:
        await mongodb_manager.disconnect()

    if REDIS_AVAILABLE:
        await redis_manager.disconnect()

    logger.info("🛑 FastAPI 데이터베이스 연동 애플리케이션 종료")


app = FastAPI(
    title="FastAPI 데이터베이스 연동 예제",
    description="FastAPI와 다양한 데이터베이스의 연동 방법을 보여주는 예제",
    version="1.0.0",
    lifespan=lifespan,
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
# 12. 사용자 관련 API
# ============================================================================


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """사용자 생성"""
    # 이메일 중복 검사
    existing_user = UserCRUD.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 이메일입니다.",
        )

    db_user = UserCRUD.create_user(db, user)
    return db_user


@app.get("/users", response_model=List[UserResponse])
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """사용자 목록 조회"""
    users = UserCRUD.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """특정 사용자 조회"""
    user = UserCRUD.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)
):
    """사용자 정보 업데이트"""
    user = UserCRUD.update_user(db, user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """사용자 삭제"""
    success = UserCRUD.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )


# ============================================================================
# 13. 게시글 관련 API
# ============================================================================


@app.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, author_id: int, db: Session = Depends(get_db)):
    """게시글 생성"""
    # 작성자 존재 확인
    author = UserCRUD.get_user(db, author_id)
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작성자를 찾을 수 없습니다."
        )

    db_post = PostCRUD.create_post(db, post, author_id)
    return db_post


@app.get("/posts", response_model=List[PostResponse])
async def get_posts(
    skip: int = 0,
    limit: int = 100,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    """게시글 목록 조회"""
    posts = PostCRUD.get_posts(
        db, skip=skip, limit=limit, published_only=published_only
    )
    return posts


@app.get("/posts/{post_id}", response_model=PostWithAuthor)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """특정 게시글 조회 (작성자 정보 포함)"""
    post = (
        db.query(Post)
        .options(selectinload(Post.author))
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )
    return post


@app.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """특정 사용자의 게시글 조회"""
    # 사용자 존재 확인
    user = UserCRUD.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )

    posts = PostCRUD.get_user_posts(db, user_id, skip=skip, limit=limit)
    return posts


@app.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int, post_update: PostUpdate, db: Session = Depends(get_db)
):
    """게시글 업데이트"""
    post = PostCRUD.update_post(db, post_id, post_update)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    """게시글 삭제"""
    success = PostCRUD.delete_post(db, post_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )


# ============================================================================
# 14. 댓글 관련 API
# ============================================================================


@app.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: int, comment: CommentCreate, author_id: int, db: Session = Depends(get_db)
):
    """댓글 생성"""
    # 게시글 존재 확인
    post = PostCRUD.get_post(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )

    # 작성자 존재 확인
    author = UserCRUD.get_user(db, author_id)
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작성자를 찾을 수 없습니다."
        )

    db_comment = CommentCRUD.create_comment(db, comment, author_id, post_id)
    return db_comment


@app.get("/posts/{post_id}/comments", response_model=List[CommentWithAuthor])
async def get_post_comments(
    post_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """게시글의 댓글 조회"""
    # 게시글 존재 확인
    post = PostCRUD.get_post(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다."
        )

    comments = (
        db.query(Comment)
        .options(selectinload(Comment.author))
        .filter(Comment.post_id == post_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return comments


# ============================================================================
# 15. 상품 관련 API
# ============================================================================


@app.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """상품 생성"""
    db_product = ProductCRUD.create_product(db, product)
    return db_product


@app.get("/products", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """상품 목록 조회"""
    products = ProductCRUD.get_products(db, skip=skip, limit=limit, category=category)
    return products


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """특정 상품 조회"""
    product = ProductCRUD.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="상품을 찾을 수 없습니다."
        )
    return product


# ============================================================================
# 16. 비동기 API 예제
# ============================================================================


@app.get("/async/users", response_model=List[UserResponse])
async def get_async_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db)
):
    """비동기 사용자 목록 조회"""
    users = await AsyncUserCRUD.get_users(db, skip=skip, limit=limit)
    return users


# ============================================================================
# 17. MongoDB API 예제 (선택적)
# ============================================================================

if MONGODB_AVAILABLE:

    @app.post("/mongodb/documents")
    async def create_mongodb_document(
        collection_name: str, document: dict, background_tasks: BackgroundTasks
    ):
        """MongoDB 문서 생성"""
        collection = mongodb_manager.get_collection(collection_name)
        result = await collection.insert_one(document)

        # 백그라운드 작업으로 인덱싱
        background_tasks.add_task(
            create_index_if_not_exists, collection_name, "created_at"
        )

        return {
            "message": "문서가 생성되었습니다.",
            "document_id": str(result.inserted_id),
        }

    @app.get("/mongodb/documents/{collection_name}")
    async def get_mongodb_documents(
        collection_name: str, skip: int = 0, limit: int = 100
    ):
        """MongoDB 문서 조회"""
        collection = mongodb_manager.get_collection(collection_name)
        cursor = collection.find().skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)

        return {"documents": documents, "total": len(documents)}

    async def create_index_if_not_exists(collection_name: str, field: str):
        """인덱스 생성 (백그라운드 작업)"""
        collection = mongodb_manager.get_collection(collection_name)
        await collection.create_index(field)
        logger.info(f"인덱스 생성됨: {collection_name}.{field}")


# ============================================================================
# 18. Redis API 예제 (선택적)
# ============================================================================

if REDIS_AVAILABLE:

    @app.post("/redis/cache")
    async def set_redis_cache(key: str, value: str, expire: int = 300):
        """Redis 캐시 설정"""
        await redis_manager.set(key, value, expire)
        return {"message": f"캐시 '{key}'가 설정되었습니다."}

    @app.get("/redis/cache/{key}")
    async def get_redis_cache(key: str):
        """Redis 캐시 조회"""
        value = await redis_manager.get(key)
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="캐시를 찾을 수 없습니다."
            )
        return {"key": key, "value": value}


# ============================================================================
# 19. 메인 실행 함수
# ============================================================================


def run_database_server():
    """데이터베이스 서버 실행"""
    print("=" * 60)
    print("FastAPI 데이터베이스 연동 서버 시작")
    print("=" * 60)
    print("🗄️ 지원하는 데이터베이스:")
    print("1. SQLite (개발/테스트용)")
    print("2. PostgreSQL (프로덕션용)")
    print("3. MySQL (대안 프로덕션용)")
    if MONGODB_AVAILABLE:
        print("4. MongoDB (NoSQL)")
    if REDIS_AVAILABLE:
        print("5. Redis (캐시/세션)")
    print("=" * 60)
    print("🌐 서버 주소:")
    print("   - API 문서: http://localhost:8002/docs")
    print("   - 데이터베이스: SQLite (./fastapi_database.db)")
    print("=" * 60)

    uvicorn.run(
        "06_fastapi_database:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_database_server()
