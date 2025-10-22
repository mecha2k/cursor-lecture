#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 고급 기능 및 실용적 예제
================================

이 파일은 FastAPI의 고급 기능과 실무에서 자주 사용되는
패턴들을 상세히 설명하고 예제를 제공합니다.

고급 기능:
1. 의존성 주입 (Dependency Injection)
2. 미들웨어와 플러그인
3. 백그라운드 작업
4. 웹소켓 지원
5. 캐싱과 성능 최적화
6. 테스트와 디버깅
7. 로깅과 모니터링
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Annotated
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
import hashlib
from functools import lru_cache

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, Field, validator
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# 1. 로깅 설정
# ============================================================================

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("fastapi_advanced.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


# ============================================================================
# 2. 커스텀 미들웨어
# ============================================================================


class TimingMiddleware(BaseHTTPMiddleware):
    """요청 처리 시간을 측정하는 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(f"{request.method} {request.url.path} - {process_time:.4f}s")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """간단한 속도 제한 미들웨어"""

    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        # 1분 이전 요청 기록 제거
        self.requests[client_ip] = [
            req_time
            for req_time in self.requests.get(client_ip, [])
            if now - req_time < 60
        ]

        # 요청 수 확인
        if len(self.requests.get(client_ip, [])) >= self.calls_per_minute:
            return JSONResponse(
                status_code=429,
                content={"message": "Too Many Requests", "retry_after": 60},
            )

        # 요청 기록 추가
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(now)

        response = await call_next(request)
        return response


# ============================================================================
# 3. 의존성 주입 시스템
# ============================================================================

# 인증 토큰 저장소 (실제로는 데이터베이스나 Redis 사용)
valid_tokens = {
    "admin-token": {
        "user_id": 1,
        "role": "admin",
        "permissions": ["read", "write", "delete"],
    },
    "user-token": {"user_id": 2, "role": "user", "permissions": ["read", "write"]},
    "guest-token": {"user_id": 3, "role": "guest", "permissions": ["read"]},
}

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """현재 사용자 정보를 가져오는 의존성"""
    token = credentials.credentials

    if token not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return valid_tokens[token]


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """활성 사용자만 허용하는 의존성"""
    if current_user.get("role") == "banned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def require_permission(permission: str):
    """특정 권한이 필요한 의존성 팩토리"""

    async def permission_checker(current_user: dict = Depends(get_current_active_user)):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user

    return permission_checker


# ============================================================================
# 4. 캐싱 시스템
# ============================================================================


class CacheManager:
    """간단한 인메모리 캐시 매니저"""

    def __init__(self):
        self.cache = {}
        self.ttl = {}

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if key in self.cache:
            if time.time() < self.ttl.get(key, 0):
                return self.cache[key]
            else:
                # TTL 만료된 항목 제거
                del self.cache[key]
                del self.ttl[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """캐시에 값 저장"""
        self.cache[key] = value
        self.ttl[key] = time.time() + ttl_seconds

    def delete(self, key: str):
        """캐시에서 값 삭제"""
        if key in self.cache:
            del self.cache[key]
            del self.ttl[key]


# 전역 캐시 인스턴스
cache_manager = CacheManager()


def cache_key_generator(*args, **kwargs) -> str:
    """캐시 키 생성기"""
    key_data = {"args": args, "kwargs": kwargs}
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


async def get_cached_data(key: str, ttl: int = 300):
    """캐시된 데이터를 가져오는 의존성"""
    cached_data = cache_manager.get(key)
    if cached_data is not None:
        logger.info(f"Cache hit for key: {key}")
        return cached_data

    logger.info(f"Cache miss for key: {key}")
    return None


# ============================================================================
# 5. 백그라운드 작업
# ============================================================================


class BackgroundTaskManager:
    """백그라운드 작업 관리자"""

    def __init__(self):
        self.tasks = {}
        self.task_counter = 0

    async def add_task(self, task_func: Callable, *args, **kwargs) -> str:
        """백그라운드 작업 추가"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1

        # 작업 정보 저장
        self.tasks[task_id] = {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }

        # 비동기 작업 시작
        asyncio.create_task(self._execute_task(task_id, task_func, *args, **kwargs))

        return task_id

    async def _execute_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        """작업 실행"""
        try:
            self.tasks[task_id]["status"] = "running"
            self.tasks[task_id]["started_at"] = datetime.now()

            result = await task_func(*args, **kwargs)

            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["completed_at"] = datetime.now()
            self.tasks[task_id]["result"] = result

        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["completed_at"] = datetime.now()
            self.tasks[task_id]["error"] = str(e)
            logger.error(f"Background task {task_id} failed: {e}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        return self.tasks.get(task_id)


# 전역 백그라운드 작업 관리자
background_task_manager = BackgroundTaskManager()


# ============================================================================
# 6. 웹소켓 연결 관리
# ============================================================================


class ConnectionManager:
    """웹소켓 연결 관리자"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.user_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """웹소켓 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """웹소켓 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)

        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """개인 메시지 전송"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: str):
        """모든 연결에 브로드캐스트"""
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.active_connections.remove(connection)

    async def send_to_user(self, message: str, user_id: int):
        """특정 사용자에게 메시지 전송"""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id].copy():
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    self.user_connections[user_id].remove(connection)


# 전역 연결 관리자
manager = ConnectionManager()


# ============================================================================
# 7. Pydantic 모델
# ============================================================================


class TaskRequest(BaseModel):
    """작업 요청 모델"""

    name: str = Field(..., description="작업 이름")
    duration: int = Field(..., ge=1, le=300, description="작업 지속 시간 (초)")
    priority: int = Field(1, ge=1, le=10, description="우선순위")


class TaskResponse(BaseModel):
    """작업 응답 모델"""

    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="상태 메시지")


class WebSocketMessage(BaseModel):
    """웹소켓 메시지 모델"""

    type: str = Field(..., description="메시지 타입")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")


class CacheRequest(BaseModel):
    """캐시 요청 모델"""

    key: str = Field(..., description="캐시 키")
    value: Any = Field(..., description="캐시 값")
    ttl: int = Field(300, ge=1, le=3600, description="TTL (초)")


# ============================================================================
# 8. FastAPI 애플리케이션 설정
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info("🚀 FastAPI 고급 예제 애플리케이션 시작")
    yield
    # 종료 시 실행
    logger.info("🛑 FastAPI 고급 예제 애플리케이션 종료")


app = FastAPI(
    title="FastAPI 고급 예제",
    description="FastAPI의 고급 기능과 실용적 패턴을 보여주는 예제",
    version="2.0.0",
    lifespan=lifespan,
)

# 미들웨어 추가
app.add_middleware(TimingMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=100)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
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
# 9. 기본 엔드포인트
# ============================================================================


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "FastAPI 고급 예제에 오신 것을 환영합니다!",
        "features": [
            "의존성 주입",
            "미들웨어",
            "백그라운드 작업",
            "웹소켓",
            "캐싱",
            "로깅",
        ],
        "docs": "/docs",
        "websocket": "/ws",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
        "cache_size": len(cache_manager.cache),
    }


# ============================================================================
# 10. 인증이 필요한 엔드포인트
# ============================================================================


@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_active_user)):
    """인증이 필요한 엔드포인트"""
    return {"message": "이 엔드포인트는 인증이 필요합니다.", "user": current_user}


@app.get("/admin-only")
async def admin_only_route(current_user: dict = Depends(require_permission("delete"))):
    """관리자만 접근 가능한 엔드포인트"""
    return {"message": "관리자 전용 엔드포인트입니다.", "user": current_user}


# ============================================================================
# 11. 캐싱 예제
# ============================================================================


@app.get("/expensive-operation")
async def expensive_operation(
    n: int = 10,
    cached_data: Optional[Any] = Depends(lambda: get_cached_data(f"expensive_{n}")),
):
    """비용이 큰 연산 (캐싱 적용)"""
    if cached_data is not None:
        return {
            "result": cached_data,
            "cached": True,
            "message": "캐시에서 데이터를 가져왔습니다.",
        }

    # 비용이 큰 연산 시뮬레이션
    await asyncio.sleep(2)
    result = sum(i**2 for i in range(n))

    # 결과를 캐시에 저장
    cache_manager.set(f"expensive_{n}", result, ttl=300)

    return {"result": result, "cached": False, "message": "새로 계산된 데이터입니다."}


@app.post("/cache")
async def set_cache(cache_request: CacheRequest):
    """캐시 설정"""
    cache_manager.set(cache_request.key, cache_request.value, cache_request.ttl)
    return {
        "message": f"캐시 '{cache_request.key}'가 설정되었습니다.",
        "ttl": cache_request.ttl,
    }


@app.get("/cache/{key}")
async def get_cache(key: str):
    """캐시 조회"""
    value = cache_manager.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="캐시를 찾을 수 없습니다.")

    return {"key": key, "value": value}


@app.delete("/cache/{key}")
async def delete_cache(key: str):
    """캐시 삭제"""
    cache_manager.delete(key)
    return {"message": f"캐시 '{key}'가 삭제되었습니다."}


# ============================================================================
# 12. 백그라운드 작업 예제
# ============================================================================


async def long_running_task(name: str, duration: int, priority: int):
    """장시간 실행되는 작업 시뮬레이션"""
    logger.info(f"작업 '{name}' 시작 (우선순위: {priority})")

    # 작업 지속 시간만큼 대기
    await asyncio.sleep(duration)

    result = {
        "task_name": name,
        "duration": duration,
        "priority": priority,
        "completed_at": datetime.now().isoformat(),
    }

    logger.info(f"작업 '{name}' 완료")
    return result


@app.post("/tasks", response_model=TaskResponse)
async def create_background_task(
    task_request: TaskRequest, background_tasks: BackgroundTasks
):
    """백그라운드 작업 생성"""
    task_id = await background_task_manager.add_task(
        long_running_task,
        task_request.name,
        task_request.duration,
        task_request.priority,
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"작업 '{task_request.name}'이 백그라운드에서 시작되었습니다.",
    )


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    task_info = background_task_manager.get_task_status(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    return {
        "task_id": task_id,
        "status": task_info["status"],
        "started_at": task_info["started_at"],
        "completed_at": task_info["completed_at"],
        "result": task_info["result"],
        "error": task_info["error"],
    }


@app.get("/tasks")
async def list_tasks():
    """모든 작업 목록 조회"""
    return {
        "tasks": background_task_manager.tasks,
        "total": len(background_task_manager.tasks),
    }


# ============================================================================
# 13. 웹소켓 엔드포인트
# ============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """웹소켓 엔드포인트"""
    await manager.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                message = WebSocketMessage(**message_data)

                # 메시지 타입에 따른 처리 (Python 3.10 match-case 사용)
                match message.type:
                    case "ping":
                        await manager.send_personal_message(
                            json.dumps(
                                {
                                    "type": "pong",
                                    "content": "pong",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            ),
                            websocket,
                        )
                    case "broadcast":
                        await manager.broadcast(
                            json.dumps(
                                {
                                    "type": "broadcast",
                                    "content": message.content,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )
                    case _:
                        await manager.send_personal_message(
                            json.dumps(
                                {
                                    "type": "echo",
                                    "content": f"Echo: {message.content}",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            ),
                            websocket,
                        )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                    websocket,
                )
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "error",
                            "content": f"Error: {str(e)}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: int):
    """사용자별 웹소켓 엔드포인트"""
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                message = WebSocketMessage(**message_data)

                # 사용자별 메시지 처리
                if message.type == "user_message":
                    await manager.send_to_user(
                        json.dumps(
                            {
                                "type": "user_response",
                                "content": f"User {user_id}: {message.content}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        ),
                        user_id,
                    )
                else:
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "echo",
                                "content": f"Echo: {message.content}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        ),
                        websocket,
                    )

            except Exception as e:
                logger.error(f"WebSocket user error: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# ============================================================================
# 14. 스트리밍 응답 예제
# ============================================================================


@app.get("/stream")
async def stream_data():
    """스트리밍 데이터 응답"""

    async def generate_data():
        for i in range(10):
            yield f"data: {json.dumps({'index': i, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        generate_data(), media_type="text/plain", headers={"Cache-Control": "no-cache"}
    )


# ============================================================================
# 15. 성능 모니터링
# ============================================================================


@app.get("/metrics")
async def get_metrics():
    """성능 메트릭 조회"""
    return {
        "active_connections": len(manager.active_connections),
        "cache_size": len(cache_manager.cache),
        "background_tasks": len(background_task_manager.tasks),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# 16. 메인 실행 함수
# ============================================================================


def run_advanced_server():
    """고급 서버 실행"""
    print("=" * 60)
    print("FastAPI 고급 예제 서버 시작")
    print("=" * 60)
    print("🚀 고급 기능:")
    print("1. 의존성 주입 시스템")
    print("2. 커스텀 미들웨어")
    print("3. 백그라운드 작업")
    print("4. 웹소켓 지원")
    print("5. 캐싱 시스템")
    print("6. 성능 모니터링")
    print("=" * 60)
    print("🌐 서버 주소:")
    print("   - API 문서: http://localhost:8001/docs")
    print("   - 웹소켓: ws://localhost:8001/ws")
    print("   - 메트릭: http://localhost:8001/metrics")
    print("=" * 60)

    uvicorn.run(
        "06_fastapi_advanced:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_advanced_server()
