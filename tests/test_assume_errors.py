"""Test error handling in assume role functionality."""

import boto3
import pytest
from botocore.stub import Stubber

from saverbot.assume import AssumeError, assume


def test_assume_access_denied() -> None:
    """Test that AccessDenied errors are handled correctly."""
    # Create a real STS client and stub it
    sts_client = boto3.client("sts", region_name="us-east-1")

    with Stubber(sts_client) as stubber:
        # Stub the assume_role call to raise AccessDenied
        stubber.add_client_error(
            "assume_role",
            service_error_code="AccessDenied",
            service_message="User is not authorized to perform: sts:AssumeRole",
        )

        # Patch boto3.client to return our stubbed client
        original_client = boto3.client
        boto3.client = lambda service, **kwargs: (  # type: ignore[assignment]
            sts_client if service == "sts" else original_client(service, **kwargs)
        )

        try:
            with pytest.raises(AssumeError) as exc_info:
                assume(
                    role_arn="arn:aws:iam::123456789012:role/test-role",
                    external_id="test-external-id",
                )

            assert exc_info.value.code == "AccessDenied"
            assert "not authorized" in exc_info.value.message
        finally:
            # Restore original boto3.client
            boto3.client = original_client


def test_assume_invalid_parameter() -> None:
    """Test that RegionDisabled errors are handled correctly."""
    sts_client = boto3.client("sts", region_name="us-east-1")

    with Stubber(sts_client) as stubber:
        # Stub the assume_role call to raise RegionDisabledException
        stubber.add_client_error(
            "assume_role",
            service_error_code="RegionDisabledException",
            service_message="The requested region is disabled",
        )

        # Patch boto3.client to return our stubbed client
        original_client = boto3.client
        boto3.client = lambda service, **kwargs: (  # type: ignore[assignment]
            sts_client if service == "sts" else original_client(service, **kwargs)
        )

        try:
            with pytest.raises(AssumeError) as exc_info:
                assume(
                    role_arn="arn:aws:iam::123456789012:role/test-role",
                    external_id="test-external-id",
                )

            assert exc_info.value.code == "RegionDisabledException"
            assert "region" in exc_info.value.message.lower()
        finally:
            # Restore original boto3.client
            boto3.client = original_client


def test_assume_malformed_policy() -> None:
    """Test that MalformedPolicyDocument errors are handled correctly."""
    sts_client = boto3.client("sts", region_name="us-east-1")

    with Stubber(sts_client) as stubber:
        # Stub the assume_role call to raise MalformedPolicyDocument
        stubber.add_client_error(
            "assume_role",
            service_error_code="MalformedPolicyDocument",
            service_message="The policy document is malformed",
        )

        # Patch boto3.client to return our stubbed client
        original_client = boto3.client
        boto3.client = lambda service, **kwargs: (  # type: ignore[assignment]
            sts_client if service == "sts" else original_client(service, **kwargs)
        )

        try:
            with pytest.raises(AssumeError) as exc_info:
                assume(
                    role_arn="arn:aws:iam::123456789012:role/test-role",
                    external_id="test-external-id",
                )

            assert exc_info.value.code == "MalformedPolicyDocument"
            assert "malformed" in exc_info.value.message.lower()
        finally:
            # Restore original boto3.client
            boto3.client = original_client


def test_assume_error_string_representation() -> None:
    """Test that AssumeError has proper string representation."""
    error = AssumeError(code="TestCode", message="Test message")

    assert error.code == "TestCode"
    assert error.message == "Test message"
    assert str(error) == "[TestCode] Test message"
