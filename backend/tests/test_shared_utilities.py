import unittest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import (
    CredentialSecurityException,
    DuplicateException,
    HeliosException,
    NotFoundException,
    PipelineStageException,
    TenantMismatchException,
    ValidationException,
)
from app.core.response import (
    ApiResponse,
    error_response,
    success_response,
)
from app.main import app


class TestExceptions(unittest.TestCase):
    """Test custom exception classes and their HTTP status mappings."""

    def test_not_found_exception(self):
        exc = NotFoundException("Tenant not found", details={"tenant_id": 999})
        self.assertEqual(exc.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(exc.message, "Tenant not found")
        self.assertEqual(exc.details["tenant_id"], 999)

    def test_duplicate_exception(self):
        exc = DuplicateException("User already exists", details={"email": "a@b.com"})
        self.assertEqual(exc.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(exc.message, "User already exists")

    def test_validation_exception(self):
        exc = ValidationException("Invalid email format")
        self.assertEqual(exc.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_tenant_mismatch_exception(self):
        exc = TenantMismatchException("Cross-tenant access forbidden")
        self.assertEqual(exc.status_code, status.HTTP_403_FORBIDDEN)

    def test_pipeline_stage_exception(self):
        exc = PipelineStageException("Silver cleaning failed", stage="silver")
        self.assertEqual(exc.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(exc.details.get("stage"), "silver")

    def test_credential_security_exception(self):
        exc = CredentialSecurityException("Databricks Secrets unreachable")
        self.assertEqual(exc.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIsInstance(exc, HeliosException)


class TestResponseWrapper(unittest.TestCase):
    """Test standard ApiResponse models and helper constructors."""

    def test_success_response_helper(self):
        resp = success_response(data={"count": 42}, message="Fetched successfully")
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, {"count": 42})
        self.assertEqual(resp.message, "Fetched successfully")

    def test_error_response_helper(self):
        resp = error_response(message="Operation failed", data={"code": "ERR_FAIL"})
        self.assertFalse(resp.success)
        self.assertEqual(resp.data, {"code": "ERR_FAIL"})
        self.assertEqual(resp.message, "Operation failed")

    def test_api_response_pydantic_serialization(self):
        resp = ApiResponse[str](success=True, data="hello", message="ok")
        d = resp.model_dump()
        self.assertEqual(d["success"], True)
        self.assertEqual(d["data"], "hello")
        self.assertEqual(d["message"], "ok")


class TestGlobalExceptionHandler(unittest.TestCase):
    """Test FastAPI application global exception handler formatting."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_global_handler_for_not_found(self):
        # Dynamically test a mock route throwing NotFoundException
        @app.get("/test-not-found-exception", include_in_schema=False)
        def trigger_not_found():
            raise NotFoundException("Mock item not found", details={"id": 123})

        response = self.client.get("/test-not-found-exception")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "Mock item not found")
        self.assertEqual(payload["error_type"], "NotFoundException")
        self.assertEqual(payload["details"]["id"], 123)
