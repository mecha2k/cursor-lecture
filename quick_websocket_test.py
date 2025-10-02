#!/usr/bin/env python3
"""
빠른 웹소켓 테스트 - 원본 코드 사용
"""
import asyncio
from websockets_test import test_websocket


async def main():
    # 서버 시작
    from websocket_basics import WebSocketServer

    server = WebSocketServer()
    server_task = asyncio.create_task(server.start_server())

    # 잠시 대기 후 테스트
    await asyncio.sleep(1)

    # 간단한 클라이언트 테스트
    import websockets
    import json

    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            print("✅ 연결 성공")

            # 텍스트 메시지
            await websocket.send("Hello Server!")
            response = await websocket.recv()
            print(f"응답: {response}")

            # JSON 메시지
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"핑 응답: {response}")

            print("✅ 웹소켓 기본 기능 정상 작동!")

    except Exception as e:
        print(f"❌ 오류: {e}")

    # 서버 종료
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
