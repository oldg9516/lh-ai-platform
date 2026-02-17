"""Tests for api/learning_api.py — Phase 9.2 admin endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# --- list_instruction_updates ---


class TestListInstructionUpdates:
    @patch("api.learning_api.get_instruction_updates")
    def test_list_all(self, mock_get):
        mock_get.return_value = [
            {"id": "1", "category": "shipping", "status": "pending"},
            {"id": "2", "category": "payment", "status": "approved"},
        ]

        response = client.get("/api/learning/instruction-updates")

        assert response.status_code == 200
        assert len(response.json()) == 2
        mock_get.assert_called_once_with(status=None, category=None)

    @patch("api.learning_api.get_instruction_updates")
    def test_filter_by_status(self, mock_get):
        mock_get.return_value = [{"id": "1", "status": "pending"}]

        response = client.get("/api/learning/instruction-updates?status=pending")

        assert response.status_code == 200
        mock_get.assert_called_once_with(status="pending", category=None)

    @patch("api.learning_api.get_instruction_updates")
    def test_filter_by_category(self, mock_get):
        mock_get.return_value = []

        response = client.get("/api/learning/instruction-updates?category=shipping_or_delivery_question")

        assert response.status_code == 200
        mock_get.assert_called_once_with(status=None, category="shipping_or_delivery_question")


# --- get_update ---


class TestGetUpdate:
    @patch("api.learning_api.get_instruction_update")
    def test_found(self, mock_get):
        mock_get.return_value = {"id": "uuid-1", "category": "shipping", "status": "pending"}

        response = client.get("/api/learning/instruction-updates/uuid-1")

        assert response.status_code == 200
        assert response.json()["id"] == "uuid-1"

    @patch("api.learning_api.get_instruction_update")
    def test_not_found(self, mock_get):
        mock_get.return_value = None

        response = client.get("/api/learning/instruction-updates/nonexistent")

        assert response.status_code == 404


# --- approve ---


class TestApproveUpdate:
    @patch("api.learning_api.update_instruction_status")
    @patch("api.learning_api.get_instruction_update")
    def test_approve_pending(self, mock_get, mock_update):
        mock_get.return_value = {"id": "uuid-1", "status": "pending", "category": "shipping"}
        mock_update.return_value = {"id": "uuid-1", "status": "approved", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/approve")

        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        mock_update.assert_called_once_with("uuid-1", "approved")

    @patch("api.learning_api.get_instruction_update")
    def test_approve_deployed_fails(self, mock_get):
        mock_get.return_value = {"id": "uuid-1", "status": "deployed", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/approve")

        assert response.status_code == 400

    @patch("api.learning_api.get_instruction_update")
    def test_approve_not_found(self, mock_get):
        mock_get.return_value = None

        response = client.post("/api/learning/instruction-updates/nonexistent/approve")

        assert response.status_code == 404


# --- reject ---


class TestRejectUpdate:
    @patch("api.learning_api.update_instruction_status")
    @patch("api.learning_api.get_instruction_update")
    def test_reject_pending(self, mock_get, mock_update):
        mock_get.return_value = {"id": "uuid-1", "status": "pending", "category": "shipping"}
        mock_update.return_value = {"id": "uuid-1", "status": "rejected", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/reject")

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    @patch("api.learning_api.update_instruction_status")
    @patch("api.learning_api.get_instruction_update")
    def test_reject_approved(self, mock_get, mock_update):
        mock_get.return_value = {"id": "uuid-1", "status": "approved", "category": "shipping"}
        mock_update.return_value = {"id": "uuid-1", "status": "rejected", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/reject")

        assert response.status_code == 200


# --- deploy ---


class TestDeployUpdate:
    @patch("api.learning_api.update_instruction_status")
    @patch("api.learning_api.get_instruction_update")
    def test_deploy_approved(self, mock_get, mock_update):
        mock_get.return_value = {"id": "uuid-1", "status": "approved", "category": "shipping"}
        mock_update.return_value = {"id": "uuid-1", "status": "deployed", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/deploy")

        assert response.status_code == 200
        assert response.json()["status"] == "deployed"

    @patch("api.learning_api.get_instruction_update")
    def test_deploy_pending_fails(self, mock_get):
        mock_get.return_value = {"id": "uuid-1", "status": "pending", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/deploy")

        assert response.status_code == 400
        assert "pending" in response.json()["detail"]

    @patch("api.learning_api.get_instruction_update")
    def test_deploy_rejected_fails(self, mock_get):
        mock_get.return_value = {"id": "uuid-1", "status": "rejected", "category": "shipping"}

        response = client.post("/api/learning/instruction-updates/uuid-1/deploy")

        assert response.status_code == 400


# --- analyze ---


class TestAnalyze:
    @patch("api.learning_api.run_pattern_analysis", new_callable=AsyncMock)
    def test_trigger_analysis(self, mock_analysis):
        mock_analysis.return_value = ["uuid-1", "uuid-2"]

        response = client.post("/api/learning/instruction-updates/analyze")

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert data["update_ids"] == ["uuid-1", "uuid-2"]

    @patch("api.learning_api.run_pattern_analysis", new_callable=AsyncMock)
    def test_no_patterns_found(self, mock_analysis):
        mock_analysis.return_value = []

        response = client.post("/api/learning/instruction-updates/analyze")

        assert response.status_code == 200
        assert response.json()["created"] == 0
