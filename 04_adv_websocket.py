"""
고급 웹소켓 애플리케이션
실시간 데이터 스트리밍, 모니터링, 부하 분산 등 고급 기능 구현
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics

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


class StreamType(Enum):
    """스트림 타입"""

    SENSOR_DATA = "sensor_data"
    SYSTEM_METRICS = "system_metrics"
    USER_ACTIVITY = "user_activity"
    MARKET_DATA = "market_data"
    LOG_EVENTS = "log_events"


@dataclass
class StreamData:
    """스트림 데이터"""

    id: str
    stream_type: StreamType
    data: Dict[str, Any]
    timestamp: datetime
    source: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stream_type": self.stream_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


@dataclass
class ClientSubscription:
    """클라이언트 구독 정보"""

    client_id: str
    stream_types: Set[StreamType]
    filters: Dict[str, Any]
    last_activity: datetime


class StreamProcessor:
    """스트림 데이터 처리기"""

    def __init__(self):
        self.processors: Dict[StreamType, List[Callable]] = defaultdict(list)
        self.aggregators: Dict[StreamType, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

    def register_processor(self, stream_type: StreamType, processor: Callable) -> None:
        """스트림 처리기 등록"""
        self.processors[stream_type].append(processor)

    async def process_data(self, data: StreamData) -> StreamData:
        """데이터 처리"""
        # 데이터 집계
        self.aggregators[data.stream_type].append(data)

        # 등록된 처리기들 실행
        for processor in self.processors[data.stream_type]:
            try:
                data = await processor(data)
            except Exception as e:
                logger.error(f"데이터 처리 중 오류: {e}")

        return data

    def get_aggregated_data(
        self, stream_type: StreamType, window_size: int = 100
    ) -> Dict[str, Any]:
        """집계된 데이터 반환"""
        data_points = list(self.aggregators[stream_type])[-window_size:]

        if not data_points:
            return {}

        # 기본 통계 계산
        if stream_type == StreamType.SENSOR_DATA:
            values = [point.data.get("value", 0) for point in data_points]
            return {
                "count": len(values),
                "mean": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0,
                "latest": values[-1] if values else None,
            }
        elif stream_type == StreamType.SYSTEM_METRICS:
            cpu_values = [point.data.get("cpu_usage", 0) for point in data_points]
            memory_values = [point.data.get("memory_usage", 0) for point in data_points]
            return {
                "cpu": {
                    "mean": statistics.mean(cpu_values),
                    "max": max(cpu_values),
                    "current": cpu_values[-1] if cpu_values else None,
                },
                "memory": {
                    "mean": statistics.mean(memory_values),
                    "max": max(memory_values),
                    "current": memory_values[-1] if memory_values else None,
                },
            }

        return {"count": len(data_points)}


class LoadBalancer:
    """로드 밸런서"""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.server_weights: Dict[str, float] = {}
        self.current_connections: Dict[str, int] = defaultdict(int)

    def add_server(self, server_id: str, capacity: int, weight: float = 1.0) -> None:
        """서버 추가"""
        self.servers[server_id] = {
            "capacity": capacity,
            "weight": weight,
            "status": "active",
        }
        self.server_weights[server_id] = weight

    def get_best_server(self) -> Optional[str]:
        """최적 서버 선택"""
        available_servers = [
            server_id
            for server_id, server in self.servers.items()
            if server["status"] == "active"
            and self.current_connections[server_id] < server["capacity"]
        ]

        if not available_servers:
            return None

        # 가중치 기반 선택
        total_weight = sum(
            self.server_weights[server_id] for server_id in available_servers
        )
        if total_weight == 0:
            return available_servers[0]

        choice = random.uniform(0, total_weight)
        current_weight = 0

        for server_id in available_servers:
            current_weight += self.server_weights[server_id]
            if choice <= current_weight:
                return server_id

        return available_servers[-1]

    def update_connections(self, server_id: str, delta: int) -> None:
        """연결 수 업데이트"""
        self.current_connections[server_id] += delta
        self.current_connections[server_id] = max(
            0, self.current_connections[server_id]
        )


class AdvancedWebSocketServer:
    """고급 웹소켓 서버"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, ClientSubscription] = {}
        self.stream_processor = StreamProcessor()
        self.load_balancer = LoadBalancer()
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "start_time": datetime.now(),
        }

        # 스트림 생성기 등록
        self._register_stream_generators()
        self._register_data_processors()

    def _register_stream_generators(self) -> None:
        """스트림 생성기 등록"""
        asyncio.create_task(self._generate_sensor_data())
        asyncio.create_task(self._generate_system_metrics())
        asyncio.create_task(self._generate_user_activity())
        asyncio.create_task(self._generate_market_data())

    def _register_data_processors(self) -> None:
        """데이터 처리기 등록"""

        # 센서 데이터 이상치 탐지
        async def detect_anomalies(data: StreamData) -> StreamData:
            if data.stream_type == StreamType.SENSOR_DATA:
                value = data.data.get("value", 0)
                aggregated = self.stream_processor.get_aggregated_data(
                    StreamType.SENSOR_DATA
                )

                if aggregated and "mean" in aggregated and "std" in aggregated:
                    mean = aggregated["mean"]
                    std = aggregated["std"]

                    if std > 0 and abs(value - mean) > 3 * std:  # 3시그마 규칙
                        data.data["anomaly"] = True
                        data.data["anomaly_score"] = abs(value - mean) / std
                        logger.warning(
                            f"이상치 탐지: {value} (평균: {mean:.2f}, 표준편차: {std:.2f})"
                        )

            return data

        # 시스템 메트릭 임계값 체크
        async def check_thresholds(data: StreamData) -> StreamData:
            if data.stream_type == StreamType.SYSTEM_METRICS:
                cpu = data.data.get("cpu_usage", 0)
                memory = data.data.get("memory_usage", 0)

                if cpu > 80:
                    data.data["cpu_alert"] = True
                    logger.warning(f"높은 CPU 사용률: {cpu}%")

                if memory > 90:
                    data.data["memory_alert"] = True
                    logger.warning(f"높은 메모리 사용률: {memory}%")

            return data

        self.stream_processor.register_processor(
            StreamType.SENSOR_DATA, detect_anomalies
        )
        self.stream_processor.register_processor(
            StreamType.SYSTEM_METRICS, check_thresholds
        )

    async def _generate_sensor_data(self) -> None:
        """센서 데이터 생성"""
        while True:
            await asyncio.sleep(1)  # 1초마다

            data = StreamData(
                id=str(uuid.uuid4()),
                stream_type=StreamType.SENSOR_DATA,
                data={
                    "value": random.uniform(20, 30),  # 온도 센서
                    "unit": "celsius",
                    "location": random.choice(["room1", "room2", "room3"]),
                },
                timestamp=datetime.now(),
                source="temperature_sensor",
            )

            await self._broadcast_stream_data(data)

    async def _generate_system_metrics(self) -> None:
        """시스템 메트릭 생성"""
        while True:
            await asyncio.sleep(2)  # 2초마다

            data = StreamData(
                id=str(uuid.uuid4()),
                stream_type=StreamType.SYSTEM_METRICS,
                data={
                    "cpu_usage": random.uniform(10, 100),
                    "memory_usage": random.uniform(30, 95),
                    "disk_usage": random.uniform(20, 80),
                    "network_io": random.uniform(0, 1000),
                },
                timestamp=datetime.now(),
                source="system_monitor",
            )

            await self._broadcast_stream_data(data)

    async def _generate_user_activity(self) -> None:
        """사용자 활동 데이터 생성"""
        while True:
            await asyncio.sleep(5)  # 5초마다

            data = StreamData(
                id=str(uuid.uuid4()),
                stream_type=StreamType.USER_ACTIVITY,
                data={
                    "user_id": f"user_{random.randint(1, 100)}",
                    "action": random.choice(
                        ["login", "logout", "page_view", "click", "purchase"]
                    ),
                    "page": random.choice(["/home", "/products", "/cart", "/checkout"]),
                    "session_duration": random.uniform(0, 3600),
                },
                timestamp=datetime.now(),
                source="user_tracker",
            )

            await self._broadcast_stream_data(data)

    async def _generate_market_data(self) -> None:
        """시장 데이터 생성"""
        while True:
            await asyncio.sleep(0.5)  # 0.5초마다

            data = StreamData(
                id=str(uuid.uuid4()),
                stream_type=StreamType.MARKET_DATA,
                data={
                    "symbol": random.choice(["AAPL", "GOOGL", "MSFT", "TSLA"]),
                    "price": random.uniform(100, 500),
                    "volume": random.randint(1000, 10000),
                    "change": random.uniform(-5, 5),
                },
                timestamp=datetime.now(),
                source="market_feed",
            )

            await self._broadcast_stream_data(data)

    async def _broadcast_stream_data(self, data: StreamData) -> None:
        """스트림 데이터 브로드캐스트"""
        # 데이터 처리
        processed_data = await self.stream_processor.process_data(data)

        # 구독자들에게 전송
        for client_id, subscription in self.subscriptions.items():
            if data.stream_type in subscription.stream_types:
                if client_id in self.clients:
                    try:
                        message = json.dumps(processed_data.to_dict())
                        await self.clients[client_id].send(message)
                        self.metrics["messages_sent"] += 1
                    except ConnectionClosed:
                        await self._remove_client(client_id)
                    except Exception as e:
                        logger.error(f"메시지 전송 실패 (클라이언트: {client_id}): {e}")

    async def handle_client(
        self, websocket: WebSocketServerProtocol, path: str
    ) -> None:
        """클라이언트 연결 처리"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        self.metrics["total_connections"] += 1
        self.metrics["active_connections"] += 1

        logger.info(
            f"새 클라이언트 연결: {client_id} (총 연결: {self.metrics['active_connections']})"
        )

        try:
            async for message in websocket:
                await self._process_client_message(client_id, message)
        except ConnectionClosed:
            logger.info(f"클라이언트 연결 종료: {client_id}")
        except Exception as e:
            logger.error(f"클라이언트 처리 중 오류 (클라이언트: {client_id}): {e}")
        finally:
            await self._remove_client(client_id)

    async def _process_client_message(self, client_id: str, message: str) -> None:
        """클라이언트 메시지 처리"""
        self.metrics["messages_received"] += 1

        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")

            if message_type == "subscribe":
                # 스트림 구독
                stream_types = [StreamType(t) for t in data.get("stream_types", [])]
                filters = data.get("filters", {})

                self.subscriptions[client_id] = ClientSubscription(
                    client_id=client_id,
                    stream_types=set(stream_types),
                    filters=filters,
                    last_activity=datetime.now(),
                )

                await self._send_response(
                    client_id,
                    {
                        "type": "subscription_confirmed",
                        "stream_types": [t.value for t in stream_types],
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            elif message_type == "unsubscribe":
                # 구독 해제
                if client_id in self.subscriptions:
                    del self.subscriptions[client_id]

                await self._send_response(
                    client_id,
                    {
                        "type": "unsubscription_confirmed",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            elif message_type == "get_metrics":
                # 서버 메트릭 요청
                await self._send_response(
                    client_id,
                    {
                        "type": "server_metrics",
                        "metrics": self.metrics,
                        "uptime": (
                            datetime.now() - self.metrics["start_time"]
                        ).total_seconds(),
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            elif message_type == "get_aggregated_data":
                # 집계된 데이터 요청
                stream_type = StreamType(data.get("stream_type", "sensor_data"))
                window_size = data.get("window_size", 100)

                aggregated = self.stream_processor.get_aggregated_data(
                    stream_type, window_size
                )

                await self._send_response(
                    client_id,
                    {
                        "type": "aggregated_data",
                        "stream_type": stream_type.value,
                        "data": aggregated,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            elif message_type == "ping":
                # 핑 응답
                await self._send_response(
                    client_id, {"type": "pong", "timestamp": datetime.now().isoformat()}
                )

            else:
                # 알 수 없는 메시지 타입
                await self._send_response(
                    client_id,
                    {
                        "type": "error",
                        "message": f"알 수 없는 메시지 타입: {message_type}",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

        except json.JSONDecodeError:
            await self._send_response(
                client_id,
                {
                    "type": "error",
                    "message": "유효하지 않은 JSON 메시지",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}")
            await self._send_response(
                client_id,
                {
                    "type": "error",
                    "message": f"서버 오류: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _send_response(self, client_id: str, response: dict) -> None:
        """클라이언트에게 응답 전송"""
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(response))
                self.metrics["messages_sent"] += 1
            except ConnectionClosed:
                await self._remove_client(client_id)
            except Exception as e:
                logger.error(f"응답 전송 실패 (클라이언트: {client_id}): {e}")

    async def _remove_client(self, client_id: str) -> None:
        """클라이언트 제거"""
        if client_id in self.clients:
            del self.clients[client_id]
            self.metrics["active_connections"] -= 1

        if client_id in self.subscriptions:
            del self.subscriptions[client_id]

        logger.info(
            f"클라이언트 제거: {client_id} (활성 연결: {self.metrics['active_connections']})"
        )

    async def start_server(self) -> None:
        """서버 시작"""
        logger.info(f"고급 웹소켓 서버 시작: ws://{self.host}:{self.port}")

        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=10,
        ):
            logger.info("서버가 실행 중입니다. Ctrl+C로 종료하세요.")
            await asyncio.Future()


class AdvancedWebSocketClient:
    """고급 웹소켓 클라이언트"""

    def __init__(self, uri: str, client_name: str = "AdvancedClient"):
        self.uri = uri
        self.client_name = client_name
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.subscriptions: Set[StreamType] = set()

    async def connect(self) -> None:
        """서버에 연결"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.running = True
            logger.info(f"서버에 연결됨: {self.uri}")
        except Exception as e:
            logger.error(f"서버 연결 실패: {e}")
            raise

    async def disconnect(self) -> None:
        """서버 연결 해제"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("서버 연결 해제")

    async def subscribe(
        self, stream_types: List[StreamType], filters: Dict[str, Any] = None
    ) -> None:
        """스트림 구독"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = {
            "type": "subscribe",
            "stream_types": [t.value for t in stream_types],
            "filters": filters or {},
        }

        await self.websocket.send(json.dumps(message))
        self.subscriptions.update(stream_types)
        logger.info(f"구독 요청: {[t.value for t in stream_types]}")

    async def unsubscribe(self) -> None:
        """구독 해제"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = {"type": "unsubscribe"}
        await self.websocket.send(json.dumps(message))
        self.subscriptions.clear()
        logger.info("구독 해제")

    async def get_server_metrics(self) -> None:
        """서버 메트릭 요청"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = {"type": "get_metrics"}
        await self.websocket.send(json.dumps(message))

    async def get_aggregated_data(
        self, stream_type: StreamType, window_size: int = 100
    ) -> None:
        """집계된 데이터 요청"""
        if not self.websocket:
            raise RuntimeError("서버에 연결되지 않았습니다")

        message = {
            "type": "get_aggregated_data",
            "stream_type": stream_type.value,
            "window_size": window_size,
        }
        await self.websocket.send(json.dumps(message))

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
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.info(f"수신된 메시지: {message}")

        except ConnectionClosed:
            logger.info("서버 연결이 종료되었습니다")
        except Exception as e:
            logger.error(f"메시지 수신 중 오류: {e}")

    async def _handle_message(self, data: dict) -> None:
        """메시지 처리"""
        message_type = data.get("type", "unknown")

        if message_type == "subscription_confirmed":
            logger.info(f"구독 확인: {data.get('stream_types', [])}")

        elif message_type == "server_metrics":
            metrics = data.get("metrics", {})
            uptime = data.get("uptime", 0)
            print(f"\n=== 서버 메트릭 ===")
            print(f"활성 연결: {metrics.get('active_connections', 0)}")
            print(f"총 연결: {metrics.get('total_connections', 0)}")
            print(f"전송된 메시지: {metrics.get('messages_sent', 0)}")
            print(f"수신된 메시지: {metrics.get('messages_received', 0)}")
            print(f"업타임: {uptime:.2f}초")
            print("=" * 20)

        elif message_type == "aggregated_data":
            stream_type = data.get("stream_type", "unknown")
            aggregated_data = data.get("data", {})
            print(f"\n=== {stream_type} 집계 데이터 ===")
            for key, value in aggregated_data.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for sub_key, sub_value in value.items():
                        print(f"  {sub_key}: {sub_value}")
                else:
                    print(f"{key}: {value}")
            print("=" * 30)

        elif message_type in [
            "sensor_data",
            "system_metrics",
            "user_activity",
            "market_data",
        ]:
            # 스트림 데이터 출력
            timestamp = datetime.fromisoformat(data["timestamp"])
            source = data.get("source", "unknown")

            print(f"[{timestamp.strftime('%H:%M:%S')}] {message_type} from {source}")

            # 특별한 데이터 표시
            if "anomaly" in data.get("data", {}):
                print("🚨 이상치 탐지!")
            if "cpu_alert" in data.get("data", {}):
                print("⚠️ CPU 경고!")
            if "memory_alert" in data.get("data", {}):
                print("⚠️ 메모리 경고!")

        else:
            logger.info(f"수신된 메시지: {data}")


async def demo_advanced_server():
    """고급 서버 데모"""
    server = AdvancedWebSocketServer()
    await server.start_server()


async def demo_advanced_client():
    """고급 클라이언트 데모"""
    client = AdvancedWebSocketClient("ws://localhost:8765", "DemoClient")

    try:
        await client.connect()

        # 센서 데이터와 시스템 메트릭 구독
        await client.subscribe([StreamType.SENSOR_DATA, StreamType.SYSTEM_METRICS])

        # 서버 메트릭 요청
        await client.get_server_metrics()

        # 메시지 수신 시작
        await client.listen_for_messages()

    except KeyboardInterrupt:
        logger.info("클라이언트 종료")
    finally:
        await client.disconnect()


async def demo_data_analysis():
    """데이터 분석 데모"""
    client = AdvancedWebSocketClient("ws://localhost:8765", "AnalysisClient")

    try:
        await client.connect()

        # 모든 스트림 구독
        await client.subscribe(
            [
                StreamType.SENSOR_DATA,
                StreamType.SYSTEM_METRICS,
                StreamType.USER_ACTIVITY,
                StreamType.MARKET_DATA,
            ]
        )

        # 주기적으로 집계 데이터 요청
        async def periodic_analysis():
            while True:
                await asyncio.sleep(10)  # 10초마다
                print("\n=== 데이터 분석 ===")
                await client.get_aggregated_data(StreamType.SENSOR_DATA, 50)
                await client.get_aggregated_data(StreamType.SYSTEM_METRICS, 50)
                await client.get_server_metrics()

        # 분석 태스크와 메시지 수신을 동시에 실행
        analysis_task = asyncio.create_task(periodic_analysis())

        try:
            await client.listen_for_messages()
        finally:
            analysis_task.cancel()
            try:
                await analysis_task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        logger.info("분석 클라이언트 종료")
    finally:
        await client.disconnect()


async def main():
    """메인 함수"""
    print("고급 웹소켓 애플리케이션 데모")
    print("1. 서버 실행")
    print("2. 기본 클라이언트 실행")
    print("3. 데이터 분석 클라이언트 실행")
    print("4. 종료")

    choice = input("선택하세요 (1-4): ").strip()

    if choice == "1":
        print("고급 웹소켓 서버를 시작합니다...")
        await demo_advanced_server()
    elif choice == "2":
        print("기본 클라이언트를 시작합니다...")
        await demo_advanced_client()
    elif choice == "3":
        print("데이터 분석 클라이언트를 시작합니다...")
        await demo_data_analysis()
    else:
        print("프로그램을 종료합니다.")


if __name__ == "__main__":
    asyncio.run(main())
