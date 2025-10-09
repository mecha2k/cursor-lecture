"""
CancelledError 처리와 예외 전파 메커니즘 상세 분석
"""

import asyncio
import logging
import traceback
from typing import Optional, List
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CancelledErrorAnalyzer:
    """CancelledError 처리 메커니즘 분석"""

    def __init__(self):
        self.error_chain: List[str] = []
        self.cleanup_steps: List[str] = []

    async def demonstrate_error_propagation(self):
        """예외 전파 메커니즘 시연"""
        logger.info("=" * 80)
        logger.info("🚨 CancelledError 전파 메커니즘 상세 분석")
        logger.info("=" * 80)

        # 1. 기본 전파 시나리오
        await self.basic_propagation_scenario()

        # 2. 중첩된 태스크에서의 전파
        await self.nested_task_propagation()

        # 3. 예외 처리와 전파
        await self.exception_handling_propagation()

        # 4. 복잡한 시나리오
        await self.complex_propagation_scenario()

    async def basic_propagation_scenario(self):
        """기본 전파 시나리오"""
        logger.info("\n📋 시나리오 1: 기본 전파")
        logger.info("-" * 50)

        async def simple_task():
            try:
                logger.info("🔄 태스크 시작 - await 지점에서 대기")
                await asyncio.sleep(10)  # ← 여기서 CancelledError 발생
                logger.info("✅ 태스크 완료 (실행되지 않음)")
            except asyncio.CancelledError:
                logger.warning("⚠️  CancelledError 발생 - 전파 시작")
                logger.info("🧹 정리 작업 수행")
                await asyncio.sleep(0.2)  # 정리 작업
                logger.info("🚀 CancelledError 재발생")
                raise  # ← 이 부분이 핵심!
            except Exception as e:
                logger.error(f"❌ 예상치 못한 오류: {e}")
                raise

        # 태스크 생성 및 취소
        task = asyncio.create_task(simple_task())
        await asyncio.sleep(0.5)

        logger.info("🛑 cancel() 호출")
        task.cancel()

        try:
            result = await task
            logger.info(f"📊 결과: {result}")
        except asyncio.CancelledError:
            logger.info("✅ CancelledError 정상 처리됨")
        except Exception as e:
            logger.error(f"❌ 오류: {e}")

    async def nested_task_propagation(self):
        """중첩된 태스크에서의 전파"""
        logger.info("\n📋 시나리오 2: 중첩된 태스크 전파")
        logger.info("-" * 50)

        async def inner_task(task_id: str):
            try:
                logger.info(f"🔄 내부 태스크 {task_id} 시작")
                await asyncio.sleep(5)
                logger.info(f"✅ 내부 태스크 {task_id} 완료")
            except asyncio.CancelledError:
                logger.warning(f"⚠️  내부 태스크 {task_id} 취소됨")
                await asyncio.sleep(0.1)  # 정리 작업
                raise

        async def outer_task():
            try:
                logger.info("🔄 외부 태스크 시작")

                # 여러 내부 태스크 생성
                inner_tasks = [
                    asyncio.create_task(inner_task("A")),
                    asyncio.create_task(inner_task("B")),
                    asyncio.create_task(inner_task("C")),
                ]

                # 모든 내부 태스크 완료 대기
                await asyncio.gather(*inner_tasks)
                logger.info("✅ 외부 태스크 완료")

            except asyncio.CancelledError:
                logger.warning("⚠️  외부 태스크 취소됨")
                # 내부 태스크들도 취소
                for task in inner_tasks:
                    if not task.done():
                        task.cancel()
                raise

        # 외부 태스크 생성 및 취소
        outer_task_obj = asyncio.create_task(outer_task())
        await asyncio.sleep(0.5)

        logger.info("🛑 외부 태스크 취소")
        outer_task_obj.cancel()

        try:
            await outer_task_obj
        except asyncio.CancelledError:
            logger.info("✅ 외부 태스크 정상 취소됨")

    async def exception_handling_propagation(self):
        """예외 처리와 전파"""
        logger.info("\n📋 시나리오 3: 예외 처리와 전파")
        logger.info("-" * 50)

        async def task_with_exception_handling():
            try:
                logger.info("🔄 예외 처리 태스크 시작")
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.warning("⚠️  취소 신호 수신 - 정리 작업 시작")

                # 정리 작업 중 다른 예외 발생 가능
                try:
                    await self.simulate_cleanup_with_error()
                except Exception as cleanup_error:
                    logger.error(f"❌ 정리 작업 중 오류: {cleanup_error}")
                    # 정리 오류가 있어도 CancelledError는 재발생해야 함

                logger.info("🚀 CancelledError 재발생")
                raise  # ← 여전히 CancelledError 재발생

            except Exception as e:
                logger.error(f"❌ 일반 예외: {e}")
                raise

        task = asyncio.create_task(task_with_exception_handling())
        await asyncio.sleep(0.5)

        logger.info("🛑 태스크 취소")
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            logger.info("✅ CancelledError 정상 처리됨")

    async def simulate_cleanup_with_error(self):
        """정리 작업 중 오류 시뮬레이션"""
        logger.info("🧹 정리 작업 수행 중...")
        await asyncio.sleep(0.1)

        # 50% 확률로 오류 발생
        import random

        if random.random() < 0.5:
            raise Exception("정리 작업 중 예상치 못한 오류")

        logger.info("✅ 정리 작업 완료")

    async def complex_propagation_scenario(self):
        """복잡한 전파 시나리오"""
        logger.info("\n📋 시나리오 4: 복잡한 전파 시나리오")
        logger.info("-" * 50)

        async def complex_server_task():
            """복잡한 서버 태스크"""
            try:
                logger.info("🌐 복잡한 서버 태스크 시작")

                # 여러 하위 작업들
                subtasks = []
                for i in range(3):
                    subtask = asyncio.create_task(self.server_subtask(f"SubTask-{i}"))
                    subtasks.append(subtask)

                # 모든 하위 작업 완료 대기
                await asyncio.gather(*subtasks)
                logger.info("✅ 서버 태스크 완료")

            except asyncio.CancelledError:
                logger.warning("⚠️  서버 태스크 취소됨")
                await self.server_cleanup()
                raise

        async def server_subtask(name: str):
            """서버 하위 작업"""
            try:
                logger.info(f"🔄 {name} 시작")
                await asyncio.sleep(3)
                logger.info(f"✅ {name} 완료")
            except asyncio.CancelledError:
                logger.warning(f"⚠️  {name} 취소됨")
                await asyncio.sleep(0.1)  # 하위 작업 정리
                raise

        async def server_cleanup():
            """서버 정리 작업"""
            logger.info("🧹 서버 정리 작업 시작")

            # 1. 데이터베이스 연결 정리
            logger.info("🗄️  데이터베이스 연결 정리")
            await asyncio.sleep(0.2)

            # 2. 파일 시스템 정리
            logger.info("📁 파일 시스템 정리")
            await asyncio.sleep(0.2)

            # 3. 네트워크 연결 정리
            logger.info("🌐 네트워크 연결 정리")
            await asyncio.sleep(0.2)

            logger.info("✅ 서버 정리 완료")

        # 복잡한 서버 태스크 실행
        server_task = asyncio.create_task(complex_server_task())
        await asyncio.sleep(1)

        logger.info("🛑 복잡한 서버 태스크 취소")
        server_task.cancel()

        try:
            await server_task
        except asyncio.CancelledError:
            logger.info("✅ 복잡한 서버 태스크 정상 취소됨")


class ErrorChainAnalyzer:
    """에러 체인 분석"""

    def __init__(self):
        self.error_chain: List[str] = []

    async def analyze_error_chain(self):
        """에러 체인 분석"""
        logger.info("\n" + "=" * 80)
        logger.info("🔗 CancelledError 체인 분석")
        logger.info("=" * 80)

        # 1. 단순 체인
        await self.simple_error_chain()

        # 2. 복잡한 체인
        await self.complex_error_chain()

        # 3. 체인 중단 시나리오
        await self.broken_chain_scenario()

    async def simple_error_chain(self):
        """단순 에러 체인"""
        logger.info("\n📋 단순 에러 체인")
        logger.info("-" * 30)

        async def level3():
            try:
                logger.info("🔄 Level 3 시작")
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                logger.warning("⚠️  Level 3에서 CancelledError 발생")
                raise  # Level 2로 전파

        async def level2():
            try:
                logger.info("🔄 Level 2 시작")
                await level3()
            except asyncio.CancelledError:
                logger.warning("⚠️  Level 2에서 CancelledError 수신")
                raise  # Level 1로 전파

        async def level1():
            try:
                logger.info("🔄 Level 1 시작")
                await level2()
            except asyncio.CancelledError:
                logger.warning("⚠️  Level 1에서 CancelledError 수신")
                raise  # 메인으로 전파

        # 체인 실행
        task = asyncio.create_task(level1())
        await asyncio.sleep(0.5)

        logger.info("🛑 체인 취소")
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            logger.info("✅ 체인 정상 취소됨")

    async def complex_error_chain(self):
        """복잡한 에러 체인"""
        logger.info("\n📋 복잡한 에러 체인")
        logger.info("-" * 30)

        async def worker_task(worker_id: int):
            try:
                logger.info(f"👷 Worker {worker_id} 시작")
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                logger.warning(f"⚠️  Worker {worker_id} 취소됨")
                await asyncio.sleep(0.1)  # 정리 작업
                raise

        async def manager_task():
            try:
                logger.info("👔 Manager 시작")

                # 여러 워커 생성
                workers = []
                for i in range(3):
                    worker = asyncio.create_task(worker_task(i))
                    workers.append(worker)

                # 모든 워커 완료 대기
                await asyncio.gather(*workers)
                logger.info("✅ Manager 완료")

            except asyncio.CancelledError:
                logger.warning("⚠️  Manager 취소됨")

                # 모든 워커 취소
                for worker in workers:
                    if not worker.done():
                        worker.cancel()

                # 워커 취소 완료 대기
                for worker in workers:
                    try:
                        await worker
                    except asyncio.CancelledError:
                        pass

                raise

        # 매니저 태스크 실행
        manager = asyncio.create_task(manager_task())
        await asyncio.sleep(0.5)

        logger.info("🛑 매니저 취소")
        manager.cancel()

        try:
            await manager
        except asyncio.CancelledError:
            logger.info("✅ 매니저 정상 취소됨")

    async def broken_chain_scenario(self):
        """체인 중단 시나리오"""
        logger.info("\n📋 체인 중단 시나리오")
        logger.info("-" * 30)

        async def problematic_task():
            try:
                logger.info("🔄 문제가 있는 태스크 시작")
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                logger.warning("⚠️  취소 신호 수신")

                # 문제: CancelledError를 재발생하지 않음!
                logger.error("❌ CancelledError를 재발생하지 않음!")
                # raise  # ← 이 줄이 주석처리됨!

                logger.info("✅ 태스크 완료 (잘못된 처리)")

        # 문제가 있는 태스크 실행
        task = asyncio.create_task(problematic_task())
        await asyncio.sleep(0.5)

        logger.info("🛑 태스크 취소")
        task.cancel()

        try:
            result = await task
            logger.info(f"📊 결과: {result}")
            logger.warning("⚠️  CancelledError가 전파되지 않음!")
        except asyncio.CancelledError:
            logger.info("✅ CancelledError 정상 처리됨")


async def demonstrate_best_practices():
    """최적의 실무 패턴 시연"""
    logger.info("\n" + "=" * 80)
    logger.info("💡 CancelledError 처리 최적 실무 패턴")
    logger.info("=" * 80)

    class ProductionWebSocketServer:
        """실무용 웹소켓 서버"""

        def __init__(self):
            self.clients = set()
            self.server_task = None
            self.is_running = False

        async def handle_client(self, websocket, path):
            """클라이언트 처리 (실무 패턴)"""
            self.clients.add(websocket)
            logger.info(f"📱 클라이언트 연결: {len(self.clients)}개")

            try:
                async for message in websocket:
                    await self.process_message(websocket, message)
            except asyncio.CancelledError:
                logger.info("📱 클라이언트 연결 취소됨")
                raise  # 정상적인 취소 전파
            except Exception as e:
                logger.error(f"📱 클라이언트 오류: {e}")
            finally:
                self.clients.discard(websocket)
                logger.info(f"📱 클라이언트 연결 해제: {len(self.clients)}개")

        async def process_message(self, websocket, message):
            """메시지 처리"""
            logger.info(f"📨 메시지 처리: {message}")
            await asyncio.sleep(0.1)  # 처리 시간

        async def start_server(self):
            """서버 시작 (실무 패턴)"""
            logger.info("🚀 서버 시작")
            self.is_running = True

            try:
                # 실제로는 websockets.serve() 사용
                await asyncio.sleep(10)  # 서버 실행 시뮬레이션
            except asyncio.CancelledError:
                logger.warning("⚠️  서버 취소 신호 수신")
                await self.graceful_shutdown()
                raise  # ← 핵심: CancelledError 재발생
            except Exception as e:
                logger.error(f"❌ 서버 오류: {e}")
                await self.emergency_shutdown()
                raise
            finally:
                self.is_running = False
                logger.info("🏁 서버 완전 종료")

        async def graceful_shutdown(self):
            """우아한 종료 (실무 패턴)"""
            logger.info("🛑 우아한 종료 시작")

            # 1. 새 연결 차단
            logger.info("🚫 새 연결 차단")

            # 2. 기존 클라이언트에게 종료 알림
            if self.clients:
                logger.info(f"📢 {len(self.clients)}개 클라이언트에게 종료 알림")
                for client in list(self.clients):
                    try:
                        await client.send('{"type": "server_shutdown"}')
                    except:
                        pass

            # 3. 클라이언트 연결 종료
            if self.clients:
                logger.info("📱 클라이언트 연결 종료")
                for client in list(self.clients):
                    try:
                        await client.close()
                    except:
                        pass
                self.clients.clear()

            # 4. 리소스 정리
            await self.cleanup_resources()

            logger.info("✅ 우아한 종료 완료")

        async def emergency_shutdown(self):
            """비상 종료"""
            logger.info("🚨 비상 종료")
            # 최소한의 정리 작업만 수행
            self.clients.clear()

        async def cleanup_resources(self):
            """리소스 정리"""
            logger.info("🧹 리소스 정리")
            await asyncio.sleep(0.3)  # 정리 작업 시뮬레이션

    # 실무 패턴 시연
    server = ProductionWebSocketServer()
    server.server_task = asyncio.create_task(server.start_server())

    try:
        # 서버 실행
        await asyncio.sleep(1)

        # 안전한 종료
        logger.info("🛑 서버 안전 종료")
        server.server_task.cancel()

        try:
            await server.server_task
        except asyncio.CancelledError:
            logger.info("✅ 서버 정상 종료됨")

    except Exception as e:
        logger.error(f"❌ 오류: {e}")


async def main():
    """메인 함수"""
    logger.info("🔬 CancelledError 처리 완전 분석")
    logger.info("=" * 80)

    # 1. 예외 전파 메커니즘
    analyzer = CancelledErrorAnalyzer()
    await analyzer.demonstrate_error_propagation()

    # 2. 에러 체인 분석
    chain_analyzer = ErrorChainAnalyzer()
    await chain_analyzer.analyze_error_chain()

    # 3. 최적 실무 패턴
    await demonstrate_best_practices()

    logger.info("=" * 80)
    logger.info("🎯 CancelledError 분석 완료!")


if __name__ == "__main__":
    asyncio.run(main())

