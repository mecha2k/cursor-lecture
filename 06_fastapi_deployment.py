#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 배포 및 운영
==================

이 파일은 FastAPI 애플리케이션을 프로덕션 환경에 배포하고
운영하는 방법을 상세히 설명하고 예제를 제공합니다.

주요 배포 방법:
1. Docker 컨테이너화
2. Kubernetes 배포
3. AWS 배포 (ECS, Lambda)
4. Google Cloud 배포 (Cloud Run)
5. Azure 배포 (Container Instances)
6. Heroku 배포
7. Nginx 리버스 프록시
8. Gunicorn/Uvicorn 워커
9. 모니터링 및 로깅
10. CI/CD 파이프라인
"""

import asyncio
import logging
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware

# 모니터링 관련 (선택적)
try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


# ============================================================================
# 1. 로깅 설정
# ============================================================================


# 구조화된 로깅 설정
class JSONFormatter(logging.Formatter):
    """JSON 형태의 로그 포맷터"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)

logger = logging.getLogger(__name__)

# JSON 로거 (구조화된 로깅)
json_logger = logging.getLogger("json")
json_handler = logging.StreamHandler()
json_handler.setFormatter(JSONFormatter())
json_logger.addHandler(json_handler)
json_logger.setLevel(logging.INFO)


# ============================================================================
# 2. 모니터링 설정
# ============================================================================

if PROMETHEUS_AVAILABLE:
    # Prometheus 메트릭 정의
    REQUEST_COUNT = Counter(
        "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
    )

    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
    )

    ACTIVE_CONNECTIONS = Counter("active_connections_total", "Total active connections")


# ============================================================================
# 3. 환경 변수 설정
# ============================================================================


class Settings:
    """애플리케이션 설정"""

    def __init__(self):
        # 기본 설정
        self.app_name = os.getenv("APP_NAME", "FastAPI Production App")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")

        # 서버 설정
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.workers = int(os.getenv("WORKERS", "1"))

        # 데이터베이스 설정
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")

        # 보안 설정
        self.secret_key = os.getenv(
            "SECRET_KEY", "your-secret-key-change-in-production"
        )
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(
            ","
        )

        # 모니터링 설정
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.sentry_dsn = os.getenv("SENTRY_DSN", "")

        # 로깅 설정
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_json_logs = os.getenv("ENABLE_JSON_LOGS", "false").lower() == "true"


settings = Settings()


# ============================================================================
# 4. 모니터링 미들웨어
# ============================================================================


class MetricsMiddleware(BaseHTTPMiddleware):
    """메트릭 수집 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        if not PROMETHEUS_AVAILABLE or not settings.enable_metrics:
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time

            # 메트릭 기록
            REQUEST_COUNT.labels(
                method=request.method, endpoint=request.url.path, status=status_code
            ).inc()

            REQUEST_DURATION.labels(
                method=request.method, endpoint=request.url.path
            ).observe(duration)

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """로깅 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 요청 로깅
        logger.info(f"Request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # 응답 로깅
            logger.info(
                f"Response: {response.status_code} - "
                f"{request.method} {request.url.path} - "
                f"{duration:.4f}s"
            )

            # 구조화된 로깅
            if settings.enable_json_logs:
                json_logger.info(
                    {
                        "event": "http_request",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration": duration,
                        "client_ip": request.client.host,
                        "user_agent": request.headers.get("user-agent", ""),
                    }
                )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - {request.method} {request.url.path} - {duration:.4f}s"
            )
            raise e


# ============================================================================
# 5. 헬스 체크 모델
# ============================================================================


class HealthCheck(BaseModel):
    """헬스 체크 응답 모델"""

    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(..., description="체크 시간")
    version: str = Field(..., description="애플리케이션 버전")
    environment: str = Field(..., description="환경")
    uptime: float = Field(..., description="가동 시간 (초)")


class DetailedHealthCheck(HealthCheck):
    """상세 헬스 체크 응답 모델"""

    database: Dict[str, Any] = Field(..., description="데이터베이스 상태")
    memory: Dict[str, Any] = Field(..., description="메모리 사용량")
    disk: Dict[str, Any] = Field(..., description="디스크 사용량")
    metrics: Optional[Dict[str, Any]] = Field(None, description="메트릭 정보")


# ============================================================================
# 6. 시스템 정보 모델
# ============================================================================


class SystemInfo(BaseModel):
    """시스템 정보 모델"""

    app_name: str
    version: str
    environment: str
    python_version: str
    fastapi_version: str
    uptime: float
    memory_usage: Dict[str, Any]
    disk_usage: Dict[str, Any]


# ============================================================================
# 7. 애플리케이션 시작 시간
# ============================================================================

app_start_time = time.time()


# ============================================================================
# 8. FastAPI 애플리케이션 설정
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    logger.info(f"🚀 {settings.app_name} 시작")
    logger.info(f"환경: {settings.environment}")
    logger.info(f"디버그 모드: {settings.debug}")

    # Sentry 초기화 (선택적)
    if SENTRY_AVAILABLE and settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=settings.environment,
        )
        logger.info("Sentry 초기화됨")

    # 데이터베이스 연결 확인
    try:
        # 실제로는 데이터베이스 연결 테스트
        logger.info("데이터베이스 연결 확인됨")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")

    yield

    # 종료 시 실행
    logger.info(f"🛑 {settings.app_name} 종료")


app = FastAPI(
    title=settings.app_name,
    description="FastAPI 프로덕션 배포 및 운영 예제",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# 미들웨어 추가
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

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
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 9. 시스템 정보 수집 함수
# ============================================================================


def get_system_info() -> Dict[str, Any]:
    """시스템 정보 수집"""
    import psutil
    import sys
    import platform

    # 메모리 사용량
    memory = psutil.virtual_memory()
    memory_info = {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent,
        "used": memory.used,
        "free": memory.free,
    }

    # 디스크 사용량
    disk = psutil.disk_usage("/")
    disk_info = {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": (disk.used / disk.total) * 100,
    }

    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "python_version": sys.version,
        "fastapi_version": "0.104.1",  # 실제로는 import로 가져오기
        "uptime": time.time() - app_start_time,
        "memory_usage": memory_info,
        "disk_usage": disk_info,
        "platform": platform.platform(),
        "cpu_count": psutil.cpu_count(),
    }


def get_database_status() -> Dict[str, Any]:
    """데이터베이스 상태 확인"""
    try:
        # 실제로는 데이터베이스 연결 테스트
        return {"status": "healthy", "connection": "active", "response_time": 0.001}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "connection": "failed"}


# ============================================================================
# 10. 기본 엔드포인트
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def root():
    """루트 엔드포인트"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{settings.app_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
            .status {{ background: #ecf0f1; padding: 20px; border-radius: 5px; }}
            .endpoints {{ margin-top: 20px; }}
            .endpoint {{ margin: 10px 0; }}
            .method {{ display: inline-block; width: 80px; font-weight: bold; }}
            .get {{ color: #27ae60; }}
            .post {{ color: #3498db; }}
            .put {{ color: #f39c12; }}
            .delete {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">{settings.app_name}</h1>
            <div class="status">
                <h2>서비스 상태</h2>
                <p><strong>환경:</strong> {settings.environment}</p>
                <p><strong>버전:</strong> {settings.app_version}</p>
                <p><strong>상태:</strong> <span style="color: green;">정상 운영 중</span></p>
            </div>
            <div class="endpoints">
                <h2>주요 엔드포인트</h2>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/health">/health</a> - 헬스 체크
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/health/detailed">/health/detailed</a> - 상세 헬스 체크
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/system">/system</a> - 시스템 정보
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/metrics">/metrics</a> - 메트릭 정보
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """기본 헬스 체크"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        environment=settings.environment,
        uptime=time.time() - app_start_time,
    )


@app.get("/health/detailed", response_model=DetailedHealthCheck)
async def detailed_health_check():
    """상세 헬스 체크"""
    system_info = get_system_info()
    database_status = get_database_status()

    metrics_info = None
    if PROMETHEUS_AVAILABLE and settings.enable_metrics:
        metrics_info = {"prometheus_available": True, "metrics_endpoint": "/metrics"}

    return DetailedHealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        environment=settings.environment,
        uptime=time.time() - app_start_time,
        database=database_status,
        memory=system_info["memory_usage"],
        disk=system_info["disk_usage"],
        metrics=metrics_info,
    )


@app.get("/system", response_model=SystemInfo)
async def get_system_info_endpoint():
    """시스템 정보 조회"""
    system_info = get_system_info()
    return SystemInfo(**system_info)


@app.get("/metrics")
async def get_metrics():
    """Prometheus 메트릭 조회"""
    if not PROMETHEUS_AVAILABLE or not settings.enable_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metrics not available"
        )

    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type="text/plain")


# ============================================================================
# 11. 관리자 엔드포인트
# ============================================================================


@app.get("/admin/status")
async def admin_status():
    """관리자 상태 조회"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "uptime": time.time() - app_start_time,
        "workers": settings.workers,
        "host": settings.host,
        "port": settings.port,
    }


@app.post("/admin/restart")
async def admin_restart():
    """애플리케이션 재시작 (시뮬레이션)"""
    logger.info("애플리케이션 재시작 요청됨")
    return {
        "message": "재시작 요청이 처리되었습니다.",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/admin/logs")
async def admin_logs(lines: int = 100):
    """로그 조회"""
    try:
        with open("app.log", "r") as f:
            log_lines = f.readlines()
            recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines

        return {
            "logs": recent_logs,
            "total_lines": len(log_lines),
            "returned_lines": len(recent_logs),
        }
    except FileNotFoundError:
        return {
            "logs": [],
            "total_lines": 0,
            "returned_lines": 0,
            "message": "로그 파일을 찾을 수 없습니다.",
        }


# ============================================================================
# 12. 성능 테스트 엔드포인트
# ============================================================================


@app.get("/test/performance")
async def performance_test():
    """성능 테스트 엔드포인트"""
    start_time = time.time()

    # CPU 집약적 작업 시뮬레이션
    result = sum(i**2 for i in range(10000))

    # I/O 작업 시뮬레이션
    await asyncio.sleep(0.1)

    duration = time.time() - start_time

    return {
        "message": "성능 테스트 완료",
        "result": result,
        "duration": duration,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/test/memory")
async def memory_test():
    """메모리 테스트 엔드포인트"""
    import psutil
    import gc

    # 메모리 사용량 측정
    memory_before = psutil.virtual_memory().used

    # 메모리 할당
    data = [i for i in range(100000)]

    memory_after = psutil.virtual_memory().used
    memory_used = memory_after - memory_before

    # 가비지 컬렉션
    gc.collect()

    return {
        "message": "메모리 테스트 완료",
        "memory_before": memory_before,
        "memory_after": memory_after,
        "memory_used": memory_used,
        "data_length": len(data),
    }


# ============================================================================
# 13. 에러 핸들링
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)

    # Sentry에 오류 전송 (선택적)
    if SENTRY_AVAILABLE and settings.sentry_dsn:
        sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


# ============================================================================
# 14. Docker 및 배포 설정 파일 생성
# ============================================================================


def create_dockerfile():
    """Dockerfile 생성"""
    dockerfile_content = """
# Python 3.11 슬림 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "06_fastapi_deployment:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)

    print("✅ Dockerfile이 생성되었습니다.")


def create_docker_compose():
    """Docker Compose 파일 생성"""
    docker_compose_content = """
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - WORKERS=4
      - ENABLE_METRICS=true
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    restart: unless-stopped

volumes:
  grafana-storage:
"""

    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose_content)

    print("✅ docker-compose.yml이 생성되었습니다.")


def create_nginx_config():
    """Nginx 설정 파일 생성"""
    nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream fastapi {
        server app:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://fastapi;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /metrics {
            proxy_pass http://fastapi/metrics;
        }
    }
}
"""

    with open("nginx.conf", "w") as f:
        f.write(nginx_config)

    print("✅ nginx.conf가 생성되었습니다.")


# ============================================================================
# 15. 메인 실행 함수
# ============================================================================


def run_production_server():
    """프로덕션 서버 실행"""
    print("=" * 60)
    print("FastAPI 프로덕션 배포 및 운영 서버 시작")
    print("=" * 60)
    print("🚀 배포 방법:")
    print("1. Docker 컨테이너화")
    print("2. Kubernetes 배포")
    print("3. AWS/Google Cloud/Azure 배포")
    print("4. Nginx 리버스 프록시")
    print("5. 모니터링 및 로깅")
    print("=" * 60)
    print("🌐 서버 주소:")
    print(f"   - 애플리케이션: http://localhost:{settings.port}")
    print("   - 헬스 체크: http://localhost:8000/health")
    print("   - 시스템 정보: http://localhost:8000/system")
    if settings.enable_metrics:
        print("   - 메트릭: http://localhost:8000/metrics")
    print("=" * 60)

    # 배포 파일 생성
    create_dockerfile()
    create_docker_compose()
    create_nginx_config()

    uvicorn.run(
        "06_fastapi_deployment:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if settings.environment == "production" else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run_production_server()
