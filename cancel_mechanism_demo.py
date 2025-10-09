"""
server_task.cancel() 메커니즘 상세 분석 및 데모
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DetailedTaskManager:
    """Task 취소 메커니즘을 상세히 분석하는 클래스"""

    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.cancelled_tasks: list[asyncio.Task] = []

    async def long_running_task(self, task_id: int, duration: int = 10) -> str:
        """
        장시간 실행되는 태스크 (취소 메커니즘 분석용)

        Args:
            task_id: 태스크 식별자
            duration: 실행 시간 (초)

        Returns:
            완료 메시지
        """
        logger.info(f"🚀 Task {task_id} 시작 (예상 실행시간: {duration}초)")

        try:
            # 1. 일반적인 작업 시뮬레이션
            for i in range(duration):
                logger.info(f"📊 Task {task_id} 진행률: {i+1}/{duration}")
                await asyncio.sleep(1)  # ← 여기서 CancelledError 발생 가능

            logger.info(f"✅ Task {task_id} 정상 완료")
            return f"Task {task_id} completed successfully"

        except asyncio.CancelledError:
            # 2. 취소 신호를 받았을 때의 처리
            logger.warning(f"⚠️  Task {task_id} 취소 요청 받음 - 정리 작업 시작")

            # 정리 작업 시뮬레이션
            await asyncio.sleep(0.5)  # 리소스 정리 시간
            logger.info(f"🧹 Task {task_id} 정리 작업 완료")

            # CancelledError를 다시 발생시켜야 함 (중요!)
            raise  # 이 부분이 핵심!

        except Exception as e:
            logger.error(f"❌ Task {task_id} 예상치 못한 오류: {e}")
            raise

    async def demonstrate_cancel_mechanism(self):
        """취소 메커니즘 시연"""
        logger.info("=" * 60)
        logger.info("🔬 Task 취소 메커니즘 상세 분석 시작")
        logger.info("=" * 60)

        # 1. 여러 태스크 생성
        tasks = []
        for i in range(3):
            task = asyncio.create_task(self.long_running_task(i + 1, 5))
            tasks.append(task)
            self.tasks.append(task)

        logger.info(f"📋 생성된 태스크 수: {len(tasks)}")

        # 2. 잠시 실행 후 취소
        await asyncio.sleep(2)
        logger.info("🛑 2초 후 모든 태스크 취소 요청")

        # 3. 모든 태스크 취소
        for i, task in enumerate(tasks):
            logger.info(f"🚫 Task {i+1} 취소 요청 전송")
            task.cancel()  # ← 여기서 CancelledError 전송

        # 4. 취소 완료 대기
        logger.info("⏳ 모든 태스크 취소 완료 대기 중...")

        for i, task in enumerate(tasks):
            try:
                result = await task
                logger.info(f"✅ Task {i+1} 결과: {result}")
            except asyncio.CancelledError:
                logger.info(f"✅ Task {i+1} 정상적으로 취소됨")
                self.cancelled_tasks.append(task)
            except Exception as e:
                logger.error(f"❌ Task {i+1} 오류: {e}")

        logger.info(f"📊 취소된 태스크 수: {len(self.cancelled_tasks)}")
        logger.info("=" * 60)


class WebSocketServerAnalyzer:
    """웹소켓 서버의 취소 메커니즘 분석"""

    def __init__(self):
        self.server_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def mock_server_operation(self):
        """서버 작업 시뮬레이션"""
        logger.info("🌐 웹소켓 서버 시뮬레이션 시작")
        self.is_running = True

        try:
            # 서버가 계속 실행되는 상태 시뮬레이션
            while True:
                logger.info("🔄 서버가 클라이언트 연결을 대기 중...")
                await asyncio.sleep(1)  # ← 여기서 CancelledError 발생

        except asyncio.CancelledError:
            logger.warning("⚠️  서버 취소 신호 수신 - 정리 작업 시작")

            # 서버 정리 작업
            await self.cleanup_server_resources()

            logger.info("✅ 서버 정리 완료 - CancelledError 재발생")
            raise  # CancelledError 재발생 (중요!)

        except Exception as e:
            logger.error(f"❌ 서버 오류: {e}")
            raise
        finally:
            self.is_running = False
            logger.info("🏁 서버 완전 종료")

    async def cleanup_server_resources(self):
        """서버 리소스 정리"""
        logger.info("🧹 서버 리소스 정리 중...")

        # 1. 활성 연결 종료
        logger.info("📡 활성 웹소켓 연결 종료")
        await asyncio.sleep(0.2)

        # 2. 데이터베이스 연결 정리
        logger.info("🗄️  데이터베이스 연결 정리")
        await asyncio.sleep(0.2)

        # 3. 로그 파일 정리
        logger.info("📝 로그 파일 정리")
        await asyncio.sleep(0.2)

        logger.info("✅ 서버 리소스 정리 완료")

    async def start_server(self):
        """서버 시작"""
        logger.info("🚀 서버 시작 요청")
        self.server_task = asyncio.create_task(self.mock_server_operation())
        return self.server_task

    async def stop_server(self):
        """서버 안전 종료"""
        if not self.server_task:
            logger.warning("⚠️  서버가 실행 중이 아닙니다")
            return

        logger.info("🛑 서버 종료 요청")
        self.server_task.cancel()  # ← 취소 요청 전송

        try:
            await self.server_task  # ← 취소 완료 대기
            logger.info("✅ 서버 정상 종료")
        except asyncio.CancelledError:
            logger.info("✅ 서버가 정상적으로 취소됨")
        except Exception as e:
            logger.error(f"❌ 서버 종료 중 오류: {e}")
        finally:
            self.server_task = None


async def demonstrate_websocket_cancel():
    """웹소켓 서버 취소 시연"""
    logger.info("=" * 60)
    logger.info("🌐 웹소켓 서버 취소 메커니즘 시연")
    logger.info("=" * 60)

    server_analyzer = WebSocketServerAnalyzer()

    try:
        # 1. 서버 시작
        await server_analyzer.start_server()
        logger.info("⏳ 서버 실행 중... (3초 후 종료)")

        # 2. 서버 실행 대기
        await asyncio.sleep(3)

        # 3. 서버 안전 종료
        await server_analyzer.stop_server()

    except Exception as e:
        logger.error(f"❌ 시연 중 오류: {e}")


async def demonstrate_cancel_timing():
    """취소 타이밍 분석"""
    logger.info("=" * 60)
    logger.info("⏰ 취소 타이밍 분석")
    logger.info("=" * 60)

    async def timed_task(task_id: int, sleep_time: float):
        """시간 측정이 가능한 태스크"""
        start_time = datetime.now()
        logger.info(
            f"🚀 Task {task_id} 시작: {start_time.strftime('%H:%M:%S.%f')[:-3]}"
        )

        try:
            await asyncio.sleep(sleep_time)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ Task {task_id} 완료: {duration:.3f}초")
            return f"Task {task_id} completed in {duration:.3f}s"

        except asyncio.CancelledError:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"⚠️  Task {task_id} 취소됨: {duration:.3f}초 후")
            raise

    # 여러 태스크를 다른 시점에 취소
    tasks = []

    # 즉시 취소
    task1 = asyncio.create_task(timed_task(1, 5.0))
    tasks.append(task1)

    # 1초 후 취소
    task2 = asyncio.create_task(timed_task(2, 5.0))
    tasks.append(task2)

    # 2초 후 취소
    task3 = asyncio.create_task(timed_task(3, 5.0))
    tasks.append(task3)

    # 취소 실행
    await asyncio.sleep(0.1)
    logger.info("🚫 Task 1 즉시 취소")
    task1.cancel()

    await asyncio.sleep(1.0)
    logger.info("🚫 Task 2 1초 후 취소")
    task2.cancel()

    await asyncio.sleep(1.0)
    logger.info("🚫 Task 3 2초 후 취소")
    task3.cancel()

    # 결과 수집
    for i, task in enumerate(tasks, 1):
        try:
            result = await task
            logger.info(f"📊 Task {i} 결과: {result}")
        except asyncio.CancelledError:
            logger.info(f"📊 Task {i} 취소됨")


async def main():
    """메인 함수"""
    logger.info("🔬 Asyncio Task 취소 메커니즘 상세 분석")
    logger.info("=" * 80)

    # 1. 기본 취소 메커니즘 시연
    await DetailedTaskManager().demonstrate_cancel_mechanism()

    # 2. 웹소켓 서버 취소 시연
    await demonstrate_websocket_cancel()

    # 3. 취소 타이밍 분석
    await demonstrate_cancel_timing()

    logger.info("=" * 80)
    logger.info("🎯 분석 완료 - server_task.cancel()의 모든 측면을 확인했습니다!")


if __name__ == "__main__":
    asyncio.run(main())

