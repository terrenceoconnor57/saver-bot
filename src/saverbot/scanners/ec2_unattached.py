"""Scanner for unattached EBS volumes."""

from typing import Any

import boto3

from saverbot.jsonlog import setup_logger

logger = setup_logger(__name__)


def list_unattached_volumes(session: boto3.Session, region: str) -> list[dict[str, Any]]:
    """
    List all unattached EBS volumes in a region.

    Args:
        session: boto3 Session with credentials
        region: AWS region to scan

    Returns:
        List of unattached volume dictionaries with simplified structure
    """
    logger.info("Scanning for unattached volumes", extra={"region": region})

    ec2 = session.client("ec2", region_name=region)

    try:
        response = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])

        volumes = []
        for vol in response.get("Volumes", []):
            # Extract tags as a simple dict
            tags = {}
            for tag in vol.get("Tags", []):
                tags[tag["Key"]] = tag["Value"]

            volumes.append(
                {
                    "Region": region,
                    "VolumeId": vol["VolumeId"],
                    "Size": vol["Size"],
                    "CreateTime": vol["CreateTime"].isoformat(),
                    "Tags": tags,
                }
            )

        logger.info(
            "Found unattached volumes",
            extra={"region": region, "count": len(volumes)},
        )
        return volumes

    except Exception as e:
        logger.error(
            "Failed to scan region",
            extra={"region": region, "error": str(e)},
        )
        raise
