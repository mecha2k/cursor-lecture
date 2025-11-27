#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic 완전 가이드
==================

이 파일은 Pydantic 라이브러리에 대한 기초부터 고급 사용법까지
상세히 설명하고 실용적인 예제를 제공합니다.

Pydantic이란?
- Python 타입 힌트를 사용한 데이터 검증 라이브러리
- 런타임 데이터 검증 및 직렬화/역직렬화
- FastAPI의 핵심 의존성
- JSON 스키마 자동 생성
- 타입 안전성 보장

주요 특징:
- 타입 힌트 기반 검증
- 자동 데이터 변환
- 상세한 에러 메시지
- JSON 스키마 생성
- FastAPI와 완벽한 통합
"""

from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
import json
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    computed_field,
    ConfigDict,
    EmailStr,
    HttpUrl,
    PastDate,
    FutureDate,
    PositiveInt,
    NegativeInt,
    PositiveFloat,
    NegativeFloat,
    SecretStr,
    SecretBytes,
    ValidationError,
    ValidationInfo,
    FieldValidationInfo,
)
from pydantic_settings import BaseSettings
import uvicorn
from fastapi import FastAPI, HTTPException


# ============================================================================
# 1. Pydantic 기초
# ============================================================================


class BasicUser(BaseModel):
    """기본 사용자 모델 - 가장 간단한 형태"""

    name: str
    age: int
    email: str


def demonstrate_basic_usage():
    """기본 사용법 데모"""
    print("=" * 60)
    print("1. Pydantic 기초 사용법")
    print("=" * 60)

    # 1. 딕셔너리에서 모델 생성
    user_data = {"name": "홍길동", "age": 30, "email": "hong@example.com"}
    user = BasicUser(**user_data)
    print(f"딕셔너리에서 생성: {user}")

    # 2. JSON에서 모델 생성
    json_data = '{"name": "김철수", "age": 25, "email": "kim@example.com"}'
    user = BasicUser.model_validate_json(json_data)
    print(f"JSON에서 생성: {user}")

    # 3. 모델을 딕셔너리로 변환
    user_dict = user.model_dump()
    print(f"딕셔너리로 변환: {user_dict}")

    # 4. 모델을 JSON으로 변환
    user_json = user.model_dump_json()
    print(f"JSON으로 변환: {user_json}")

    # 5. 타입 검증 (자동 변환)
    user = BasicUser(name="이영희", age="28", email="lee@example.com")
    print(f"문자열 '28'이 자동으로 int로 변환: {user.age} (타입: {type(user.age)})")

    # 6. 검증 실패 예제
    try:
        user = BasicUser(name="박민수", age="not_a_number", email="park@example.com")
    except ValidationError as e:
        print(f"\n검증 실패 예제:")
        print(e.json(indent=2))


# ============================================================================
# 2. 필드 검증 (Field)
# ============================================================================


class ValidatedUser(BaseModel):
    """검증이 포함된 사용자 모델"""

    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="사용자 이름 (2-50자)",
        examples=["홍길동", "김철수"],
    )
    age: int = Field(
        ...,
        ge=0,
        le=120,
        description="나이 (0-120세)",
        examples=[25, 30, 45],
    )
    email: EmailStr = Field(..., description="이메일 주소")
    salary: Optional[float] = Field(
        None,
        gt=0,
        description="급여 (양수만 허용)",
        examples=[3000.0, 5000.0],
    )


def demonstrate_field_validation():
    """필드 검증 데모"""
    print("\n" + "=" * 60)
    print("2. 필드 검증 (Field)")
    print("=" * 60)

    # 정상적인 데이터
    user = ValidatedUser(
        name="홍길동",
        age=30,
        email="hong@example.com",
        salary=5000.0,
    )
    print(f"정상 데이터: {user}")

    # 검증 실패 예제들
    print("\n검증 실패 예제:")

    # 이름이 너무 짧음
    try:
        user = ValidatedUser(name="홍", age=30, email="hong@example.com")
    except ValidationError as e:
        print("1. 이름이 너무 짧음:")
        print(f"   {e.errors()[0]['msg']}")

    # 나이가 범위를 벗어남
    try:
        user = ValidatedUser(name="홍길동", age=150, email="hong@example.com")
    except ValidationError as e:
        print("2. 나이가 범위를 벗어남:")
        print(f"   {e.errors()[0]['msg']}")

    # 이메일 형식 오류
    try:
        user = ValidatedUser(name="홍길동", age=30, email="invalid-email")
    except ValidationError as e:
        print("3. 이메일 형식 오류:")
        print(f"   {e.errors()[0]['msg']}")

    # 급여가 음수
    try:
        user = ValidatedUser(
            name="홍길동", age=30, email="hong@example.com", salary=-1000.0
        )
    except ValidationError as e:
        print("4. 급여가 음수:")
        print(f"   {e.errors()[0]['msg']}")


# ============================================================================
# 3. 커스텀 검증 (field_validator)
# ============================================================================


class CustomValidatedUser(BaseModel):
    """커스텀 검증이 포함된 사용자 모델"""

    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)
    email: EmailStr
    phone: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """사용자명 검증: 영문, 숫자, 언더스코어만 허용"""
        if not v.replace("_", "").isalnum():
            raise ValueError("사용자명은 영문, 숫자, 언더스코어만 사용할 수 있습니다")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """비밀번호 검증: 대소문자, 숫자, 특수문자 포함"""
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호에 대문자가 포함되어야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호에 소문자가 포함되어야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에 숫자가 포함되어야 합니다")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("비밀번호에 특수문자가 포함되어야 합니다")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """전화번호 검증: 숫자와 하이픈만 허용"""
        cleaned = v.replace("-", "").replace(" ", "")
        if not cleaned.isdigit():
            raise ValueError("전화번호는 숫자와 하이픈만 사용할 수 있습니다")
        if len(cleaned) not in [10, 11]:
            raise ValueError("전화번호는 10자리 또는 11자리여야 합니다")
        return cleaned


def demonstrate_custom_validation():
    """커스텀 검증 데모"""
    print("\n" + "=" * 60)
    print("3. 커스텀 검증 (field_validator)")
    print("=" * 60)

    # 정상적인 데이터
    user = CustomValidatedUser(
        username="john_doe",
        password="SecurePass123!",
        email="john@example.com",
        phone="010-1234-5678",
    )
    print(f"정상 데이터: {user}")

    # 검증 실패 예제들
    print("\n커스텀 검증 실패 예제:")

    # 사용자명에 특수문자 포함
    try:
        user = CustomValidatedUser(
            username="john@doe",
            password="SecurePass123!",
            email="john@example.com",
            phone="010-1234-5678",
        )
    except ValidationError as e:
        print("1. 사용자명 검증 실패:")
        print(f"   {e.errors()[0]['msg']}")

    # 비밀번호에 대문자 없음
    try:
        user = CustomValidatedUser(
            username="john_doe",
            password="securepass123!",
            email="john@example.com",
            phone="010-1234-5678",
        )
    except ValidationError as e:
        print("2. 비밀번호 검증 실패:")
        print(f"   {e.errors()[0]['msg']}")

    # 전화번호 형식 오류
    try:
        user = CustomValidatedUser(
            username="john_doe",
            password="SecurePass123!",
            email="john@example.com",
            phone="010-12345",
        )
    except ValidationError as e:
        print("3. 전화번호 검증 실패:")
        print(f"   {e.errors()[0]['msg']}")


# ============================================================================
# 4. 모델 검증 (model_validator)
# ============================================================================


class OrderModel(BaseModel):
    """주문 모델 - 모델 레벨 검증"""

    item_count: int = Field(..., gt=0)
    total_price: float = Field(..., gt=0)
    discount: float = Field(0.0, ge=0, le=1.0)
    final_price: Optional[float] = None

    @model_validator(mode="after")
    def validate_prices(self) -> "OrderModel":
        """최종 가격 검증: 할인 후 가격이 0보다 커야 함"""
        if self.final_price is None:
            self.final_price = self.total_price * (1 - self.discount)

        if self.final_price <= 0:
            raise ValueError("할인 후 가격은 0보다 커야 합니다")

        if self.final_price > self.total_price:
            raise ValueError("할인 후 가격은 원래 가격보다 클 수 없습니다")

        return self


def demonstrate_model_validation():
    """모델 검증 데모"""
    print("\n" + "=" * 60)
    print("4. 모델 검증 (model_validator)")
    print("=" * 60)

    # 정상적인 주문
    order = OrderModel(item_count=5, total_price=10000.0, discount=0.1)
    print(f"정상 주문: {order}")
    print(f"최종 가격: {order.final_price}원")

    # 검증 실패 예제
    print("\n모델 검증 실패 예제:")

    # 할인율이 100%를 초과
    try:
        order = OrderModel(item_count=5, total_price=10000.0, discount=1.5)
    except ValidationError as e:
        print("1. 할인율 범위 초과:")
        print(f"   {e.errors()[0]['msg']}")


# ============================================================================
# 5. 모델 상속
# ============================================================================


class UserBase(BaseModel):
    """사용자 기본 모델"""

    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    age: int = Field(..., ge=0, le=120)


class UserCreate(UserBase):
    """사용자 생성 모델"""

    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """사용자 응답 모델"""

    id: int
    created_at: datetime
    is_active: bool = True


class UserUpdate(BaseModel):
    """사용자 업데이트 모델 (모든 필드 선택적)"""

    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=120)


def demonstrate_model_inheritance():
    """모델 상속 데모"""
    print("\n" + "=" * 60)
    print("5. 모델 상속")
    print("=" * 60)

    # 사용자 생성
    user_create = UserCreate(
        name="홍길동",
        email="hong@example.com",
        age=30,
        password="SecurePass123!",
    )
    print(f"생성 모델: {user_create}")

    # 사용자 응답
    user_response = UserResponse(
        id=1,
        name="홍길동",
        email="hong@example.com",
        age=30,
        created_at=datetime.now(),
        is_active=True,
    )
    print(f"응답 모델: {user_response}")

    # 사용자 업데이트 (부분 업데이트)
    user_update = UserUpdate(name="홍길동2", age=31)
    print(f"업데이트 모델: {user_update}")


# ============================================================================
# 6. 고급 타입
# ============================================================================


class AdvancedTypesModel(BaseModel):
    """고급 타입 사용 예제"""

    # 리스트 타입
    tags: List[str] = Field(default_factory=list, min_length=0, max_length=10)
    scores: List[int] = Field(..., min_length=1, max_length=5)

    # 옵셔널 타입
    optional_field: Optional[str] = None
    optional_with_default: Optional[int] = Field(default=0)

    # 유니온 타입
    value: Union[int, str, float]

    # 딕셔너리 타입
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 리터럴 타입
    status: Literal["pending", "approved", "rejected"]

    # 중첩 모델
    address: Optional["AddressModel"] = None

    # 날짜/시간 타입
    birth_date: date
    created_at: datetime
    appointment_time: Optional[time] = None


class AddressModel(BaseModel):
    """주소 모델"""

    street: str
    city: str
    postal_code: str
    country: str = "대한민국"


# 순환 참조 해결
AdvancedTypesModel.model_rebuild()


def demonstrate_advanced_types():
    """고급 타입 데모"""
    print("\n" + "=" * 60)
    print("6. 고급 타입")
    print("=" * 60)

    model = AdvancedTypesModel(
        tags=["python", "fastapi", "pydantic"],
        scores=[85, 90, 95, 88, 92],
        value=42,  # int로 자동 인식
        metadata={"version": "1.0", "author": "홍길동"},
        status="approved",
        address=AddressModel(
            street="강남대로 123",
            city="서울",
            postal_code="06000",
        ),
        birth_date=date(1990, 1, 1),
        created_at=datetime.now(),
    )

    print(f"고급 타입 모델: {model}")
    print(f"주소: {model.address}")
    print(f"태그 개수: {len(model.tags)}")
    print(f"평균 점수: {sum(model.scores) / len(model.scores):.2f}")


# ============================================================================
# 7. 계산된 필드 (computed_field)
# ============================================================================


class ProductModel(BaseModel):
    """상품 모델 - 계산된 필드 포함"""

    name: str
    price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    discount_rate: float = Field(0.0, ge=0, le=1.0)

    @computed_field
    @property
    def total_price(self) -> float:
        """총 가격 계산"""
        return self.price * self.quantity

    @computed_field
    @property
    def discounted_price(self) -> float:
        """할인 후 가격 계산"""
        return self.total_price * (1 - self.discount_rate)

    @computed_field
    @property
    def savings(self) -> float:
        """절약 금액 계산"""
        return self.total_price - self.discounted_price


def demonstrate_computed_fields():
    """계산된 필드 데모"""
    print("\n" + "=" * 60)
    print("7. 계산된 필드 (computed_field)")
    print("=" * 60)

    product = ProductModel(
        name="노트북",
        price=1000000.0,
        quantity=2,
        discount_rate=0.15,
    )

    print(f"상품: {product.name}")
    print(f"단가: {product.price:,}원")
    print(f"수량: {product.quantity}개")
    print(f"할인율: {product.discount_rate * 100}%")
    print(f"총 가격: {product.total_price:,}원")
    print(f"할인 후 가격: {product.discounted_price:,}원")
    print(f"절약 금액: {product.savings:,}원")


# ============================================================================
# 8. 설정 관리 (BaseSettings)
# ============================================================================


class AppSettings(BaseSettings):
    """애플리케이션 설정 모델"""

    app_name: str = "My FastAPI App"
    debug: bool = False
    database_url: str
    secret_key: SecretStr
    max_connections: int = Field(10, ge=1, le=100)
    timeout: float = Field(30.0, gt=0)

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def demonstrate_settings():
    """설정 관리 데모"""
    print("\n" + "=" * 60)
    print("8. 설정 관리 (BaseSettings)")
    print("=" * 60)

    # 환경 변수나 .env 파일에서 자동으로 로드
    # 여기서는 예제로 직접 생성
    try:
        settings = AppSettings(
            database_url="postgresql://user:pass@localhost/db",
            secret_key="my-secret-key",
        )
        print(f"앱 이름: {settings.app_name}")
        print(f"디버그 모드: {settings.debug}")
        print(f"데이터베이스 URL: {settings.database_url}")
        print(f"시크릿 키: {settings.secret_key.get_secret_value()}")
        print(f"최대 연결 수: {settings.max_connections}")
        print(f"타임아웃: {settings.timeout}초")
    except ValidationError as e:
        print(f"설정 로드 실패: {e}")


# ============================================================================
# 9. JSON 스키마 생성
# ============================================================================


def demonstrate_json_schema():
    """JSON 스키마 생성 데모"""
    print("\n" + "=" * 60)
    print("9. JSON 스키마 생성")
    print("=" * 60)

    # 모델의 JSON 스키마 생성
    schema = ValidatedUser.model_json_schema()
    print("ValidatedUser 모델의 JSON 스키마:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))


# ============================================================================
# 10. FastAPI와의 통합
# ============================================================================


# FastAPI 앱 생성
api_app = FastAPI(title="Pydantic 예제 API", version="1.0.0")


@api_app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate) -> UserResponse:
    """사용자 생성 엔드포인트"""
    # 실제로는 데이터베이스에 저장
    return UserResponse(
        id=1,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=datetime.now(),
        is_active=True,
    )


@api_app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """사용자 조회 엔드포인트"""
    # 실제로는 데이터베이스에서 조회
    return UserResponse(
        id=user_id,
        name="홍길동",
        email="hong@example.com",
        age=30,
        created_at=datetime.now(),
        is_active=True,
    )


@api_app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate) -> UserResponse:
    """사용자 업데이트 엔드포인트"""
    # 실제로는 데이터베이스에서 업데이트
    return UserResponse(
        id=user_id,
        name=user_update.name or "홍길동",
        email=user_update.email or "hong@example.com",
        age=user_update.age or 30,
        created_at=datetime.now(),
        is_active=True,
    )


@api_app.post("/products", response_model=ProductModel)
async def create_product(product: ProductModel) -> ProductModel:
    """상품 생성 엔드포인트"""
    return product


def demonstrate_fastapi_integration():
    """FastAPI 통합 데모"""
    print("\n" + "=" * 60)
    print("10. FastAPI와의 통합")
    print("=" * 60)
    print("FastAPI 앱이 생성되었습니다.")
    print("다음 명령어로 서버를 실행하세요:")
    print("  uvicorn 07_pydantic_guide:api_app --reload")
    print("\nAPI 엔드포인트:")
    print("  POST /users - 사용자 생성")
    print("  GET /users/{user_id} - 사용자 조회")
    print("  PATCH /users/{user_id} - 사용자 업데이트")
    print("  POST /products - 상품 생성")
    print("\nAPI 문서:")
    print("  http://localhost:8000/docs - Swagger UI")
    print("  http://localhost:8000/redoc - ReDoc")


# ============================================================================
# 11. 데이터 직렬화 옵션
# ============================================================================


def demonstrate_serialization():
    """데이터 직렬화 데모"""
    print("\n" + "=" * 60)
    print("11. 데이터 직렬화 옵션")
    print("=" * 60)

    user = UserResponse(
        id=1,
        name="홍길동",
        email="hong@example.com",
        age=30,
        created_at=datetime.now(),
        is_active=True,
    )

    # 기본 직렬화
    print("1. 기본 직렬화 (model_dump):")
    print(f"   {user.model_dump()}")

    # JSON 직렬화
    print("\n2. JSON 직렬화 (model_dump_json):")
    print(f"   {user.model_dump_json()}")

    # 특정 필드만 포함
    print("\n3. 특정 필드만 포함:")
    print(f"   {user.model_dump(include={'name', 'email'})}")

    # 특정 필드 제외
    print("\n4. 특정 필드 제외:")
    print(f"   {user.model_dump(exclude={'created_at'})}")

    # 모드 설정
    print("\n5. JSON 모드 (datetime을 문자열로):")
    print(f"   {user.model_dump(mode='json')}")


# ============================================================================
# 12. 에러 처리
# ============================================================================


def demonstrate_error_handling():
    """에러 처리 데모"""
    print("\n" + "=" * 60)
    print("12. 에러 처리")
    print("=" * 60)

    try:
        user = ValidatedUser(
            name="홍",
            age=150,
            email="invalid-email",
            salary=-1000.0,
        )
    except ValidationError as e:
        print("검증 에러 발생:")
        print(f"에러 개수: {len(e.errors())}")
        print("\n상세 에러 정보:")
        for error in e.errors():
            print(f"  필드: {error['loc']}")
            print(f"  메시지: {error['msg']}")
            print(f"  타입: {error['type']}")
            print()

        # JSON 형식으로 출력
        print("JSON 형식 에러:")
        error_dict = json.loads(e.json())
        print(json.dumps(error_dict, indent=2, ensure_ascii=False))


# ============================================================================
# 메인 함수
# ============================================================================


def main():
    """메인 함수 - 모든 데모 실행"""
    print("Pydantic 완전 가이드")
    print("=" * 60)
    print("이 가이드는 Pydantic의 모든 주요 기능을 보여줍니다:")
    print("1. 기본 사용법")
    print("2. 필드 검증")
    print("3. 커스텀 검증")
    print("4. 모델 검증")
    print("5. 모델 상속")
    print("6. 고급 타입")
    print("7. 계산된 필드")
    print("8. 설정 관리")
    print("9. JSON 스키마 생성")
    print("10. FastAPI 통합")
    print("11. 데이터 직렬화")
    print("12. 에러 처리")
    print("=" * 60)

    try:
        demonstrate_basic_usage()
        demonstrate_field_validation()
        demonstrate_custom_validation()
        demonstrate_model_validation()
        demonstrate_model_inheritance()
        demonstrate_advanced_types()
        demonstrate_computed_fields()
        demonstrate_settings()
        demonstrate_json_schema()
        demonstrate_fastapi_integration()
        demonstrate_serialization()
        demonstrate_error_handling()

        print("\n" + "=" * 60)
        print("모든 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)
        print("\nFastAPI 서버를 실행하려면:")
        print("  uvicorn 07_pydantic_guide:api_app --reload")
        print("\n또는 Python으로 직접 실행:")
        print("  python 07_pydantic_guide.py")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
        print("\n필요한 패키지를 설치하세요:")
        print("  pip install pydantic pydantic-settings fastapi uvicorn")


if __name__ == "__main__":
    main()
