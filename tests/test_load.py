# test_load.py
import asyncio
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"


async def make_request(client: httpx.AsyncClient, user_id: int):
    response = await client.post("/api/analyze/", json={"url": "http://google.com"})
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_100_users():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        tasks = [make_request(client, i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        await asyncio.sleep(1)  
    assert len(results) == 100
