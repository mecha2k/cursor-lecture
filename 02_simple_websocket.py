#!/usr/bin/env python3
"""
간단한 웹소켓 서버 테스트
"""
import asyncio
import websockets
import json
from datetime import datetime


class SimpleWebSocketServer:
    def __init__(self):
        self.clients = set()

    async def handle_client(self, websocket):
        """클라이언트 연결 처리"""
        self.clients.add(websocket)
        print(f"클라이언트 연결: {websocket.remote_address}")

        try:
            async for message in websocket:
                print(f"받은 메시지: {message}")

                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        response = {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat(),
                        }
                        await websocket.send(json.dumps(response))
                    else:
                        await websocket.send(f"에코: {message}")
                except json.JSONDecodeError:
                    await websocket.send(f"에코: {message}")

        except websockets.exceptions.ConnectionClosed:
            print("클라이언트 연결 종료")
        finally:
            self.clients.discard(websocket)

    async def start_server(self):
        """서버 시작"""
        print("웹소켓 서버 시작: ws://localhost:8765")

        async with websockets.serve(self.handle_client, "localhost", 8765):
            print("서버 실행 중...")
            await asyncio.Future()  # 무한 대기


async def test_client():
    """클라이언트 테스트"""
    await asyncio.sleep(1)  # 서버 시작 대기

    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            print("✅ 클라이언트 연결 성공")

            # 텍스트 메시지
            await websocket.send("Hello!")
            response = await websocket.recv()
            print(f"응답: {response}")

            # JSON 메시지
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"핑 응답: {response}")

            print("✅ 테스트 완료")

    except Exception as e:
        print(f"❌ 클라이언트 오류: {e}")


async def main():
    """메인 함수"""
    server = SimpleWebSocketServer()

    # 서버와 클라이언트를 동시에 실행
    server_task = asyncio.create_task(server.start_server())
    client_task = asyncio.create_task(test_client())

    # 클라이언트 테스트 완료 후 서버 종료
    await client_task
    server_task.cancel()

    try:
        await server_task
    except asyncio.CancelledError:
        pass

    print("테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
