"""AWS STS assume role functionality."""

import boto3
from botocore.exceptions import ClientError

from saverbot.jsonlog import setup_logger

logger = setup_logger(__name__)


class AssumeError(Exception):
    """Custom exception for assume role errors."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize AssumeError with code and message."""
        self.code = code
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        """String representation of the error."""
        return f"[{self.code}] {self.message}"


def assume(role_arn: str, external_id: str, duration: int = 900) -> boto3.Session:
    """
    Assume an AWS IAM role and return a boto3 session.

    Args:
        role_arn: The ARN of the role to assume
        external_id: External ID for additional security
        duration: Session duration in seconds (default: 900)

    Returns:
        A boto3.Session with temporary credentials

    Raises:
        AssumeError: If the assume role operation fails
    """
    logger.info(
        "Attempting to assume role",
        extra={"role_arn": role_arn, "duration": duration},
    )

    try:
        sts_client = boto3.client("sts")
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="saverbot-session",
            ExternalId=external_id,
            DurationSeconds=duration,
        )

        credentials = response["Credentials"]

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        logger.info("Successfully assumed role", extra={"role_arn": role_arn})
        return session

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(
            "Failed to assume role",
            extra={
                "role_arn": role_arn,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

        raise AssumeError(code=error_code, message=error_message) from e

    except Exception as e:
        logger.error(
            "Unexpected error assuming role",
            extra={"role_arn": role_arn, "error": str(e)},
        )
        raise AssumeError(code="UnexpectedError", message=str(e)) from e
