#!/usr/bin/env python3
"""
웹소켓 서버 테스트
"""
import asyncio
import websockets
import json


async def test_websocket():
    """웹소켓 서버 테스트"""
    try:
        # 서버에 연결
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            print("✅ 서버 연결 성공")

            # 텍스트 메시지 전송
            await websocket.send("Hello Server!")
            response = await websocket.recv()
            print(f"서버 응답: {response}")

            # JSON 메시지 전송
            ping_data = {"type": "ping"}
            await websocket.send(json.dumps(ping_data))
            response = await websocket.recv()
            print(f"핑 응답: {response}")

            print("✅ 웹소켓 테스트 완료")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
