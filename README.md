# asyncio와 웹소켓 기초부터 고급까지

이 프로젝트는 Python의 asyncio와 웹소켓을 사용한 비동기 프로그래밍을 단계적으로 학습할 수 있도록 구성되었습니다.

## 📚 학습 순서

### 1. asyncio 기초 (`01_asyncio_basics.py`)

- 비동기 프로그래밍의 기본 개념
- 코루틴, 이벤트 루프, Task 객체
- 동시 실행과 순차 실행의 차이
- 타임아웃과 작업 취소

### 2. 웹소켓 기초 (`02_websocket_basics.py`)

- 웹소켓 서버와 클라이언트 구현
- 메시지 브로드캐스트
- 연결 관리와 오류 처리
- JSON 메시지 처리

### 3. 실시간 채팅 애플리케이션 (`03_realtime_chat.py`)

- asyncio와 웹소켓을 결합한 실전 예제
- 사용자 관리와 메시지 히스토리
- 하트비트 모니터링
- 대화형 클라이언트

### 4. 고급 웹소켓 애플리케이션 (`04_advanced_websocket.py`)

- 실시간 데이터 스트리밍
- 데이터 처리와 집계
- 이상치 탐지와 임계값 모니터링
- 서버 메트릭과 부하 관리

### 5. AES 암호화 기초 (`05_aes_encryption.py`)

- AES 암호화/복호화 기본 개념
- CBC, GCM 모드 사용법
- 비밀번호 기반 키 유도 (PBKDF2)
- 추가 인증 데이터 (AAD) 활용
- 데이터 변조 탐지

### 6. AES 보안 모범 사례 (`05_aes_security_guide.py`)

- 보안 키 관리
- 안전한 랜덤 생성
- 타이밍 공격 방어
- 키 로테이션
- 대용량 데이터 암호화

### 7. AES 고급 사용법 (`05_aes_advanced_examples.py`)

- 하이브리드 암호화 (RSA + AES)
- 파일 암호화/복호화
- 데이터베이스 암호화
- 네트워크 통신 암호화
- 클라우드 저장소 암호화
- 실시간 스트리밍 암호화

### 8. FastAPI 기초 (`06_fastapi_basics.py`)

- FastAPI 기본 개념과 설정
- Pydantic 모델과 타입 검증
- 경로 매개변수와 쿼리 매개변수
- 요청/응답 모델
- 에러 핸들링
- 파일 업로드
- 비동기 작업

### 9. FastAPI 고급 기능 (`06_fastapi_advanced.py`)

- 의존성 주입 (Dependency Injection)
- 커스텀 미들웨어
- 백그라운드 작업
- 웹소켓 지원
- 캐싱 시스템
- 성능 모니터링

### 10. FastAPI 데이터베이스 연동 (`06_fastapi_database.py`)

- SQLAlchemy ORM
- 비동기 데이터베이스 작업
- SQLite, PostgreSQL, MySQL 지원
- MongoDB (NoSQL) 연동
- Redis 캐시 연동
- 데이터베이스 마이그레이션

### 11. FastAPI 인증 및 보안 (`06_fastapi_auth_security.py`)

- JWT 토큰 인증
- OAuth2 인증
- 비밀번호 해싱
- 세션 관리
- API 키 인증
- CORS 설정
- 요청 제한
- 보안 헤더

### 12. FastAPI 배포 및 운영 (`06_fastapi_deployment.py`)

- Docker 컨테이너화
- Kubernetes 배포
- AWS/Google Cloud/Azure 배포
- Nginx 리버스 프록시
- 모니터링 및 로깅
- 헬스 체크
- 성능 메트릭

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 예제 실행

#### asyncio 기초 학습

```bash
python 01_asyncio_basics.py
```

#### 웹소켓 기초 학습

```bash
python 02_websocket_basics.py
```

#### 실시간 채팅 (서버)

```bash
python 03_realtime_chat.py
# 선택: 1 (서버 실행)
```

#### 실시간 채팅 (클라이언트)

```bash
python 03_realtime_chat.py
# 선택: 2 (클라이언트 실행)
```

#### 고급 웹소켓 (서버)

```bash
python 04_advanced_websocket.py
# 선택: 1 (서버 실행)
```

#### 고급 웹소켓 (클라이언트)

```bash
python 04_advanced_websocket.py
# 선택: 2 (기본 클라이언트) 또는 3 (분석 클라이언트)
```

#### AES 암호화 기초 학습

```bash
python 05_aes_encryption.py
```

#### AES 보안 모범 사례 학습

```bash
python 05_aes_security_guide.py
```

#### AES 고급 사용법 학습

```bash
python 05_aes_advanced_examples.py
```

#### FastAPI 기초 학습

```bash
python 06_fastapi_basics.py
```

#### FastAPI 고급 기능 학습

```bash
python 06_fastapi_advanced.py
```

#### FastAPI 데이터베이스 연동 학습

```bash
python 06_fastapi_database.py
```

#### FastAPI 인증 및 보안 학습

```bash
python 06_fastapi_auth_security.py
```

#### FastAPI 배포 및 운영 학습

```bash
python 06_fastapi_deployment.py
```

## 📖 주요 개념

### asyncio 핵심 개념

- **Coroutine**: `async def`로 정의된 비동기 함수
- **Event Loop**: 비동기 작업들을 관리하는 루프
- **await**: 다른 코루틴의 완료를 기다림
- **Task**: 실행 중인 코루틴을 관리하는 객체

### 웹소켓 핵심 개념

- **Handshake**: 클라이언트와 서버 간 연결 설정
- **Frame**: 데이터 전송의 기본 단위
- **Ping/Pong**: 연결 상태 확인 메커니즘
- **Close**: 연결 종료 프로세스

### 실무 활용 패턴

- **Connection Pooling**: 연결 재사용으로 성능 최적화
- **Message Queuing**: 메시지 순서 보장과 배치 처리
- **Load Balancing**: 여러 서버 간 부하 분산
- **Monitoring**: 실시간 메트릭 수집과 알림

## 🔧 고급 기능

### 1. 실시간 데이터 스트리밍

- 센서 데이터, 시스템 메트릭, 사용자 활동 등 다양한 데이터 소스
- 실시간 처리와 집계
- 이상치 탐지와 임계값 모니터링

### 2. 연결 관리

- 자동 재연결
- 하트비트 모니터링
- 연결 풀 관리

### 3. 성능 최적화

- 비동기 I/O 활용
- 메시지 배치 처리
- 메모리 효율적인 데이터 구조

### 4. 오류 처리

- 연결 끊김 감지
- 자동 재시도
- 우아한 서비스 중단

## 🎯 실무 적용 사례

### 1. 실시간 채팅 시스템

- 다중 사용자 지원
- 메시지 히스토리
- 사용자 상태 관리

### 2. IoT 데이터 수집

- 센서 데이터 실시간 수집
- 데이터 전처리와 필터링
- 이상 상황 알림

### 3. 금융 데이터 스트리밍

- 실시간 시장 데이터
- 고빈도 거래 처리
- 위험 관리

### 4. 시스템 모니터링

- 서버 성능 메트릭
- 로그 스트리밍
- 알림 시스템

### 5. 데이터 보안

- 파일 암호화/복호화
- 데이터베이스 암호화
- 네트워크 통신 보안
- 클라우드 저장소 암호화

### 6. 웹 API 개발

- RESTful API 설계
- 자동 문서 생성
- 타입 안전성
- 비동기 처리
- 인증 및 보안
- 데이터베이스 연동
- 배포 및 운영

## 📝 학습 팁

1. **단계별 학습**: 각 파일을 순서대로 실행해보세요
2. **코드 수정**: 예제 코드를 수정하며 실험해보세요
3. **디버깅**: 로그를 통해 비동기 작업의 흐름을 파악하세요
4. **성능 측정**: 시간 측정을 통해 동기/비동기의 차이를 확인하세요

## 🐛 문제 해결

### 일반적인 문제들

1. **ImportError: No module named 'websockets'**

   ```bash
   pip install websockets
   ```

2. **연결 거부 오류**

   - 서버가 실행 중인지 확인
   - 포트 번호가 올바른지 확인

3. **메모리 사용량 증가**

   - 연결이 제대로 해제되는지 확인
   - 메시지 히스토리 크기 제한

4. **암호화 관련 오류**

   ```bash
   pip install cryptography
   ```

5. **키 관리 오류**

   - 키 길이가 올바른지 확인 (128, 192, 256비트)
   - IV(초기화 벡터)가 매번 새로 생성되는지 확인

6. **FastAPI 관련 오류**

   ```bash
   pip install fastapi uvicorn
   ```

7. **데이터베이스 연결 오류**
   - 데이터베이스 서버가 실행 중인지 확인
   - 연결 문자열이 올바른지 확인
   - 필요한 드라이버가 설치되었는지 확인

## 📚 추가 학습 자료

- [Python asyncio 공식 문서](https://docs.python.org/3/library/asyncio.html)
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [websockets 라이브러리 문서](https://websockets.readthedocs.io/)
- [cryptography 라이브러리 문서](https://cryptography.io/)
- [AES 암호화 표준 (NIST)](https://csrc.nist.gov/publications/detail/fips/197/final)
- [PBKDF2 키 유도 함수](https://tools.ietf.org/html/rfc2898)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)
- [Pydantic 공식 문서](https://docs.pydantic.dev/)
- [Uvicorn 공식 문서](https://www.uvicorn.org/)
- [Docker 공식 문서](https://docs.docker.com/)
- [Kubernetes 공식 문서](https://kubernetes.io/docs/)

## 🤝 기여하기

이 프로젝트에 기여하고 싶으시다면:

1. 이슈를 생성하여 개선 사항을 제안하세요
2. 풀 리퀘스트를 통해 코드 개선을 제안하세요
3. 새로운 예제나 사용 사례를 추가하세요

---

**Happy Coding! 🚀**
