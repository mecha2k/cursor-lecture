"""
server_task.cancel() 대안 방법들과의 상세 비교
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, List
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServerTerminationComparison:
    """서버 종료 방법들 비교 분석"""

    def __init__(self):
        self.server_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.cleanup_completed = False

    async def mock_server_operation(self, server_id: str = "default"):
        """서버 작업 시뮬레이션"""
        logger.info(f"🌐 서버 {server_id} 시작")
        self.is_running = True

        try:
            counter = 0
            while True:
                logger.info(f"🔄 서버 {server_id} 작업 중... (카운터: {counter})")
                await asyncio.sleep(1)
                counter += 1

        except asyncio.CancelledError:
            logger.warning(f"⚠️  서버 {server_id} 취소 신호 수신")
            await self.cleanup_resources(server_id)
            raise
        except Exception as e:
            logger.error(f"❌ 서버 {server_id} 오류: {e}")
            raise
        finally:
            self.is_running = False
            logger.info(f"🏁 서버 {server_id} 완전 종료")

    async def cleanup_resources(self, server_id: str):
        """리소스 정리"""
        logger.info(f"🧹 서버 {server_id} 리소스 정리 중...")
        await asyncio.sleep(0.5)  # 정리 작업 시뮬레이션
        self.cleanup_completed = True
        logger.info(f"✅ 서버 {server_id} 리소스 정리 완료")


class Method1_CancelAwait:
    """방법 1: cancel() + await (권장 방법)"""

    async def demonstrate(self):
        logger.info("=" * 60)
        logger.info("🟢 방법 1: cancel() + await (권장)")
        logger.info("=" * 60)

        server = ServerTerminationComparison()
        server_task = asyncio.create_task(server.mock_server_operation("Method1"))

        try:
            # 서버 실행
            await asyncio.sleep(1)

            # 안전한 종료
            logger.info("🛑 cancel() 호출")
            server_task.cancel()

            logger.info("⏳ await로 취소 완료 대기")
            try:
                await server_task
            except asyncio.CancelledError:
                logger.info("✅ 정상적으로 취소됨")

            logger.info(f"📊 정리 완료: {server.cleanup_completed}")

        except Exception as e:
            logger.error(f"❌ 오류: {e}")


class Method2_ForceTerminate:
    """방법 2: 강제 종료 (비권장)"""

    async def demonstrate(self):
        logger.info("=" * 60)
        logger.info("🔴 방법 2: 강제 종료 (비권장)")
        logger.info("=" * 60)

        server = ServerTerminationComparison()
        server_task = asyncio.create_task(server.mock_server_operation("Method2"))

        try:
            # 서버 실행
            await asyncio.sleep(1)

            # 강제 종료 (정리 작업 없음)
            logger.info("💥 강제 종료 - 정리 작업 없음")
            # server_task는 그대로 두고 프로그램 종료

            logger.info(f"📊 정리 완료: {server.cleanup_completed}")  # False

        except Exception as e:
            logger.error(f"❌ 오류: {e}")


class Method3_TimeoutCancel:
    """방법 3: 타임아웃과 함께 취소"""

    async def demonstrate(self):
        logger.info("=" * 60)
        logger.info("🟡 방법 3: 타임아웃과 함께 취소")
        logger.info("=" * 60)

        server = ServerTerminationComparison()
        server_task = asyncio.create_task(server.mock_server_operation("Method3"))

        try:
            # 서버 실행
            await asyncio.sleep(1)

            # 타임아웃과 함께 취소
            logger.info("🛑 cancel() 호출")
            server_task.cancel()

            logger.info("⏳ 3초 타임아웃으로 취소 대기")
            try:
                await asyncio.wait_for(server_task, timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️  타임아웃 - 강제 종료")
            except asyncio.CancelledError:
                logger.info("✅ 정상적으로 취소됨")

            logger.info(f"📊 정리 완료: {server.cleanup_completed}")

        except Exception as e:
            logger.error(f"❌ 오류: {e}")


class Method4_SignalHandler:
    """방법 4: 시그널 핸들러와 함께"""

    def __init__(self):
        self.server_task: Optional[asyncio.Task] = None
        self.server = ServerTerminationComparison()

    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"📡 시그널 {signum} 수신 - 서버 종료 시작")
        if self.server_task:
            self.server_task.cancel()

    async def demonstrate(self):
        logger.info("=" * 60)
        logger.info("🟣 방법 4: 시그널 핸들러와 함께")
        logger.info("=" * 60)

        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            self.server_task = asyncio.create_task(
                self.server.mock_server_operation("Method4")
            )

            # 서버 실행
            await asyncio.sleep(1)

            # 시뮬레이션: Ctrl+C 시그널 전송
            logger.info("📡 SIGINT 시그널 시뮬레이션")
            self.signal_handler(signal.SIGINT, None)

            # 취소 완료 대기
            try:
                await self.server_task
            except asyncio.CancelledError:
                logger.info("✅ 시그널에 의한 정상 취소")

            logger.info(f"📊 정리 완료: {self.server.cleanup_completed}")

        except Exception as e:
            logger.error(f"❌ 오류: {e}")


class Method5_ExceptionBased:
    """방법 5: 예외 기반 종료"""

    class ServerShutdownException(Exception):
        """서버 종료 예외"""

        pass

    async def demonstrate(self):
        logger.info("=" * 60)
        logger.info("🟠 방법 5: 예외 기반 종료")
        logger.info("=" * 60)

        server = ServerTerminationComparison()

        async def server_with_exception_handling():
            try:
                await server.mock_server_operation("Method5")
            except self.ServerShutdownException:
                logger.info("🛑 서버 종료 예외 수신")
                await server.cleanup_resources("Method5")
                raise

        server_task = asyncio.create_task(server_with_exception_handling())

        try:
            # 서버 실행
            await asyncio.sleep(1)

            # 예외로 종료
            logger.info("💥 서버 종료 예외 발생")
            server_task.cancel()  # 실제로는 예외를 발생시켜야 함

            try:
                await server_task
            except asyncio.CancelledError:
                logger.info("✅ 예외에 의한 정상 종료")

            logger.info(f"📊 정리 완료: {server.cleanup_completed}")

        except Exception as e:
            logger.error(f"❌ 오류: {e}")


async def compare_all_methods():
    """모든 방법 비교"""
    logger.info("🔬 서버 종료 방법들 상세 비교")
    logger.info("=" * 80)

    methods = [
        ("방법 1: cancel() + await", Method1_CancelAwait()),
        ("방법 2: 강제 종료", Method2_ForceTerminate()),
        ("방법 3: 타임아웃 취소", Method3_TimeoutCancel()),
        ("방법 4: 시그널 핸들러", Method4_SignalHandler()),
        ("방법 5: 예외 기반", Method5_ExceptionBased()),
    ]

    for name, method in methods:
        logger.info(f"\n📋 {name} 테스트")
        try:
            await method.demonstrate()
        except Exception as e:
            logger.error(f"❌ {name} 실패: {e}")

        await asyncio.sleep(0.5)  # 방법 간 구분

    logger.info("\n" + "=" * 80)
    logger.info("📊 비교 결과 요약:")
    logger.info("✅ 방법 1 (cancel + await): 가장 안전하고 권장")
    logger.info("❌ 방법 2 (강제 종료): 리소스 누수 위험")
    logger.info("⚠️  방법 3 (타임아웃): 상황에 따라 유용")
    logger.info("🔄 방법 4 (시그널): 외부 신호 처리에 유용")
    logger.info("🎯 방법 5 (예외): 특수한 경우에만 사용")


async def demonstrate_real_world_scenario():
    """실제 웹소켓 서버 시나리오"""
    logger.info("=" * 80)
    logger.info("🌐 실제 웹소켓 서버 종료 시나리오")
    logger.info("=" * 80)

    class RealWebSocketServer:
        def __init__(self):
            self.clients = set()
            self.server_task = None
            self.is_running = False

        async def handle_client(self, websocket, path):
            """클라이언트 처리"""
            self.clients.add(websocket)
            logger.info(f"📱 새 클라이언트 연결: {len(self.clients)}개")

            try:
                async for message in websocket:
                    logger.info(f"📨 메시지 수신: {message}")
            except Exception as e:
                logger.info(f"📱 클라이언트 연결 종료: {e}")
            finally:
                self.clients.discard(websocket)
                logger.info(f"📱 클라이언트 연결 해제: {len(self.clients)}개")

        async def start_server(self):
            """서버 시작"""
            logger.info("🚀 웹소켓 서버 시작")
            self.is_running = True

            try:
                # 실제로는 websockets.serve()를 사용
                await asyncio.sleep(5)  # 서버 실행 시뮬레이션
            except asyncio.CancelledError:
                logger.warning("⚠️  서버 취소 신호 수신")
                await self.cleanup_server()
                raise

        async def cleanup_server(self):
            """서버 정리"""
            logger.info("🧹 서버 정리 시작")

            # 1. 모든 클라이언트 연결 종료
            if self.clients:
                logger.info(f"📱 {len(self.clients)}개 클라이언트 연결 종료")
                for client in list(self.clients):
                    try:
                        await client.close()
                    except:
                        pass
                self.clients.clear()

            # 2. 데이터베이스 연결 정리
            logger.info("🗄️  데이터베이스 연결 정리")
            await asyncio.sleep(0.2)

            # 3. 로그 파일 정리
            logger.info("📝 로그 파일 정리")
            await asyncio.sleep(0.2)

            logger.info("✅ 서버 정리 완료")

    # 실제 시나리오 시뮬레이션
    server = RealWebSocketServer()
    server.server_task = asyncio.create_task(server.start_server())

    try:
        # 서버 실행
        await asyncio.sleep(2)

        # 안전한 종료
        logger.info("🛑 서버 안전 종료 시작")
        server.server_task.cancel()

        try:
            await server.server_task
        except asyncio.CancelledError:
            logger.info("✅ 서버가 안전하게 종료됨")

    except Exception as e:
        logger.error(f"❌ 오류: {e}")


async def main():
    """메인 함수"""
    logger.info("🔬 server_task.cancel() 완전 분석")
    logger.info("=" * 80)

    # 1. 모든 방법 비교
    await compare_all_methods()

    # 2. 실제 시나리오
    await demonstrate_real_world_scenario()

    logger.info("=" * 80)
    logger.info("🎯 분석 완료!")


if __name__ == "__main__":
    asyncio.run(main())

