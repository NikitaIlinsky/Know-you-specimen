"""Integration tests for the Know Your Specimen REST API server."""

import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient pointed at a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from know_your_specimen.config import config

        config.output_dir = tmpdir

        from know_your_specimen.server import app

        yield TestClient(app)


@pytest.fixture
def valid_image_bytes() -> bytes:
    """Create a small valid JPEG image in memory."""
    import cv2
    import numpy as np

    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[:, :] = (100, 150, 200)  # BGR
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


class TestHealth:
    """Tests for the health-check endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAnalyze:
    """Tests for the POST /api/v1/analyze endpoint."""

    def test_no_file_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/analyze")
        assert response.status_code == 422

    def test_invalid_extension_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 422

    def test_valid_image_returns_stats_and_urls(
        self, client: TestClient, valid_image_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("specimen.jpg", valid_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert isinstance(data["stats"], dict)
        assert "artifacts" in data
        assert "annotated_image" in data["artifacts"]
        assert "mask_image" in data["artifacts"]
        assert "stats_json" in data["artifacts"]
        for url in data["artifacts"].values():
            assert url.startswith("/api/v1/output/")

    @patch("know_your_specimen.server.process_file")
    def test_unreadable_image_returns_422(
        self, mock_process, client: TestClient, valid_image_bytes: bytes
    ) -> None:
        mock_process.return_value = None
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("bad.jpg", valid_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 422
        assert "unreadable" in response.json()["detail"].lower()

    @patch("know_your_specimen.server.process_file")
    def test_processing_error_returns_500(
        self, mock_process, client: TestClient, valid_image_bytes: bytes
    ) -> None:
        mock_process.side_effect = RuntimeError("Simulated failure")
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("sample.jpg", valid_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 500
        assert "Simulated failure" in response.json()["detail"]

    def test_generated_artifacts_are_servable(
        self, client: TestClient, valid_image_bytes: bytes
    ) -> None:
        """End-to-end: analyze an image, then download every artifact URL."""
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("ore.jpg", valid_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        artifacts = resp.json()["artifacts"]

        for url in artifacts.values():
            get_resp = client.get(url)
            assert get_resp.status_code == 200


class TestOutputServing:
    """Tests for the GET /api/v1/output/{filename} endpoint."""

    def test_nonexistent_file_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/output/nonexistent_abc.jpg")
        assert response.status_code == 404
