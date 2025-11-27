#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 데코레이터 완전 가이드
============================

이 파일은 Python의 데코레이터(Decorator)에 대한 기초부터 고급 사용법까지
상세히 설명하고 실용적인 예제를 제공합니다.

데코레이터란?
- 함수나 클래스를 수정하지 않고도 기능을 추가하거나 변경할 수 있는 기능
- 코드 재사용성과 가독성을 높여줍니다
- DRY(Don't Repeat Yourself) 원칙을 지키는 데 도움이 됩니다

주요 특징:
- 함수/클래스를 감싸서 기능 추가
- 데코레이터 체이닝 가능
- 메타데이터 보존 (functools.wraps)
- 인자 전달 가능한 데코레이터 팩토리
"""

from typing import Callable, Any, TypeVar, ParamSpec
from functools import wraps, lru_cache
from datetime import datetime
import time
import json
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    computed_field,
    ValidationError,
)

# 타입 변수
F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")


# ============================================================================
# 1. 데코레이터 기본 개념
# ============================================================================


def demonstrate_basic_concept():
    """데코레이터 기본 개념 설명"""
    print("=" * 60)
    print("1. 데코레이터 기본 개념")
    print("=" * 60)

    print(
        """
        데코레이터는 함수나 클래스를 감싸서 기능을 추가하는 Python의 강력한 기능입니다.

        기본 문법:
            @decorator
            def function():
                pass

        이는 다음과 동일합니다:
            def function():
                pass
            function = decorator(function)

        데코레이터는 함수를 받아서 함수를 반환하는 함수입니다.
        """
    )

    # 기본 데코레이터 예제
    def simple_decorator(func: Callable) -> Callable:
        """간단한 데코레이터"""

        def wrapper(*args, **kwargs):
            print(f"함수 {func.__name__} 호출 전")
            result = func(*args, **kwargs)
            print(f"함수 {func.__name__} 호출 후")
            return result

        return wrapper

    @simple_decorator
    def greet(name: str) -> str:
        """인사 함수"""
        return f"안녕하세요, {name}님!"

    print("\n기본 데코레이터 예제:")
    result = greet("홍길동")
    print(f"결과: {result}")


# ============================================================================
# 2. @classmethod 데코레이터
# ============================================================================


def demonstrate_classmethod():
    """@classmethod 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("2. @classmethod 데코레이터")
    print("=" * 60)

    print(
        """
@classmethod는 메서드를 클래스 메서드로 만듭니다.

특징:
- 첫 번째 인자로 클래스 자체(cls)를 받습니다
- 인스턴스를 생성하지 않고도 호출 가능합니다
- 클래스 레벨에서 동작하는 메서드를 만들 때 사용합니다
- 팩토리 메서드 패턴 구현에 유용합니다
"""
    )

    class User:
        """사용자 클래스"""

        def __init__(self, name: str, age: int):
            self.name = name
            self.age = age

        @classmethod
        def from_dict(cls, data: dict) -> "User":
            """딕셔너리로부터 인스턴스 생성 (팩토리 메서드)"""
            return cls(data["name"], data["age"])

        @classmethod
        def from_json(cls, json_str: str) -> "User":
            """JSON 문자열로부터 인스턴스 생성"""
            data = json.loads(json_str)
            return cls.from_dict(data)

        @classmethod
        def get_class_name(cls) -> str:
            """클래스 이름 반환"""
            return cls.__name__

        def __str__(self) -> str:
            return f"{self.name} ({self.age}세)"

    print("\n@classmethod 예제:")
    # 클래스 메서드 호출 (인스턴스 없이)
    print(f"클래스명: {User.get_class_name()}")

    # 팩토리 메서드 사용
    user1 = User.from_dict({"name": "홍길동", "age": 30})
    print(f"딕셔너리로 생성: {user1}")

    user2 = User.from_json('{"name": "김철수", "age": 25}')
    print(f"JSON으로 생성: {user2}")


# ============================================================================
# 3. @staticmethod 데코레이터
# ============================================================================


def demonstrate_staticmethod():
    """@staticmethod 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("3. @staticmethod 데코레이터")
    print("=" * 60)

    print(
        """
@staticmethod는 정적 메서드를 만듭니다.

특징:
- cls나 self를 받지 않습니다
- 클래스나 인스턴스와 독립적으로 동작합니다
- 유틸리티 함수를 클래스 내부에 정의할 때 사용합니다
- 네임스페이스를 정리하는 데 유용합니다
"""
    )

    class MathUtils:
        """수학 유틸리티 클래스"""

        @staticmethod
        def add(a: int, b: int) -> int:
            """덧셈"""
            return a + b

        @staticmethod
        def multiply(a: int, b: int) -> int:
            """곱셈"""
            return a * b

        @staticmethod
        def power(base: int, exponent: int) -> int:
            """거듭제곱"""
            return base**exponent

    print("\n@staticmethod 예제:")
    print(f"10 + 20 = {MathUtils.add(10, 20)}")
    print(f"10 * 20 = {MathUtils.multiply(10, 20)}")
    print(f"2^8 = {MathUtils.power(2, 8)}")

    # 인스턴스에서도 호출 가능
    utils = MathUtils()
    print(f"인스턴스로 호출: {utils.add(5, 3)}")


# ============================================================================
# 4. @property 데코레이터
# ============================================================================


def demonstrate_property():
    """@property 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("4. @property 데코레이터")
    print("=" * 60)

    print(
        """
@property는 메서드를 속성처럼 사용할 수 있게 해줍니다.

특징:
- getter, setter, deleter를 정의할 수 있습니다
- 계산된 속성을 만들 때 유용합니다
- 데이터 검증을 추가할 수 있습니다
- 캡슐화를 구현하는 데 도움이 됩니다
"""
    )

    class Circle:
        """원 클래스"""

        def __init__(self, radius: float):
            self._radius = radius

        @property
        def radius(self) -> float:
            """반지름 getter"""
            return self._radius

        @radius.setter
        def radius(self, value: float):
            """반지름 setter (검증 포함)"""
            if value < 0:
                raise ValueError("반지름은 0 이상이어야 합니다")
            self._radius = value

        @property
        def diameter(self) -> float:
            """지름 (계산된 속성)"""
            return 2 * self._radius

        @property
        def area(self) -> float:
            """면적 (계산된 속성)"""
            return 3.14159 * self._radius**2

        @property
        def circumference(self) -> float:
            """둘레 (계산된 속성)"""
            return 2 * 3.14159 * self._radius

    print("\n@property 예제:")
    circle = Circle(5.0)
    print(f"반지름: {circle.radius}")
    print(f"지름: {circle.diameter}")
    print(f"면적: {circle.area:.2f}")
    print(f"둘레: {circle.circumference:.2f}")

    # setter 사용
    print("\n반지름 변경:")
    circle.radius = 10.0
    print(f"새 반지름: {circle.radius}")
    print(f"새 면적: {circle.area:.2f}")

    # 검증 테스트
    try:
        circle.radius = -5.0
    except ValueError as e:
        print(f"\n검증 실패: {e}")


# ============================================================================
# 5. Pydantic의 @field_validator 데코레이터
# ============================================================================


def demonstrate_field_validator():
    """@field_validator 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("5. Pydantic의 @field_validator 데코레이터")
    print("=" * 60)

    print(
        """
@field_validator는 Pydantic에서 특정 필드에 커스텀 검증 로직을
적용할 때 사용하는 데코레이터입니다.

특징:
- @classmethod와 함께 사용해야 합니다
- 필드 값을 검증하고 변환할 수 있습니다
- 여러 필드에 동시에 적용 가능합니다
- mode 파라미터로 검증 시점을 제어할 수 있습니다
"""
    )

    class AdvancedUser(BaseModel):
        """고급 사용자 모델"""

        username: str
        email: str
        age: int
        phone: str

        @field_validator("username")
        @classmethod
        def validate_username(cls, v: str) -> str:
            """사용자명 검증 및 변환"""
            if len(v) < 3:
                raise ValueError("사용자명은 최소 3자 이상이어야 합니다")
            if not v.replace("_", "").isalnum():
                raise ValueError(
                    "사용자명은 영문, 숫자, 언더스코어만 사용할 수 있습니다"
                )
            return v.lower().strip()

        @field_validator("email")
        @classmethod
        def validate_email(cls, v: str) -> str:
            """이메일 검증"""
            if "@" not in v:
                raise ValueError("올바른 이메일 형식이 아닙니다")
            return v.lower().strip()

        @field_validator("age")
        @classmethod
        def validate_age(cls, v: int) -> int:
            """나이 검증"""
            if v < 0 or v > 120:
                raise ValueError("나이는 0-120 사이여야 합니다")
            return v

        @field_validator("username", "email")
        @classmethod
        def validate_no_spaces(cls, v: str) -> str:
            """여러 필드에 동시 적용 - 공백 제거"""
            if " " in v:
                raise ValueError("공백을 포함할 수 없습니다")
            return v

    print("\n@field_validator 예제:")
    try:
        user = AdvancedUser(
            username="  JohnDoe  ",  # 공백 포함, 대소문자 혼합
            email="  JOHN@EXAMPLE.COM  ",  # 공백 포함, 대문자
            age=25,
            phone="010-1234-5678",
        )
        print(f"검증 후 사용자명: '{user.username}'")
        print(f"검증 후 이메일: '{user.email}'")
        print(f"나이: {user.age}")
    except ValidationError as e:
        print(f"검증 실패:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")


# ============================================================================
# 6. Pydantic의 @model_validator 데코레이터
# ============================================================================


def demonstrate_model_validator():
    """@model_validator 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("6. Pydantic의 @model_validator 데코레이터")
    print("=" * 60)

    print(
        """
@model_validator는 모델 전체에 대한 검증을 수행합니다.

특징:
- 여러 필드 간의 관계를 검증할 때 사용합니다
- mode='before' 또는 mode='after'로 검증 시점 제어
- before: 타입 변환 전 검증
- after: 타입 변환 후 검증 (기본값)
"""
    )

    class Order(BaseModel):
        """주문 모델"""

        quantity: int = Field(..., gt=0)
        unit_price: float = Field(..., gt=0)
        discount: float = Field(0.0, ge=0, le=1.0)
        total: float | None = None

        @model_validator(mode="after")
        def validate_order(self) -> "Order":
            """주문 검증 - 할인 후 가격 계산"""
            if self.total is None:
                self.total = self.quantity * self.unit_price * (1 - self.discount)

            if self.total <= 0:
                raise ValueError("총액은 0보다 커야 합니다")

            if self.total > self.quantity * self.unit_price:
                raise ValueError("할인 후 가격은 원래 가격보다 클 수 없습니다")

            return self

    print("\n@model_validator 예제:")
    order = Order(quantity=10, unit_price=1000.0, discount=0.1)
    print(f"수량: {order.quantity}")
    print(f"단가: {order.unit_price}")
    print(f"할인율: {order.discount * 100}%")
    print(f"총액: {order.total}")


# ============================================================================
# 7. Pydantic의 @computed_field 데코레이터
# ============================================================================


def demonstrate_computed_field():
    """@computed_field 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("7. Pydantic의 @computed_field 데코레이터")
    print("=" * 60)

    print(
        """
@computed_field는 계산된 필드를 정의합니다.

특징:
- @property와 유사하지만 Pydantic 모델에서 사용됩니다
- JSON 스키마에 포함됩니다
- 직렬화 시 자동으로 계산됩니다
- 다른 필드에 의존하는 값을 계산할 때 유용합니다
"""
    )

    class Product(BaseModel):
        """상품 모델"""

        name: str
        price: float = Field(..., gt=0)
        quantity: int = Field(..., gt=0)
        discount: float = Field(0.0, ge=0, le=1.0)

        @computed_field
        @property
        def subtotal(self) -> float:
            """소계"""
            return self.price * self.quantity

        @computed_field
        @property
        def total(self) -> float:
            """총액 (할인 적용)"""
            return self.subtotal * (1 - self.discount)

        @computed_field
        @property
        def savings(self) -> float:
            """절약 금액"""
            return self.subtotal - self.total

    print("\n@computed_field 예제:")
    product = Product(name="노트북", price=1000000.0, quantity=2, discount=0.15)
    print(f"상품명: {product.name}")
    print(f"단가: {product.price:,}원")
    print(f"수량: {product.quantity}개")
    print(f"소계: {product.subtotal:,}원")
    print(f"할인율: {product.discount * 100}%")
    print(f"총액: {product.total:,}원")
    print(f"절약: {product.savings:,}원")

    # JSON 직렬화 시 계산된 필드 포함
    print(f"\nJSON 직렬화:")
    product_dict = product.model_dump()
    print(json.dumps(product_dict, indent=2, ensure_ascii=False))


# ============================================================================
# 8. 커스텀 데코레이터 만들기
# ============================================================================


def demonstrate_custom_decorators():
    """커스텀 데코레이터 만들기"""
    print("\n" + "=" * 60)
    print("8. 커스텀 데코레이터 만들기")
    print("=" * 60)

    print(
        """
데코레이터는 함수를 받아서 함수를 반환하는 함수입니다.
복잡한 로직을 재사용 가능한 데코레이터로 만들 수 있습니다.
"""
    )

    # 1. 실행 시간 측정 데코레이터
    def timing_decorator(func: Callable) -> Callable:
        """실행 시간 측정 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"{func.__name__} 실행 시간: {(end - start) * 1000:.2f}ms")
            return result

        return wrapper

    # 2. 재시도 데코레이터 팩토리
    def retry_decorator(max_retries: int = 3, delay: float = 1.0):
        """재시도 데코레이터 팩토리"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(1, max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries:
                            raise
                        print(
                            f"{func.__name__} 실패 (시도 {attempt}/{max_retries}): {e}"
                        )
                        time.sleep(delay)

            return wrapper

        return decorator

    # 3. 로깅 데코레이터
    def log_decorator(func: Callable) -> Callable:
        """로깅 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[{datetime.now()}] {func.__name__} 호출됨")
            print(f"  인자: args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                print(f"[{datetime.now()}] {func.__name__} 완료됨")
                return result
            except Exception as e:
                print(f"[{datetime.now()}] {func.__name__} 오류: {e}")
                raise

        return wrapper

    # 4. 캐싱 데코레이터
    @lru_cache(maxsize=128)
    def cached_function(n: int) -> int:
        """캐싱된 함수"""
        print(f"계산 중: {n}")
        return sum(range(n))

    print("\n1. 실행 시간 측정 데코레이터:")

    @timing_decorator
    def slow_function(n: int) -> int:
        """느린 함수"""
        time.sleep(0.1)
        return sum(range(n))

    result = slow_function(1000)
    print(f"결과: {result}")

    print("\n2. 재시도 데코레이터:")

    @retry_decorator(max_retries=3, delay=0.1)
    def unreliable_function() -> int:
        """불안정한 함수 (시뮬레이션)"""
        import random

        if random.random() < 0.7:
            raise ValueError("임의의 오류 발생")
        return 42

    try:
        result = unreliable_function()
        print(f"성공: {result}")
    except ValueError as e:
        print(f"최종 실패: {e}")

    print("\n3. 로깅 데코레이터:")

    @log_decorator
    def calculate(x: int, y: int) -> int:
        """계산 함수"""
        return x * y

    result = calculate(10, 20)
    print(f"결과: {result}")

    print("\n4. 캐싱 데코레이터:")
    print("첫 번째 호출 (계산 수행):")
    result1 = cached_function(1000)
    print(f"결과: {result1}")

    print("두 번째 호출 (캐시 사용):")
    result2 = cached_function(1000)
    print(f"결과: {result2}")


# ============================================================================
# 9. 데코레이터 체이닝
# ============================================================================


def demonstrate_decorator_chaining():
    """데코레이터 체이닝 설명"""
    print("\n" + "=" * 60)
    print("9. 데코레이터 체이닝")
    print("=" * 60)

    print(
        """
여러 데코레이터를 순차적으로 적용할 수 있습니다.
아래에서 위로 순서대로 적용됩니다.

@decorator1
@decorator2
@decorator3
def function():
    pass

이는 다음과 동일합니다:
function = decorator1(decorator2(decorator3(function)))
"""
    )

    def log_decorator(func: Callable) -> Callable:
        """로깅 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[LOG] {func.__name__} 호출됨")
            result = func(*args, **kwargs)
            print(f"[LOG] {func.__name__} 완료됨")
            return result

        return wrapper

    def timing_decorator(func: Callable) -> Callable:
        """실행 시간 측정 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"[TIMING] {func.__name__} 실행 시간: {(end - start) * 1000:.2f}ms")
            return result

        return wrapper

    @log_decorator
    @timing_decorator
    def complex_function(x: int, y: int) -> int:
        """복잡한 함수"""
        time.sleep(0.05)
        return x * y

    print("\n데코레이터 체이닝 예제:")
    result = complex_function(10, 20)
    print(f"결과: {result}")


# ============================================================================
# 10. functools.wraps 사용
# ============================================================================


def demonstrate_functools_wraps():
    """functools.wraps 사용 설명"""
    print("\n" + "=" * 60)
    print("10. functools.wraps 사용")
    print("=" * 60)

    print(
        """
functools.wraps를 사용하면 원본 함수의 메타데이터를 보존할 수 있습니다.
이렇게 하면 디버깅과 문서화가 더 쉬워집니다.

보존되는 메타데이터:
- __name__: 함수 이름
- __doc__: 함수 문서 문자열
- __module__: 함수가 정의된 모듈
- __annotations__: 타입 힌트
"""
    )

    def without_wraps_decorator(func: Callable) -> Callable:
        """wraps 없이 만든 데코레이터"""

        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    def with_wraps_decorator(func: Callable) -> Callable:
        """wraps를 사용한 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @without_wraps_decorator
    def function_without_wraps(x: int) -> int:
        """wraps 없이 데코레이터 적용된 함수"""
        return x * 2

    @with_wraps_decorator
    def function_with_wraps(x: int) -> int:
        """wraps를 사용한 데코레이터 적용된 함수"""
        return x * 2

    print("\nwraps 없이:")
    print(f"함수명: {function_without_wraps.__name__}")
    print(f"문서: {function_without_wraps.__doc__}")

    print("\nwraps 사용:")
    print(f"함수명: {function_with_wraps.__name__}")
    print(f"문서: {function_with_wraps.__doc__}")


# ============================================================================
# 11. 클래스 데코레이터
# ============================================================================


def demonstrate_class_decorator():
    """클래스 데코레이터 설명"""
    print("\n" + "=" * 60)
    print("11. 클래스 데코레이터")
    print("=" * 60)

    print(
        """
데코레이터는 클래스에도 적용할 수 있습니다.
클래스의 모든 메서드에 기능을 추가할 수 있습니다.
"""
    )

    def add_logging(cls):
        """클래스에 로깅 기능 추가"""

        class LoggedClass(cls):
            def __getattribute__(self, name):
                attr = super().__getattribute__(name)
                if callable(attr) and not name.startswith("__"):
                    print(f"[LOG] {name} 메서드 호출")
                return attr

        return LoggedClass

    @add_logging
    class Calculator:
        """계산기 클래스"""

        def add(self, a: int, b: int) -> int:
            return a + b

        def multiply(self, a: int, b: int) -> int:
            return a * b

        def subtract(self, a: int, b: int) -> int:
            return a - b

    print("\n클래스 데코레이터 예제:")
    calc = Calculator()
    print(f"10 + 20 = {calc.add(10, 20)}")
    print(f"10 * 20 = {calc.multiply(10, 20)}")
    print(f"10 - 5 = {calc.subtract(10, 5)}")


# ============================================================================
# 12. 데코레이터 팩토리 (인자 전달)
# ============================================================================


def demonstrate_decorator_factory():
    """데코레이터 팩토리 설명"""
    print("\n" + "=" * 60)
    print("12. 데코레이터 팩토리 (인자 전달)")
    print("=" * 60)

    print(
        """
데코레이터에 인자를 전달하려면 데코레이터 팩토리를 사용합니다.
이는 데코레이터를 반환하는 함수입니다.
"""
    )

    def repeat(times: int):
        """함수를 여러 번 실행하는 데코레이터 팩토리"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                results = []
                for i in range(times):
                    result = func(*args, **kwargs)
                    results.append(result)
                return results

            return wrapper

        return decorator

    def rate_limit(calls_per_second: float):
        """호출 빈도 제한 데코레이터 팩토리"""

        min_interval = 1.0 / calls_per_second
        last_called = [0.0]

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                elapsed = time.perf_counter() - last_called[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                last_called[0] = time.perf_counter()
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @repeat(times=3)
    def greet(name: str) -> str:
        """인사 함수"""
        return f"안녕하세요, {name}님!"

    @rate_limit(calls_per_second=2.0)
    def api_call() -> str:
        """API 호출 시뮬레이션"""
        return "API 응답"

    print("\n1. repeat 데코레이터:")
    results = greet("홍길동")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")

    print("\n2. rate_limit 데코레이터:")
    start = time.perf_counter()
    for i in range(3):
        result = api_call()
        print(f"  {i+1}. {result}")
    elapsed = time.perf_counter() - start
    print(f"  총 소요 시간: {elapsed:.2f}초 (최소 1초 간격)")


# ============================================================================
# 메인 함수
# ============================================================================


def main():
    """메인 함수 - 모든 데모 실행"""
    print("Python 데코레이터 완전 가이드")
    print("=" * 60)
    print("이 가이드는 Python 데코레이터의 모든 주요 기능을 보여줍니다:")
    print("1. 데코레이터 기본 개념")
    print("2. @classmethod 데코레이터")
    print("3. @staticmethod 데코레이터")
    print("4. @property 데코레이터")
    print("5. Pydantic의 @field_validator")
    print("6. Pydantic의 @model_validator")
    print("7. Pydantic의 @computed_field")
    print("8. 커스텀 데코레이터 만들기")
    print("9. 데코레이터 체이닝")
    print("10. functools.wraps 사용")
    print("11. 클래스 데코레이터")
    print("12. 데코레이터 팩토리")
    print("=" * 60)

    try:
        demonstrate_basic_concept()
        demonstrate_classmethod()
        demonstrate_staticmethod()
        demonstrate_property()
        demonstrate_field_validator()
        demonstrate_model_validator()
        demonstrate_computed_field()
        demonstrate_custom_decorators()
        demonstrate_decorator_chaining()
        demonstrate_functools_wraps()
        demonstrate_class_decorator()
        demonstrate_decorator_factory()

        print("\n" + "=" * 60)
        print("모든 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
        print("\n필요한 패키지를 설치하세요:")
        print("  pip install pydantic")


if __name__ == "__main__":
    main()
