"""
웹소켓 기초 예제
웹소켓 서버와 클라이언트의 기본 사용법을 학습합니다.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Dict, Set, Optional, Any
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed


# 로깅 설정 (UTF-8 인코딩 지원)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


class WebSocketServer:
    """웹소켓 서버 클래스"""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.clients: Set[Any] = set()
        self.message_count = 0
        self.ready = asyncio.Event()  # 서버 준비 상태 이벤트

    async def register_client(self, websocket: Any) -> None:
        """새 클라이언트 등록"""
        self.clients.add(websocket)
        logger.info(f"새 클라이언트 연결: {websocket.remote_address}")
        logger.info(f"현재 연결된 클라이언트 수: {len(self.clients)}")

    async def unregister_client(self, websocket: Any) -> None:
        """클라이언트 연결 해제"""
        self.clients.discard(websocket)
        logger.info(f"클라이언트 연결 해제: {websocket.remote_address}")
        logger.info(f"현재 연결된 클라이언트 수: {len(self.clients)}")

    async def broadcast_message(
        self, message: str, sender: Optional[Any] = None
    ) -> None:
        """모든 클라이언트에게 메시지 브로드캐스트"""
        if not self.clients:
            return

        # 연결이 끊어진 클라이언트 제거
        disconnected_clients = set()

        for client in self.clients.copy():
            try:
                await client.send(message)
            except ConnectionClosed:
                disconnected_clients.add(client)

        # 끊어진 연결 제거
        for client in disconnected_clients:
            await self.unregister_client(client)

    async def handle_client(self, websocket: Any) -> None:
        """클라이언트 연결 처리"""
        client_addr = websocket.remote_address
        await self.register_client(websocket)

        try:
            async for message in websocket:
                try:
                    await self.process_message(websocket, message)
                except Exception as e:
                    logger.error(
                        f"❌ 메시지 처리 중 오류 (클라이언트: {client_addr}): {e}"
                    )
                    # 메시지 처리 오류가 전체 연결을 끊지 않도록 함
        except ConnectionClosed:
            logger.info(f"클라이언트 연결 정상 종료: {client_addr}")
        except Exception as e:
            logger.error(
                f"❌ 클라이언트 처리 중 심각한 오류 (클라이언트: {client_addr}): {e}"
            )
            import traceback

            logger.error(traceback.format_exc())
        finally:
            await self.unregister_client(websocket)

    async def process_message(self, websocket: Any, message: str) -> None:
        """메시지 처리"""
        self.message_count += 1

        try:
            # JSON 메시지 파싱 시도
            data = json.loads(message)
            message_type = data.get("type", "unknown")

            if message_type == "echo":
                # 에코 메시지
                response = {
                    "type": "echo_response",
                    "original_message": data.get("message", ""),
                    "timestamp": datetime.now().isoformat(),
                    "server_message_count": self.message_count,
                }
                await websocket.send(json.dumps(response, ensure_ascii=False))

            elif message_type == "broadcast":
                # 브로드캐스트 메시지
                broadcast_data = {
                    "type": "broadcast",
                    "message": data.get("message", ""),
                    "sender": str(websocket.remote_address),
                    "timestamp": datetime.now().isoformat(),
                }
                await self.broadcast_message(
                    json.dumps(broadcast_data, ensure_ascii=False), websocket
                )

            elif message_type == "ping":
                # 핑 메시지
                pong_response = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(pong_response, ensure_ascii=False))

            else:
                # 알 수 없는 메시지 타입
                error_response = {
                    "type": "error",
                    "message": f"알 수 없는 메시지 타입: {message_type}",
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(error_response, ensure_ascii=False))

        except json.JSONDecodeError:
            # JSON이 아닌 일반 텍스트 메시지
            response = (
                f"서버가 받은 메시지: {message} (메시지 번호: {self.message_count})"
            )
            await websocket.send(response)

    async def start_server(self) -> None:
        """서버 시작"""
        logger.info(f"웹소켓 서버 시작 시도: ws://{self.host}:{self.port}")

        async def handler(websocket):
            await self.handle_client(websocket)

        try:
            async with websockets.serve(
                handler,
                self.host,
                self.port,
                ping_interval=20,  # 20초마다 핑 전송
                ping_timeout=10,  # 10초 내 핑 응답 없으면 연결 종료
                close_timeout=10,  # 연결 종료 타임아웃
            ):
                logger.info(
                    f"✅ 서버가 성공적으로 시작됨: ws://{self.host}:{self.port}"
                )
                self.ready.set()  # 서버 준비 완료 신호
                await asyncio.Future()  # 서버를 계속 실행
        except Exception as e:
            logger.error(f"❌ 서버 시작 실패: {e}")
            raise


class WebSocketClient:
    """웹소켓 클라이언트 클래스"""

    def __init__(self, uri: str):
        self.uri = uri
        self.websocket: Optional[Any] = None

    async def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """서버에 연결 (재시도 로직 포함)"""
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"서버 연결 시도 {attempt}/{max_retries}: {self.uri}")
                self.websocket = await websockets.connect(self.uri)
                logger.info(f"✅ 서버에 연결됨: {self.uri}")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  연결 실패 (시도 {attempt}/{max_retries}): {e}")

                if attempt < max_retries:
                    logger.info(f"   {retry_delay}초 후 재시도...")
                    await asyncio.sleep(retry_delay)

        logger.error(f"❌ 서버 연결 실패 (모든 재시도 소진): {last_error}")
        raise last_error if last_error else RuntimeError("연결 실패")

    async def disconnect(self) -> None:
        """서버 연결 해제"""
        if self.websocket:
            await self.websocket.close()
            logger.info("서버 연결 해제")

    async def send_message(self, message: str) -> None:
        """메시지 전송"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        await self.websocket.send(message)
        # JSON 문자열인 경우 예쁘게 포맷팅하여 로그 출력
        try:
            data = json.loads(message)
            logger.info(
                f"메시지 전송: {json.dumps(data, ensure_ascii=False, indent=2)}"
            )
        except (json.JSONDecodeError, TypeError):
            logger.info(f"메시지 전송: {message}")

    async def send_json(self, data: dict) -> None:
        """JSON 메시지 전송"""
        message = json.dumps(data, ensure_ascii=False)
        await self.send_message(message)

    async def receive_message(self) -> str:
        """메시지 수신"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = await self.websocket.recv()
        # JSON 문자열인 경우 예쁘게 포맷팅하여 로그 출력
        try:
            data = json.loads(message)
            logger.info(
                f"메시지 수신: {json.dumps(data, ensure_ascii=False, indent=2)}"
            )
        except (json.JSONDecodeError, TypeError):
            logger.info(f"메시지 수신: {message}")
        return message

    async def listen_for_messages(self) -> None:
        """메시지 수신 대기"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        try:
            async for message in self.websocket:
                # JSON 문자열인 경우 예쁘게 포맷팅하여 로그 출력
                try:
                    data = json.loads(message)
                    logger.info(
                        f"수신된 메시지: {json.dumps(data, ensure_ascii=False, indent=2)}"
                    )
                except (json.JSONDecodeError, TypeError):
                    logger.info(f"수신된 메시지: {message}")
        except ConnectionClosed:
            logger.info("서버 연결이 종료되었습니다")
        except Exception as e:
            logger.error(f"메시지 수신 중 오류: {e}")


async def demo_client_interactions():
    """클라이언트 상호작용 데모"""
    client = WebSocketClient("ws://localhost:8000")

    try:
        logger.info("📱 단일 클라이언트 데모 시작")
        await client.connect()

        # 1. 일반 텍스트 메시지 전송
        logger.info("1️⃣  일반 텍스트 메시지 전송")
        await client.send_message("안녕하세요, 서버!")

        # 2. JSON 메시지 전송 (에코)
        logger.info("2️⃣  에코 메시지 전송")
        echo_data = {"type": "echo", "message": "이 메시지를 에코해주세요"}
        await client.send_json(echo_data)

        # 3. 핑 메시지 전송
        logger.info("3️⃣  핑 메시지 전송")
        ping_data = {"type": "ping"}
        await client.send_json(ping_data)

        # 4. 브로드캐스트 메시지 전송
        logger.info("4️⃣  브로드캐스트 메시지 전송")
        broadcast_data = {
            "type": "broadcast",
            "message": "모든 클라이언트에게 전송되는 메시지입니다",
        }
        await client.send_json(broadcast_data)

        # 응답 수신
        logger.info("📥 응답 수신 대기 중...")
        for i in range(4):
            try:
                response = await asyncio.wait_for(client.receive_message(), timeout=2.0)
                print(f"   응답 {i+1}: {response}")
            except asyncio.TimeoutError:
                logger.warning(f"⏱️  응답 {i+1} 타임아웃")
                break

        logger.info("✅ 단일 클라이언트 데모 완료")

    except Exception as e:
        logger.error(f"❌ 클라이언트 데모 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        await client.disconnect()


async def demo_multiple_clients():
    """여러 클라이언트 데모"""
    clients = []

    try:
        logger.info("👥 다중 클라이언트 데모 시작")

        # 3개의 클라이언트 생성
        for i in range(3):
            logger.info(f"🔌 클라이언트 {i+1} 연결 중...")
            client = WebSocketClient(f"ws://localhost:8000")
            await client.connect()
            clients.append(client)
            logger.info(f"✅ 클라이언트 {i+1} 연결됨")

            # 각 클라이언트가 브로드캐스트 메시지 전송
            broadcast_data = {
                "type": "broadcast",
                "message": f"클라이언트 {i+1}에서 전송한 메시지",
            }
            await client.send_json(broadcast_data)

            # 잠시 대기
            await asyncio.sleep(0.5)

        # 모든 클라이언트의 응답 수신
        logger.info("📥 모든 클라이언트의 응답 수신 중...")
        for idx, client in enumerate(clients, 1):
            try:
                response = await asyncio.wait_for(client.receive_message(), timeout=1.0)
                print(f"   클라이언트 {idx} 응답: {response}")
            except asyncio.TimeoutError:
                logger.warning(f"⏱️  클라이언트 {idx} 응답 타임아웃")

        logger.info("✅ 다중 클라이언트 데모 완료")

    except Exception as e:
        logger.error(f"❌ 다중 클라이언트 데모 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        # 모든 클라이언트 연결 해제
        logger.info("🔌 모든 클라이언트 연결 해제 중...")
        for client in clients:
            await client.disconnect()


async def main():
    """메인 함수"""
    print("웹소켓 기초 학습을 시작합니다...\n")

    # 서버 시작 (백그라운드)
    server = WebSocketServer()
    server_task = asyncio.create_task(server.start_server())

    # 서버 준비 대기 (최대 5초)
    try:
        logger.info("⏳ 서버 준비 대기 중...")
        await asyncio.wait_for(server.ready.wait(), timeout=5.0)
        logger.info("✅ 서버 준비 완료")
    except asyncio.TimeoutError:
        logger.error("❌ 서버 시작 타임아웃 (5초 초과)")
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        return

    # 서버 태스크 상태 확인 함수
    def check_server_status():
        if server_task.done():
            logger.error("❌ 서버 태스크가 예기치 않게 종료됨!")
            if server_task.exception():
                logger.error(f"   예외: {server_task.exception()}")
            return False
        return True

    print("\n=== 단일 클라이언트 데모 ===")
    if not check_server_status():
        return
    await demo_client_interactions()

    print("\n=== 여러 클라이언트 데모 ===")
    if not check_server_status():
        return
    await demo_multiple_clients()

    print("\n[OK] 클라이언트 테스트 완료")

    # 서버 정상 종료
    print("[STOP] 서버 종료 시작")
    server_task.cancel()

    try:
        await server_task  # ← 이 부분이 중요!
        print("[OK] 서버 종료 완료")
    except asyncio.CancelledError:
        print("[OK] 서버가 정상적으로 종료됨")

    print("[DONE] 프로그램 종료")
    print("\n웹소켓 기초 학습이 완료되었습니다!")


if __name__ == "__main__":
    asyncio.run(main())
