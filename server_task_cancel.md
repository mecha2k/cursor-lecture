# `server_task.cancel()` 완전 분석 보고서

## 📋 개요

`server_task.cancel()`은 asyncio Task의 취소 메커니즘을 사용하여 실행 중인 비동기 작업을 안전하게 중단시키는 핵심 메서드입니다.

## 🔍 핵심 동작 메커니즘

### 1. **취소 요청 전송**

```python
server_task.cancel()  # 즉시 반환 (논블로킹)
```

- `CancelledError` 예외를 해당 태스크로 전송
- **즉시 중단되지 않음** - await 지점까지 도달해야 중단
- 논블로킹 방식으로 즉시 반환

### 2. **태스크 내부에서 취소 처리**

```python
async def start_server(self) -> None:
    try:
        await asyncio.Future()  # ← 여기서 CancelledError 발생
    except asyncio.CancelledError:
        # 정리 작업 수행
        await self.cleanup_resources()
        raise  # ← 핵심: CancelledError 재발생
```

### 3. **취소 완료 대기**

```python
try:
    await server_task  # ← 취소가 완료될 때까지 대기
except asyncio.CancelledError:
    print("서버가 정상적으로 종료됨")
```

## ⚡ 동작 시나리오

### **Step 1: 서버 시작**

```python
server_task = asyncio.create_task(server.start_server())
# → 백그라운드에서 서버 실행 시작
```

### **Step 2: 클라이언트 테스트**

```python
await demo_client_interactions()
await demo_multiple_clients()
# → 서버가 계속 실행 중
```

### **Step 3: 취소 요청**

```python
server_task.cancel()
# → CancelledError 전송, 서버는 아직 실행 중
```

### **Step 4: 취소 완료 대기**

```python
await server_task
# → 서버에서 CancelledError 발생
# → 정리 작업 수행
# → CancelledError 재발생
# → 메인에서 CancelledError 수신
```

## 🚨 핵심 포인트

### **1. `await server_task`가 필수인 이유**

- `cancel()`은 **요청만 전송**하고 즉시 반환
- 실제 취소 완료를 기다리려면 `await` 필요
- 리소스 누수 방지를 위해 반드시 필요

### **2. `CancelledError`는 정상적인 신호**

- 예외가 아닌 **정상적인 취소 신호**
- 서버에서 `raise`를 해야 메인에서 수신 가능
- 정리 작업 후 반드시 재발생해야 함

### **3. 안전한 종료 보장**

- 서버가 처리 중인 연결들을 정리할 시간 제공
- 예측 가능한 종료 시점 보장
- 리소스 누수 방지

## 📊 다른 종료 방법들과의 비교

| 방법               | 안전성     | 예측성     | 권장도         |
| ------------------ | ---------- | ---------- | -------------- |
| `cancel() + await` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ **권장**    |
| 강제 종료          | ⭐         | ⭐         | ❌ 비권장      |
| 타임아웃 취소      | ⭐⭐⭐     | ⭐⭐⭐     | ⚠️ 상황에 따라 |
| 시그널 핸들러      | ⭐⭐⭐⭐   | ⭐⭐⭐⭐   | 🔄 외부 신호용 |
| 예외 기반          | ⭐⭐       | ⭐⭐       | 🎯 특수한 경우 |

## 💡 실무 최적 패턴

### **기본 패턴**

```python
# 1. 서버 시작
server_task = asyncio.create_task(server.start_server())

try:
    # 2. 비즈니스 로직 실행
    await business_logic()

finally:
    # 3. 안전한 종료
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        logger.info("서버 정상 종료")
```

### **우아한 종료 패턴**

```python
async def graceful_shutdown():
    # 1. 새 연결 차단
    # 2. 기존 클라이언트에게 종료 알림
    # 3. 클라이언트 연결 종료
    # 4. 리소스 정리
    pass
```

## 🔧 실제 웹소켓 서버에서의 활용

### **서버 구조**

```python
class WebSocketServer:
    async def start_server(self):
        try:
            async with websockets.serve(self.handler, host, port):
                await asyncio.Future()  # ← 여기서 대기
        except asyncio.CancelledError:
            await self.cleanup_resources()
            raise  # ← 핵심!
```

### **메인 프로그램**

```python
async def main():
    server = WebSocketServer()
    server_task = asyncio.create_task(server.start_server())

    try:
        # 클라이언트 테스트
        await demo_client_interactions()
        await demo_multiple_clients()

    finally:
        # 안전한 종료
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            print("서버 정상 종료")
```

## ⚠️ 주의사항

### **1. CancelledError 재발생 필수**

```python
# ❌ 잘못된 예시
except asyncio.CancelledError:
    await cleanup()
    # raise 없음 - 취소가 전파되지 않음!

# ✅ 올바른 예시
except asyncio.CancelledError:
    await cleanup()
    raise  # ← 반드시 필요!
```

### **2. await 없이 사용 금지**

```python
# ❌ 잘못된 예시
server_task.cancel()
print("서버 종료됨")  # ← 실제로는 아직 실행 중!

# ✅ 올바른 예시
server_task.cancel()
await server_task  # ← 취소 완료 대기
```

### **3. 예외 처리 필수**

```python
try:
    await server_task
except asyncio.CancelledError:
    # 정상적인 취소
    pass
except Exception as e:
    # 예상치 못한 오류
    logger.error(f"서버 오류: {e}")
```

## 🎯 결론

`server_task.cancel()`은 asyncio의 핵심 취소 메커니즘으로, **안전하고 예측 가능한 서버 종료**를 보장합니다.

### **핵심 원칙**

1. **`cancel()` + `await`** 조합 필수
2. **`CancelledError`는 정상적인 신호**
3. **서버에서 `raise` 필수**
4. **리소스 정리 후 재발생**

### **실무 적용**

- 웹소켓 서버 종료
- 백그라운드 작업 중단
- 리소스 정리 보장
- 예측 가능한 프로그램 종료

이 메커니즘을 올바르게 이해하고 활용하면 안정적이고 견고한 비동기 애플리케이션을 구축할 수 있습니다.
