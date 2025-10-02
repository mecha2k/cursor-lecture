"""
asyncio 기초 예제
비동기 프로그래밍의 기본 개념을 학습합니다.
"""

import asyncio
import time
from typing import List


async def simple_task(name: str, delay: float) -> str:
    """
    간단한 비동기 작업을 수행합니다.

    Args:
        name: 작업 이름
        delay: 대기 시간 (초)

    Returns:
        완료 메시지
    """
    print(f"작업 {name} 시작")
    await asyncio.sleep(delay)  # 비동기 대기
    print(f"작업 {name} 완료")
    return f"{name} 작업이 {delay}초 후 완료되었습니다"


async def fetch_data(url: str, delay: float) -> dict:
    """
    가상의 데이터 페칭 작업을 시뮬레이션합니다.

    Args:
        url: 가상의 URL
        delay: 네트워크 지연 시뮬레이션

    Returns:
        가상의 데이터
    """
    print(f"데이터 요청: {url}")
    await asyncio.sleep(delay)
    return {
        "url": url,
        "data": f"URL {url}에서 가져온 데이터",
        "timestamp": time.time(),
    }


def sync_task(name: str, delay: float) -> str:
    """
    동기 버전의 작업 함수 (비교용)

    Args:
        name: 작업 이름
        delay: 대기 시간 (초)

    Returns:
        완료 메시지
    """
    print(f"동기 작업 {name} 시작")
    time.sleep(delay)  # 동기 대기 (블로킹)
    print(f"동기 작업 {name} 완료")
    return f"{name} 작업이 {delay}초 후 완료되었습니다"


async def demo_sleep_difference():
    """time.sleep vs asyncio.sleep 차이점 데모"""
    print("=== time.sleep vs asyncio.sleep 차이점 ===")

    async def async_task_with_sync_sleep(name: str, delay: float) -> str:
        """비동기 함수에서 time.sleep 사용 (잘못된 방법)"""
        print(f"작업 {name} 시작 (time.sleep 사용)")
        time.sleep(delay)  # ❌ 이렇게 하면 안됨!
        print(f"작업 {name} 완료")
        return f"{name} 완료"

    async def async_task_with_async_sleep(name: str, delay: float) -> str:
        """비동기 함수에서 asyncio.sleep 사용 (올바른 방법)"""
        print(f"작업 {name} 시작 (asyncio.sleep 사용)")
        await asyncio.sleep(delay)  # ✅ 올바른 방법
        print(f"작업 {name} 완료")
        return f"{name} 완료"

    # 1. time.sleep을 사용한 잘못된 비동기 코드
    print("\n--- time.sleep 사용 (잘못된 방법) ---")
    start_time = time.time()
    results1 = await asyncio.gather(
        async_task_with_sync_sleep("A", 1.0),
        async_task_with_sync_sleep("B", 1.0),
        async_task_with_sync_sleep("C", 1.0),
    )
    end_time = time.time()
    print(f"time.sleep 사용 시간: {end_time - start_time:.2f}초")
    print("❌ time.sleep은 블로킹이므로 동시 실행이 안됨!")

    # 2. asyncio.sleep을 사용한 올바른 비동기 코드
    print("\n--- asyncio.sleep 사용 (올바른 방법) ---")
    start_time = time.time()
    results2 = await asyncio.gather(
        async_task_with_async_sleep("D", 1.0),
        async_task_with_async_sleep("E", 1.0),
        async_task_with_async_sleep("F", 1.0),
    )
    end_time = time.time()
    print(f"asyncio.sleep 사용 시간: {end_time - start_time:.2f}초")
    print("✅ asyncio.sleep은 논블로킹이므로 동시 실행됨!")


async def main_basic():
    """기본적인 asyncio 사용법"""
    print("=== asyncio 기본 예제 ===")

    # 1. 단일 코루틴 실행
    result = await simple_task("A", 1.0)
    print(f"결과: {result}")

    # 2. sleep 차이점 데모
    await demo_sleep_difference()

    # 3. 동기 함수로 순차 실행 (느림)
    print("\n--- 동기 함수 순차 실행 ---")
    start_time = time.time()
    result1 = sync_task("B", 1.0)
    result2 = sync_task("C", 1.0)
    end_time = time.time()
    print(f"동기 순차 실행 시간: {end_time - start_time:.2f}초")

    # 4. 비동기 함수로 순차 실행 (여전히 느림)
    print("\n--- 비동기 함수 순차 실행 ---")
    start_time = time.time()
    result1 = await simple_task("D", 1.0)
    result2 = await simple_task("E", 1.0)
    end_time = time.time()
    print(f"비동기 순차 실행 시간: {end_time - start_time:.2f}초")
    print("💡 순차 실행은 동기/비동기 차이가 없습니다!")


async def main_concurrent():
    """동시 실행 예제"""
    print("\n=== 동시 실행 예제 ===")

    # 1. 동기 함수로 순차 실행 (느림)
    print("--- 동기 함수 순차 실행 ---")
    start_time = time.time()
    result1 = sync_task("G", 1.0)
    result2 = sync_task("H", 1.0)
    result3 = sync_task("I", 1.0)
    end_time = time.time()
    sync_time = end_time - start_time
    print(f"동기 순차 실행 시간: {sync_time:.2f}초")

    # 2. 비동기 함수로 동시 실행 (빠름)
    print("\n--- 비동기 함수 동시 실행 ---")
    start_time = time.time()
    results = await asyncio.gather(
        simple_task("J", 1.0), simple_task("K", 1.0), simple_task("L", 1.0)
    )
    end_time = time.time()
    async_time = end_time - start_time
    print(f"비동기 동시 실행 시간: {async_time:.2f}초")
    print(f"결과들: {results}")

    # 3. 성능 비교
    speedup = sync_time / async_time if async_time > 0 else 0
    print(f"\n🚀 비동기 동시 실행이 {speedup:.1f}배 빠릅니다!")
    print(f"   시간 절약: {sync_time - async_time:.2f}초")


async def main_data_fetching():
    """데이터 페칭 시뮬레이션"""
    print("\n=== 데이터 페칭 시뮬레이션 ===")

    urls = [
        "https://api.example.com/users",
        "https://api.example.com/posts",
        "https://api.example.com/comments",
    ]

    # 동시에 여러 API 호출
    start_time = time.time()
    tasks = [fetch_data(url, 1.0) for url in urls]
    results = await asyncio.gather(*tasks)
    end_time = time.time()

    print(f"모든 데이터 페칭 완료: {end_time - start_time:.2f}초")
    for result in results:
        print(f"  - {result['url']}: {result['data']}")


async def main_with_tasks():
    """Task 객체를 사용한 예제"""
    print("\n=== Task 객체 사용 예제 ===")

    # Task 생성
    task1 = asyncio.create_task(simple_task("Task1", 2.0))
    task2 = asyncio.create_task(simple_task("Task2", 1.0))
    task3 = asyncio.create_task(simple_task("Task3", 1.5))

    # 모든 작업 완료 대기
    results = await asyncio.gather(task1, task2, task3)
    print(f"Task 결과들: {results}")


async def main_with_timeout():
    """타임아웃 처리 예제"""
    print("\n=== 타임아웃 처리 예제 ===")

    try:
        # 2초 타임아웃으로 3초 작업 실행
        result = await asyncio.wait_for(simple_task("Timeout", 3.0), timeout=2.0)
        print(f"결과: {result}")
    except asyncio.TimeoutError:
        print("작업이 타임아웃되었습니다!")


async def main_with_cancellation():
    """작업 취소 예제"""
    print("\n=== 작업 취소 예제 ===")

    async def long_running_task():
        try:
            for i in range(10):
                print(f"긴 작업 진행 중... {i+1}/10")
                await asyncio.sleep(0.5)
            return "긴 작업 완료"
        except asyncio.CancelledError:
            print("작업이 취소되었습니다!")
            raise

    # 2초 후 작업 취소
    task = asyncio.create_task(long_running_task())
    await asyncio.sleep(2.0)
    task.cancel()

    try:
        result = await task
        print(f"결과: {result}")
    except asyncio.CancelledError:
        print("작업이 성공적으로 취소되었습니다")


if __name__ == "__main__":
    print("asyncio 기초 학습을 시작합니다...\n")

    # 모든 예제 실행
    asyncio.run(main_basic())
    asyncio.run(main_concurrent())
    asyncio.run(main_data_fetching())
    asyncio.run(main_with_tasks())
    asyncio.run(main_with_timeout())
    asyncio.run(main_with_cancellation())

    print("\nasyncio 기초 학습이 완료되었습니다!")
