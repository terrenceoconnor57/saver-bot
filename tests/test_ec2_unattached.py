"""Tests for EC2 unattached volumes scanner."""

import boto3
from moto import mock_aws

from lambdas.scan_ec2_unattached_ebs.handler import handler, validate_event
from saverbot.scanners.ec2_unattached import list_unattached_volumes


@mock_aws
def test_list_unattached_volumes_finds_only_unattached() -> None:
    """Test that scanner finds only unattached volumes."""
    # Setup
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Create 2 unattached volumes
    unattached1 = ec2.create_volume(AvailabilityZone="us-east-1a", Size=10)
    unattached2 = ec2.create_volume(
        AvailabilityZone="us-east-1b",
        Size=20,
        TagSpecifications=[
            {
                "ResourceType": "volume",
                "Tags": [
                    {"Key": "Name", "Value": "test-volume"},
                    {"Key": "Environment", "Value": "test"},
                ],
            }
        ],
    )

    # Create an instance and attach a volume to it
    instance = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    instance_id = instance["Instances"][0]["InstanceId"]

    attached = ec2.create_volume(AvailabilityZone="us-east-1a", Size=30)
    ec2.attach_volume(
        VolumeId=attached["VolumeId"],
        InstanceId=instance_id,
        Device="/dev/sdf",
    )

    # Test
    session = boto3.Session()
    volumes = list_unattached_volumes(session, "us-east-1")

    # Assert
    assert len(volumes) == 2

    volume_ids = {v["VolumeId"] for v in volumes}
    assert unattached1["VolumeId"] in volume_ids
    assert unattached2["VolumeId"] in volume_ids
    assert attached["VolumeId"] not in volume_ids

    # Check structure
    for vol in volumes:
        assert "Region" in vol
        assert "VolumeId" in vol
        assert "Size" in vol
        assert "CreateTime" in vol
        assert "Tags" in vol
        assert vol["Region"] == "us-east-1"

    # Check tags on tagged volume
    tagged_vol = next(v for v in volumes if v["VolumeId"] == unattached2["VolumeId"])
    assert tagged_vol["Tags"]["Name"] == "test-volume"
    assert tagged_vol["Tags"]["Environment"] == "test"
    assert tagged_vol["Size"] == 20


@mock_aws
def test_handler_returns_correct_schema() -> None:
    """Test that handler returns the correct response schema."""
    # Setup
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=10)
    ec2.create_volume(AvailabilityZone="us-east-1b", Size=20)

    # Create role for moto (it will auto-stub STS)
    iam = boto3.client("iam", region_name="us-east-1")
    iam.create_role(
        RoleName="TestRole",
        AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}',
    )

    # Test
    event = {
        "role_arn": "arn:aws:iam::123456789012:role/TestRole",
        "external_id": "test-external-id",
        "regions": ["us-east-1"],
    }

    result = handler(event, None)

    # Assert schema
    assert "meta" in result
    assert "items" in result
    assert "count" in result

    meta = result["meta"]
    assert meta["service"] == "ec2"
    assert meta["rule"] == "ebs-unattached"
    assert meta["regions"] == ["us-east-1"]
    assert "scanned_at" in meta
    assert "duration_ms" in meta
    assert isinstance(meta["duration_ms"], int)

    assert result["count"] == 2
    assert len(result["items"]) == 2


@mock_aws
def test_handler_with_multiple_regions() -> None:
    """Test handler scanning multiple regions."""
    # Setup volumes in different regions
    ec2_us_east = boto3.client("ec2", region_name="us-east-1")
    ec2_us_east.create_volume(AvailabilityZone="us-east-1a", Size=10)

    ec2_us_west = boto3.client("ec2", region_name="us-west-2")
    ec2_us_west.create_volume(AvailabilityZone="us-west-2a", Size=20)
    ec2_us_west.create_volume(AvailabilityZone="us-west-2b", Size=30)

    # Create IAM role
    iam = boto3.client("iam", region_name="us-east-1")
    iam.create_role(
        RoleName="TestRole",
        AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}',
    )

    # Test
    event = {
        "role_arn": "arn:aws:iam::123456789012:role/TestRole",
        "external_id": "test-external-id",
        "regions": ["us-east-1", "us-west-2"],
    }

    result = handler(event, None)

    # Assert
    assert result["count"] == 3
    assert len(result["items"]) == 3

    regions = {v["Region"] for v in result["items"]}
    assert "us-east-1" in regions
    assert "us-west-2" in regions


def test_validate_event_missing_role_arn() -> None:
    """Test validation fails when role_arn is missing."""
    event = {"external_id": "test", "regions": ["us-east-1"]}
    error = validate_event(event)

    assert error is not None
    assert error["error"] == "ValidationError"
    assert "role_arn" in error["message"]


def test_validate_event_missing_external_id() -> None:
    """Test validation fails when external_id is missing."""
    event = {"role_arn": "arn:aws:iam::123:role/X", "regions": ["us-east-1"]}
    error = validate_event(event)

    assert error is not None
    assert error["error"] == "ValidationError"
    assert "external_id" in error["message"]


def test_validate_event_missing_regions() -> None:
    """Test validation fails when regions is missing."""
    event = {"role_arn": "arn:aws:iam::123:role/X", "external_id": "test"}
    error = validate_event(event)

    assert error is not None
    assert error["error"] == "ValidationError"
    assert "regions" in error["message"]


def test_validate_event_empty_regions() -> None:
    """Test validation fails when regions list is empty."""
    event = {
        "role_arn": "arn:aws:iam::123:role/X",
        "external_id": "test",
        "regions": [],
    }
    error = validate_event(event)

    assert error is not None
    assert error["error"] == "ValidationError"
    assert "non-empty list" in error["message"]


def test_validate_event_valid_input() -> None:
    """Test validation passes with valid input."""
    event = {
        "role_arn": "arn:aws:iam::123:role/X",
        "external_id": "test",
        "regions": ["us-east-1"],
    }
    error = validate_event(event)

    assert error is None


@mock_aws
def test_handler_returns_error_for_invalid_input() -> None:
    """Test handler returns clean error dict for invalid input."""
    event = {"role_arn": "arn:aws:iam::123:role/X"}  # Missing external_id and regions

    result = handler(event, None)

    assert "error" in result
    assert result["error"] == "ValidationError"
    assert "message" in result
