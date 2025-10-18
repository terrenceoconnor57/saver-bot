# saverbot
Slack-first AWS cost-saver

## Quickstart

### Installation and Testing

```bash
make install && make test
```

## Lambda Functions

### scan_ec2_unattached_ebs

Scans AWS accounts for unattached EBS volumes.

#### Local Testing

Run the handler locally with test input:

```bash
python -m lambdas.scan_ec2_unattached_ebs.handler <<EOF
{
  "role_arn": "arn:aws:iam::123456789012:role/CrossAccountRole",
  "external_id": "your-external-id",
  "regions": ["us-east-1", "us-west-2"]
}
EOF
```

#### Building the Lambda Package

```bash
make build_lambda_scan_ebs
```

This creates `lambda-scan-ebs.zip` ready for deployment.

#### Testing

Run tests for the EC2 unattached volumes scanner:

```bash
make test_lambda_scan_ebs
```

#### Deployment

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

#### Input Schema

```json
{
  "role_arn": "arn:aws:iam::ACCOUNT:role/ROLE_NAME",
  "external_id": "external-id-value",
  "regions": ["us-east-1", "us-west-2", "..."]
}
```

#### Output Schema

```json
{
  "meta": {
    "service": "ec2",
    "rule": "ebs-unattached",
    "regions": ["us-east-1"],
    "scanned_at": "2025-10-18T19:30:00.000000+00:00",
    "duration_ms": 1234
  },
  "items": [
    {
      "Region": "us-east-1",
      "VolumeId": "vol-123456789",
      "Size": 100,
      "CreateTime": "2025-01-01T00:00:00+00:00",
      "Tags": {
        "Name": "my-volume",
        "Environment": "production"
      }
    }
  ],
  "count": 1
}
```
