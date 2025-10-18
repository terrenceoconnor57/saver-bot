"""Lambda handler for scanning unattached EBS volumes."""

import json
import sys
import time
from datetime import UTC, datetime
from typing import Any

from saverbot.assume import AssumeError, assume
from saverbot.jsonlog import setup_logger
from saverbot.scanners.ec2_unattached import list_unattached_volumes

logger = setup_logger(__name__)


def validate_event(event: dict[str, Any]) -> dict[str, str] | None:
    """
    Validate the Lambda event input.

    Args:
        event: Lambda event dictionary

    Returns:
        Error dict if validation fails, None if valid
    """
    if not event.get("role_arn"):
        return {
            "error": "ValidationError",
            "message": "Missing required field: role_arn",
        }

    if not event.get("external_id"):
        return {
            "error": "ValidationError",
            "message": "Missing required field: external_id",
        }

    regions = event.get("regions")
    if regions is None:
        return {
            "error": "ValidationError",
            "message": "Missing required field: regions",
        }

    if not isinstance(regions, list) or len(regions) == 0:
        return {
            "error": "ValidationError",
            "message": "Field 'regions' must be a non-empty list",
        }

    return None


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda handler for scanning unattached EBS volumes.

    Args:
        event: Lambda event with role_arn, external_id, regions
        context: Lambda context (unused)

    Returns:
        Dict with meta, items, and count
    """
    start_time = time.time()
    logger.info("Starting EBS unattached volumes scan", extra={"event": event})

    # Validate input
    validation_error = validate_event(event)
    if validation_error:
        logger.error(
            "Validation failed",
            extra={"validation_error": validation_error["error"], "details": validation_error["message"]},
        )
        return validation_error

    role_arn = event["role_arn"]
    external_id = event["external_id"]
    regions = event["regions"]

    # Assume role
    try:
        session = assume(role_arn, external_id)
    except AssumeError as e:
        error_response = {
            "error": "AssumeRoleError",
            "message": f"Failed to assume role: {e.message}",
            "code": e.code,
        }
        logger.error("Failed to assume role", extra=error_response)
        return error_response

    # Scan all regions
    all_volumes = []
    for region in regions:
        try:
            volumes = list_unattached_volumes(session, region)
            all_volumes.extend(volumes)
        except Exception as e:
            logger.error(
                "Failed to scan region",
                extra={"region": region, "error": str(e)},
            )
            # Continue scanning other regions even if one fails
            continue

    duration_ms = int((time.time() - start_time) * 1000)

    response = {
        "meta": {
            "service": "ec2",
            "rule": "ebs-unattached",
            "regions": regions,
            "scanned_at": datetime.now(UTC).isoformat(),
            "duration_ms": duration_ms,
        },
        "items": all_volumes,
        "count": len(all_volumes),
    }

    logger.info(
        "Scan completed",
        extra={"count": len(all_volumes), "duration_ms": duration_ms},
    )

    return response


def main() -> None:
    """Run handler from command line for local testing."""
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1]) as f:
            event = json.load(f)
    else:
        # Read from stdin
        event = json.load(sys.stdin)

    result = handler(event, None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
