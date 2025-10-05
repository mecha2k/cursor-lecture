"""
웹소켓 기초 예제
웹소켓 서버와 클라이언트의 기본 사용법을 학습합니다.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketServer:
    """웹소켓 서버 클래스"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[Any] = set()
        self.message_count = 0

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
        await self.register_client(websocket)

        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except ConnectionClosed:
            logger.info("클라이언트 연결이 정상적으로 종료되었습니다")
        except Exception as e:
            logger.error(f"클라이언트 처리 중 오류 발생: {e}")
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
                await websocket.send(json.dumps(response))

            elif message_type == "broadcast":
                # 브로드캐스트 메시지
                broadcast_data = {
                    "type": "broadcast",
                    "message": data.get("message", ""),
                    "sender": str(websocket.remote_address),
                    "timestamp": datetime.now().isoformat(),
                }
                await self.broadcast_message(json.dumps(broadcast_data), websocket)

            elif message_type == "ping":
                # 핑 메시지
                pong_response = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(pong_response))

            else:
                # 알 수 없는 메시지 타입
                error_response = {
                    "type": "error",
                    "message": f"알 수 없는 메시지 타입: {message_type}",
                    "timestamp": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(error_response))

        except json.JSONDecodeError:
            # JSON이 아닌 일반 텍스트 메시지
            response = (
                f"서버가 받은 메시지: {message} (메시지 번호: {self.message_count})"
            )
            await websocket.send(response)

    async def start_server(self) -> None:
        """서버 시작"""
        logger.info(f"웹소켓 서버 시작: ws://{self.host}:{self.port}")

        async def handler(websocket):
            await self.handle_client(websocket)

        async with websockets.serve(
            handler,
            self.host,
            self.port,
            ping_interval=20,  # 20초마다 핑 전송
            ping_timeout=10,  # 10초 내 핑 응답 없으면 연결 종료
            close_timeout=10,  # 연결 종료 타임아웃
        ):
            logger.info("서버가 실행 중입니다. Ctrl+C로 종료하세요.")
            await asyncio.Future()  # 서버를 계속 실행


class WebSocketClient:
    """웹소켓 클라이언트 클래스"""

    def __init__(self, uri: str):
        self.uri = uri
        self.websocket: Optional[Any] = None

    async def connect(self) -> None:
        """서버에 연결"""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"서버에 연결됨: {self.uri}")
        except Exception as e:
            logger.error(f"서버 연결 실패: {e}")
            raise

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
        logger.info(f"메시지 전송: {message}")

    async def send_json(self, data: dict) -> None:
        """JSON 메시지 전송"""
        message = json.dumps(data)
        await self.send_message(message)

    async def receive_message(self) -> str:
        """메시지 수신"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = await self.websocket.recv()
        logger.info(f"메시지 수신: {message}")
        return message

    async def listen_for_messages(self) -> None:
        """메시지 수신 대기"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        try:
            async for message in self.websocket:
                logger.info(f"수신된 메시지: {message}")
        except ConnectionClosed:
            logger.info("서버 연결이 종료되었습니다")
        except Exception as e:
            logger.error(f"메시지 수신 중 오류: {e}")


async def demo_client_interactions():
    """클라이언트 상호작용 데모"""
    client = WebSocketClient("ws://localhost:8765")

    try:
        await client.connect()

        # 1. 일반 텍스트 메시지 전송
        await client.send_message("안녕하세요, 서버!")

        # 2. JSON 메시지 전송 (에코)
        echo_data = {"type": "echo", "message": "이 메시지를 에코해주세요"}
        await client.send_json(echo_data)

        # 3. 핑 메시지 전송
        ping_data = {"type": "ping"}
        await client.send_json(ping_data)

        # 4. 브로드캐스트 메시지 전송
        broadcast_data = {
            "type": "broadcast",
            "message": "모든 클라이언트에게 전송되는 메시지입니다",
        }
        await client.send_json(broadcast_data)

        # 응답 수신
        for _ in range(4):
            try:
                response = await asyncio.wait_for(client.receive_message(), timeout=2.0)
                print(f"서버 응답: {response}")
            except asyncio.TimeoutError:
                print("응답 타임아웃")
                break

    except Exception as e:
        logger.error(f"클라이언트 데모 오류: {e}")
    finally:
        await client.disconnect()


async def demo_multiple_clients():
    """여러 클라이언트 데모"""
    clients = []

    try:
        # 3개의 클라이언트 생성
        for i in range(3):
            client = WebSocketClient(f"ws://localhost:8765")
            await client.connect()
            clients.append(client)

            # 각 클라이언트가 브로드캐스트 메시지 전송
            broadcast_data = {
                "type": "broadcast",
                "message": f"클라이언트 {i+1}에서 전송한 메시지",
            }
            await client.send_json(broadcast_data)

            # 잠시 대기
            await asyncio.sleep(0.5)

        # 모든 클라이언트의 응답 수신
        for client in clients:
            try:
                response = await asyncio.wait_for(client.receive_message(), timeout=1.0)
                print(f"클라이언트 응답: {response}")
            except asyncio.TimeoutError:
                print("응답 타임아웃")

    finally:
        # 모든 클라이언트 연결 해제
        for client in clients:
            await client.disconnect()


async def main():
    """메인 함수"""
    print("웹소켓 기초 학습을 시작합니다...\n")

    # 서버 시작 (백그라운드)
    server = WebSocketServer()
    server_task = asyncio.create_task(server.start_server())

    # 서버 시작 대기
    await asyncio.sleep(1)

    print("=== 단일 클라이언트 데모 ===")
    await demo_client_interactions()

    print("\n=== 여러 클라이언트 데모 ===")
    await demo_multiple_clients()

    print("✅ 클라이언트 테스트 완료")

    # 여기서 await server_task를 하지 않으면?
    print("⚠️  main() 함수가 끝나려고 함...")

    # 서버 정상 종료
    print("🛑 서버 종료 시작")
    server_task.cancel()

    try:
        await server_task  # ← 이 부분이 중요!
        print("✅ 서버 종료 완료")
    except asyncio.CancelledError:
        print("✅ 서버가 정상적으로 종료됨")

    print("🏁 프로그램 종료")

    print("\n웹소켓 기초 학습이 완료되었습니다!")


if __name__ == "__main__":
    asyncio.run(main())
