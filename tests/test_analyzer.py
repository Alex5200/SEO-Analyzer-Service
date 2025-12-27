# tests/test_analyzer.py
import pytest
import time
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.parser import PageParser, ParseResult
from app.cache import cache


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestAnalyzeEndpoint:

    def test_analyze_success(self, client):
        mock_result = ParseResult(
            title="Habr - сообщество IT-специалистов",
            h1_count=1,
            meta_description="Хабр — сообщество IT-специалистов"
        )

        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result
            response = client.post("/api/analyze", json={"url": "https://habr.com/"})

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://habr.com/"
        assert data["title"] == "Habr - сообщество IT-специалистов"
        assert data["h1_count"] == 1
        assert data["meta_description"] == "Хабр — сообщество IT-специалистов"
        assert data["cached"] is False

    def test_analyze_invalid_url(self, client):
        """Тест: валидация URL (невалидный формат)."""
        response = client.post("/api/analyze", json={"url": "invalid-url"})
        assert response.status_code == 422

    def test_analyze_navigation_error(self, client):
        """Тест: ошибка навигации → 502."""
        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
            response = client.post("/api/analyze", json={"url": "https://nonexistent-site.invalid"})

        assert response.status_code == 502
        assert response.json()["error"] == "navigation_error"

    def test_analyze_timeout(self, client):
        """Тест: таймаут → 504."""
        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("Timeout 10000ms exceeded")
            response = client.post("/api/analyze", json={"url": "https://slow-site.example"})

        assert response.status_code == 504
        assert response.json()["error"] == "timeout"

    def test_analyze_without_h1(self, client):
        """Тест: страница без h1 и meta description."""
        mock_result = ParseResult(title="Страница без H1", h1_count=0, meta_description=None)
        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result
            response = client.post("/api/analyze", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Страница без H1"
        assert data["h1_count"] == 0
        assert data["meta_description"] is None


class TestCaching:

    def test_cache_hit(self, client):
        mock_result = ParseResult(title="Cached Page", h1_count=0, meta_description=None)
        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result
            r1 = client.post("/api/analyze", json={"url": "https://example.com"})
            r2 = client.post("/api/analyze", json={"url": "https://example.com"})

        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is True
        assert mock_analyze.call_count == 1

    def test_cache_different_urls(self, client):
        mock_result1 = ParseResult(title="Site A", h1_count=1, meta_description="A")
        mock_result2 = ParseResult(title="Site B", h1_count=2, meta_description="B")

        with patch.object(PageParser, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result1
            r1 = client.post("/api/analyze", json={"url": "https://example.com"})

            mock_analyze.return_value = mock_result2
            r2 = client.post("/api/analyze", json={"url": "https://habr.com"})

        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is False
        assert mock_analyze.call_count == 2

    def test_cache_ttl_unit(self):
        from app.cache import Cache
        cache_instance = Cache(ttl_seconds=1)
        cache_instance.set("key", {"value": 1})
        assert cache_instance.get("key") is not None

        time.sleep(1.1)

        assert cache_instance.get("key") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])