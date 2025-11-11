"""
실시간 채팅 애플리케이션
asyncio와 웹소켓을 결합한 실전 예제
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("websockets 라이브러리가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요: pip install websockets")
    exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """메시지 타입 열거형"""

    JOIN = "join"
    LEAVE = "leave"
    MESSAGE = "message"
    USER_LIST = "user_list"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class User:
    """사용자 정보"""

    id: str
    username: str
    websocket: WebSocketServerProtocol
    joined_at: datetime
    last_activity: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "joined_at": self.joined_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }


@dataclass
class ChatMessage:
    """채팅 메시지"""

    id: str
    user_id: str
    username: str
    message: str
    timestamp: datetime
    message_type: MessageType = MessageType.MESSAGE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "type": self.message_type.value,
        }


class ChatRoom:
    """채팅방 관리 클래스"""

    def __init__(self, room_id: str = "general"):
        self.room_id = room_id
        self.users: Dict[str, User] = {}
        self.message_history: List[ChatMessage] = []
        self.max_history = 100  # 최대 메시지 히스토리 수

    async def add_user(self, websocket: WebSocketServerProtocol, username: str) -> User:
        """사용자 추가"""
        user_id = str(uuid.uuid4())
        now = datetime.now()

        user = User(
            id=user_id,
            username=username,
            websocket=websocket,
            joined_at=now,
            last_activity=now,
        )

        self.users[user_id] = user

        # 입장 메시지 생성
        join_message = ChatMessage(
            id=str(uuid.uuid4()),
            user_id="system",
            username="System",
            message=f"{username}님이 입장했습니다.",
            timestamp=now,
            message_type=MessageType.JOIN,
        )

        await self.broadcast_message(join_message)
        await self.send_user_list()

        logger.info(f"사용자 추가: {username} (ID: {user_id})")
        return user

    async def remove_user(self, user_id: str) -> None:
        """사용자 제거"""
        if user_id in self.users:
            user = self.users[user_id]
            del self.users[user_id]

            # 퇴장 메시지 생성
            leave_message = ChatMessage(
                id=str(uuid.uuid4()),
                user_id="system",
                username="System",
                message=f"{user.username}님이 퇴장했습니다.",
                timestamp=datetime.now(),
                message_type=MessageType.LEAVE,
            )

            await self.broadcast_message(leave_message)
            await self.send_user_list()

            logger.info(f"사용자 제거: {user.username} (ID: {user_id})")

    async def send_message(self, user_id: str, message: str) -> None:
        """메시지 전송"""
        if user_id not in self.users:
            return

        user = self.users[user_id]
        user.last_activity = datetime.now()

        # 채팅 메시지 생성
        chat_message = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            username=user.username,
            message=message,
            timestamp=datetime.now(),
        )

        # 메시지 히스토리에 추가
        self.message_history.append(chat_message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        # 모든 사용자에게 브로드캐스트
        await self.broadcast_message(chat_message)

    async def broadcast_message(self, message: ChatMessage) -> None:
        """메시지 브로드캐스트"""
        if not self.users:
            return

        message_data = json.dumps(message.to_dict())
        disconnected_users = []

        for user in self.users.values():
            try:
                await user.websocket.send(message_data)
            except ConnectionClosed:
                disconnected_users.append(user.id)
            except Exception as e:
                logger.error(f"메시지 전송 실패 (사용자: {user.username}): {e}")
                disconnected_users.append(user.id)

        # 연결이 끊어진 사용자들 제거
        for user_id in disconnected_users:
            await self.remove_user(user_id)

    async def send_user_list(self) -> None:
        """사용자 목록 전송"""
        user_list_data = {
            "type": MessageType.USER_LIST.value,
            "users": [user.to_dict() for user in self.users.values()],
            "timestamp": datetime.now().isoformat(),
        }

        message_data = json.dumps(user_list_data)
        disconnected_users = []

        for user in self.users.values():
            try:
                await user.websocket.send(message_data)
            except ConnectionClosed:
                disconnected_users.append(user.id)
            except Exception as e:
                logger.error(f"사용자 목록 전송 실패 (사용자: {user.username}): {e}")
                disconnected_users.append(user.id)

        # 연결이 끊어진 사용자들 제거
        for user_id in disconnected_users:
            await self.remove_user(user_id)

    async def send_message_history(self, user_id: str, limit: int = 20) -> None:
        """메시지 히스토리 전송"""
        if user_id not in self.users:
            return

        user = self.users[user_id]
        recent_messages = self.message_history[-limit:] if self.message_history else []

        history_data = {
            "type": "message_history",
            "messages": [msg.to_dict() for msg in recent_messages],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await user.websocket.send(json.dumps(history_data))
        except Exception as e:
            logger.error(f"메시지 히스토리 전송 실패: {e}")

    def get_room_stats(self) -> dict:
        """채팅방 통계"""
        return {
            "room_id": self.room_id,
            "user_count": len(self.users),
            "message_count": len(self.message_history),
            "users": [user.to_dict() for user in self.users.values()],
        }


class ChatServer:
    """채팅 서버 클래스"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.chat_room = ChatRoom()
        self.heartbeat_interval = 30  # 30초마다 하트비트

    async def handle_client(
        self, websocket: WebSocketServerProtocol, path: str
    ) -> None:
        """클라이언트 연결 처리"""
        user = None

        try:
            # 사용자명 요청
            await websocket.send(
                json.dumps(
                    {"type": "request_username", "message": "사용자명을 입력하세요:"}
                )
            )

            # 사용자명 수신
            username_response = await websocket.recv()
            username_data = json.loads(username_response)
            username = username_data.get("username", f"User_{uuid.uuid4().hex[:8]}")

            # 사용자 추가
            user = await self.chat_room.add_user(websocket, username)

            # 메시지 히스토리 전송
            await self.chat_room.send_message_history(user.id, 20)

            # 메시지 수신 루프
            async for message in websocket:
                await self.process_message(user, message)

        except ConnectionClosed:
            logger.info("클라이언트 연결이 정상적으로 종료되었습니다")
        except Exception as e:
            logger.error(f"클라이언트 처리 중 오류 발생: {e}")
        finally:
            if user:
                await self.chat_room.remove_user(user.id)

    async def process_message(self, user: User, message: str) -> None:
        """메시지 처리"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "message")

            if message_type == "chat_message":
                # 채팅 메시지
                chat_text = data.get("message", "").strip()
                if chat_text:
                    await self.chat_room.send_message(user.id, chat_text)

            elif message_type == "heartbeat":
                # 하트비트 응답
                user.last_activity = datetime.now()
                await user.websocket.send(
                    json.dumps(
                        {
                            "type": "heartbeat_response",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )

            elif message_type == "get_users":
                # 사용자 목록 요청
                await self.chat_room.send_user_list()

            elif message_type == "get_history":
                # 메시지 히스토리 요청
                limit = data.get("limit", 20)
                await self.chat_room.send_message_history(user.id, limit)

            else:
                # 알 수 없는 메시지 타입
                await user.websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"알 수 없는 메시지 타입: {message_type}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )

        except json.JSONDecodeError:
            # JSON이 아닌 일반 텍스트 메시지
            if message.strip():
                await self.chat_room.send_message(user.id, message)
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")

    async def heartbeat_monitor(self) -> None:
        """하트비트 모니터링"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)

            current_time = datetime.now()
            inactive_users = []

            # 비활성 사용자 확인
            for user in self.chat_room.users.values():
                time_diff = (current_time - user.last_activity).total_seconds()
                if time_diff > self.heartbeat_interval * 2:  # 2배 시간 동안 비활성
                    inactive_users.append(user.id)

            # 비활성 사용자 제거
            for user_id in inactive_users:
                await self.chat_room.remove_user(user_id)
                logger.info(f"비활성 사용자 제거: {user_id}")

    async def start_server(self) -> None:
        """서버 시작"""
        logger.info(f"채팅 서버 시작: ws://{self.host}:{self.port}")

        # 하트비트 모니터링 시작
        heartbeat_task = asyncio.create_task(self.heartbeat_monitor())

        try:
            # 핸들러 래퍼 함수 생성 (self 바인딩을 위해 필요)
            # websockets 라이브러리 버전에 따라 인자 개수가 다를 수 있음
            async def handler(websocket: WebSocketServerProtocol, *args) -> None:
                path = args[0] if args else ""
                await self.handle_client(websocket, path)

            async with websockets.serve(
                handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            ):
                logger.info("채팅 서버가 실행 중입니다.")
                await asyncio.Future()  # 서버를 계속 실행
        finally:
            heartbeat_task.cancel()


class ChatClient:
    """채팅 클라이언트 클래스"""

    def __init__(self, uri: str, username: str):
        self.uri = uri
        self.username = username
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False

    async def connect(self) -> None:
        """서버에 연결"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.running = True
            logger.info(f"채팅 서버에 연결됨: {self.uri}")

            # 사용자명 전송
            await self.websocket.send(json.dumps({"username": self.username}))

        except Exception as e:
            logger.error(f"서버 연결 실패: {e}")
            raise

    async def disconnect(self) -> None:
        """서버 연결 해제"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("서버 연결 해제")

    async def send_message(self, message: str) -> None:
        """메시지 전송"""
        if not self.websocket or not self.running:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message_data = {"type": "chat_message", "message": message}
        await self.websocket.send(json.dumps(message_data))

    async def listen_for_messages(self) -> None:
        """메시지 수신 대기"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        try:
            async for message in self.websocket:
                if not self.running:
                    break

                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")

                    if message_type == "request_username":
                        # 사용자명 요청 (이미 연결 시 전송됨)
                        continue
                    elif message_type == "message_history":
                        # 메시지 히스토리
                        messages = data.get("messages", [])
                        print(f"\n=== 최근 메시지 ({len(messages)}개) ===")
                        for msg in messages:
                            timestamp = datetime.fromisoformat(msg["timestamp"])
                            print(
                                f"[{timestamp.strftime('%H:%M:%S')}] {msg['username']}: {msg['message']}"
                            )
                        print("=== 현재 채팅 ===\n")
                    elif message_type == "user_list":
                        # 사용자 목록
                        users = data.get("users", [])
                        print(
                            f"\n현재 접속자 ({len(users)}명): {', '.join([u['username'] for u in users])}\n"
                        )
                    elif message_type in ["join", "leave"]:
                        # 입장/퇴장 메시지
                        print(f"📢 {data.get('message', '')}")
                    elif message_type == "error":
                        # 오류 메시지
                        print(f"❌ 오류: {data.get('message', '')}")
                    else:
                        # 일반 채팅 메시지
                        timestamp = datetime.fromisoformat(data["timestamp"])
                        print(
                            f"[{timestamp.strftime('%H:%M:%S')}] {data['username']}: {data['message']}"
                        )

                except json.JSONDecodeError:
                    # JSON이 아닌 일반 텍스트
                    print(f"서버 메시지: {message}")

        except ConnectionClosed:
            logger.info("서버 연결이 종료되었습니다")
        except Exception as e:
            logger.error(f"메시지 수신 중 오류: {e}")

    async def start_interactive_mode(self) -> None:
        """대화형 모드 시작"""
        print(f"채팅 클라이언트 시작 (사용자: {self.username})")
        print("명령어: /users (사용자 목록), /history (메시지 히스토리), /quit (종료)")
        print("-" * 50)

        # 메시지 수신 태스크 시작
        receive_task = asyncio.create_task(self.listen_for_messages())

        try:
            while self.running:
                # 사용자 입력 받기 (타임아웃 제거)
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input
                    )

                    if user_input.strip():
                        if user_input.strip() == "/quit":
                            break
                        elif user_input.strip() == "/users":
                            await self.websocket.send(json.dumps({"type": "get_users"}))
                        elif user_input.strip() == "/history":
                            await self.websocket.send(
                                json.dumps({"type": "get_history", "limit": 10})
                            )
                        else:
                            await self.send_message(user_input)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"입력 처리 중 오류: {e}")
                    break

        finally:
            self.running = False
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass


async def demo_chat_server():
    """채팅 서버 데모"""
    server = ChatServer()

    # 서버를 백그라운드 태스크로 실행
    server_task = asyncio.create_task(server.start_server())

    print("\n채팅 서버가 실행 중입니다.")
    print("명령어: 'stop' 또는 'quit' 입력 시 서버 종료")
    print("-" * 50)

    try:
        # 사용자 입력을 받아서 서버 종료
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)

                if user_input.strip().lower() in ["stop", "quit", "exit"]:
                    print("서버 종료 중...")
                    break
                else:
                    print("알 수 없는 명령어입니다. 'stop' 또는 'quit'를 입력하세요.")

            except KeyboardInterrupt:
                print("\n서버 종료 중...")
                break
            except Exception as e:
                logger.error(f"입력 처리 중 오류: {e}")
                break
    finally:
        # 서버 태스크 취소
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        print("서버가 종료되었습니다.")


async def demo_chat_client():
    """채팅 클라이언트 데모"""
    import random

    username = f"User_{random.randint(1000, 9999)}"
    client = ChatClient("ws://localhost:8765", username)

    try:
        await client.connect()
        await client.start_interactive_mode()
    finally:
        await client.disconnect()


async def main():
    """메인 함수"""
    print("실시간 채팅 애플리케이션 데모")
    print("1. 서버 실행")
    print("2. 클라이언트 실행")
    print("3. 종료")

    choice = input("선택하세요 (1-3): ").strip()

    if choice == "1":
        print("채팅 서버를 시작합니다...")
        await demo_chat_server()
    elif choice == "2":
        print("채팅 클라이언트를 시작합니다...")
        await demo_chat_client()
    else:
        print("프로그램을 종료합니다.")


if __name__ == "__main__":
    asyncio.run(main())
