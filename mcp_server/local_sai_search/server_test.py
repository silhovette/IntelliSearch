import asyncio
import httpx
from typing import List, Dict

RAG_SERVICE_URL = "http://127.0.0.1:39255/search"
TIMEOUT = 10.0


async def check_service_alive() -> bool:
    """测试 RAG Service 端口是否存活"""
    payload = {
        "query": "ping",
        "score_threshold": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(RAG_SERVICE_URL, json=payload)
            resp.raise_for_status()
            print("✅ RAG Service 正在运行")
            return True
    except Exception as e:
        print(f"❌ RAG Service 不可用: {e}")
        return False


def get_test_cases() -> List[Dict]:
    """构造 5 个测试用例"""
    return [
        {
            "name": "课程测试",
            "query": "上海交通大学人工智能学院有哪些核心课程？",
        },
        {
            "name": "师资测试",
            "query": "SJTU AI 有哪些做大模型或机器学习的老师？",
        },
        {
            "name": "招生测试",
            "query": "人工智能学院硕士研究生的招生要求是什么？",
        },
        {
            "name": "科研方向测试",
            "query": "上海交大人工智能学院的主要研究方向有哪些？",
        },
        {
            "name": "学生生活",
            "query": "人工智能学院研究生的日常科研和生活情况如何？",
        },
    ]


async def run_testcase(case: Dict):
    payload = {
        "query": case["query"],
        "score_threshold": 0.3,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(RAG_SERVICE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    print(f"\n=== ✅ Testcase: {case['name']} ===")
    print(f"Query : {case['query']}")
    print(f"Status: {data.get('status')}")

    results = data.get("results", [])
    print(f"Results Count: {len(results)}")

    for i, r in enumerate(results):
        print(f"[{i}] {r}")


async def main():
    alive = await check_service_alive()
    if not alive:
        return

    test_cases = get_test_cases()
    for case in test_cases:
        try:
            await run_testcase(case)
        except Exception as e:
            print(f"❌ Testcase {case['name']} 失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
