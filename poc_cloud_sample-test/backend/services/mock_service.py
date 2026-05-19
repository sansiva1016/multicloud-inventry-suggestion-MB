"""Mock data service providing realistic cloud resource and billing data."""
from datetime import date, timedelta
import hashlib
import random

# ---------------------------------------------------------------------------
# AWS mock data
# ---------------------------------------------------------------------------

AWS_RESOURCES = [
    # EC2 Instances
    {
        "name": "web-server-prod", "type": "EC2", "region": "us-east-1a", "status": "running",
        "tags": "env:prod,team:web", "size": "t3.medium",
        # Core
        "instance_type": "t3.medium", "ami_id": "ami-0abcdef1234567890",
        "launch_time": "2024-01-15 08:30:00 UTC", "platform": "Linux/UNIX", "architecture": "x86_64",
        # Network
        "availability_zone": "us-east-1a", "vpc_id": "vpc-001", "subnet_id": "subnet-001",
        "private_ip": "10.0.1.10", "private_dns_name": "ip-10-0-1-10.ec2.internal",
        "public_ip": "54.210.11.1", "public_dns_name": "ec2-54-210-11-1.compute-1.amazonaws.com",
        "security_groups": "web-sg (sg-001), default (sg-000)",
        "source_dest_check": True,
        # Storage
        "root_device_type": "ebs", "root_device_name": "/dev/xvda",
        "ebs_optimized": True, "block_devices": "/dev/xvda (vol-001)",
        # Security
        "key_name": "prod-keypair", "iam_role": "WebServerRole", "tenancy": "default",
        # Performance & Monitoring
        "monitoring_state": "disabled", "cpu_core_count": 1, "cpu_threads_per_core": 2,
        "hypervisor": "nitro", "virtualization_type": "hvm",
        # State
        "state_transition_reason": "",
    },
    {
        "name": "api-server-1", "type": "EC2", "region": "us-east-1b", "status": "running",
        "tags": "env:prod,team:api", "size": "t3.large",
        "instance_type": "t3.large", "ami_id": "ami-0abcdef1234567891",
        "launch_time": "2024-02-10 12:00:00 UTC", "platform": "Linux/UNIX", "architecture": "x86_64",
        "availability_zone": "us-east-1b", "vpc_id": "vpc-001", "subnet_id": "subnet-002",
        "private_ip": "10.0.1.11", "private_dns_name": "ip-10-0-1-11.ec2.internal",
        "public_ip": "", "public_dns_name": "",
        "security_groups": "api-sg (sg-002), default (sg-000)",
        "source_dest_check": True,
        "root_device_type": "ebs", "root_device_name": "/dev/xvda",
        "ebs_optimized": True, "block_devices": "/dev/xvda (vol-002)",
        "key_name": "prod-keypair", "iam_role": "ApiServerRole", "tenancy": "default",
        "monitoring_state": "enabled", "cpu_core_count": 2, "cpu_threads_per_core": 2,
        "hypervisor": "nitro", "virtualization_type": "hvm",
        "state_transition_reason": "",
    },
    {
        "name": "api-server-2", "type": "EC2", "region": "us-west-2a", "status": "stopped",
        "tags": "env:staging,team:api", "size": "t2.micro",
        "instance_type": "t2.micro", "ami_id": "ami-0fedcba9876543210",
        "launch_time": "2023-11-20 09:15:00 UTC", "platform": "Linux/UNIX", "architecture": "x86_64",
        "availability_zone": "us-west-2a", "vpc_id": "vpc-002", "subnet_id": "subnet-101",
        "private_ip": "10.1.1.10", "private_dns_name": "ip-10-1-1-10.us-west-2.compute.internal",
        "public_ip": "", "public_dns_name": "",
        "security_groups": "staging-sg (sg-101)",
        "source_dest_check": True,
        "root_device_type": "ebs", "root_device_name": "/dev/xvda",
        "ebs_optimized": False, "block_devices": "/dev/xvda (vol-101)",
        "key_name": "staging-keypair", "iam_role": "", "tenancy": "default",
        "monitoring_state": "disabled", "cpu_core_count": 1, "cpu_threads_per_core": 1,
        "hypervisor": "xen", "virtualization_type": "hvm",
        "state_transition_reason": "User initiated (2024-03-01 10:00:00 GMT)",
    },
    {
        "name": "batch-worker", "type": "EC2", "region": "eu-west-1a", "status": "running",
        "tags": "env:prod,team:data", "size": "c5.xlarge",
        "instance_type": "c5.xlarge", "ami_id": "ami-0abcdef1234567892",
        "launch_time": "2024-03-01 06:00:00 UTC", "platform": "Linux/UNIX", "architecture": "x86_64",
        "availability_zone": "eu-west-1a", "vpc_id": "vpc-001", "subnet_id": "subnet-003",
        "private_ip": "10.0.2.20", "private_dns_name": "ip-10-0-2-20.eu-west-1.compute.internal",
        "public_ip": "", "public_dns_name": "",
        "security_groups": "batch-sg (sg-003), default (sg-000)",
        "source_dest_check": True,
        "root_device_type": "ebs", "root_device_name": "/dev/xvda",
        "ebs_optimized": True, "block_devices": "/dev/xvda (vol-003), /dev/xvdb (vol-004)",
        "key_name": "prod-keypair", "iam_role": "BatchWorkerRole", "tenancy": "default",
        "monitoring_state": "enabled", "cpu_core_count": 2, "cpu_threads_per_core": 2,
        "hypervisor": "nitro", "virtualization_type": "hvm",
        "state_transition_reason": "",
    },
    # S3
    {"name": "app-assets", "type": "S3", "region": "us-east-1", "status": "active", "tags": "env:prod,team:web", "size": "2.4 GB", "storage_size": "2.4 GB"},
    {"name": "data-lake-raw", "type": "S3", "region": "us-east-1", "status": "active", "tags": "env:prod,team:data", "size": "842.1 GB", "storage_size": "842.1 GB"},
    {"name": "backups-bucket", "type": "S3", "region": "us-west-2", "status": "active", "tags": "env:prod,team:ops", "size": "125.7 GB", "storage_size": "125.7 GB"},
    # RDS
    {"name": "users-db", "type": "RDS", "region": "us-east-1", "status": "available", "tags": "env:prod,team:backend", "size": "100 GB", "instance_class": "db.t3.medium", "engine": "postgres", "engine_version": "14.5", "multi_az": True, "storage_gb": "100"},
    {"name": "analytics-db", "type": "RDS", "region": "us-east-1", "status": "available", "tags": "env:prod,team:data", "size": "500 GB", "instance_class": "db.r5.large", "engine": "mysql", "engine_version": "8.0.32", "multi_az": False, "storage_gb": "500"},
    # Lambda
    {"name": "process-orders", "type": "Lambda", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": "512 MB", "runtime": "python3.11", "timeout": 30},
    {"name": "resize-images", "type": "Lambda", "region": "us-east-1", "status": "active", "tags": "env:prod,team:web", "size": "1024 MB", "runtime": "nodejs18.x", "timeout": 60},
    {"name": "send-emails", "type": "Lambda", "region": "eu-west-1", "status": "active", "tags": "env:prod,team:marketing", "size": "256 MB", "runtime": "python3.11", "timeout": 15},
    # ElastiCache
    {"name": "app-cache", "type": "ElastiCache", "region": "us-east-1", "status": "available", "tags": "env:prod,team:backend", "size": "cache.r6g.large", "engine": "redis", "engine_version": "7.0.7", "num_nodes": 2},
    # OpenSearch
    {"name": "search-cluster", "type": "OpenSearch", "region": "us-east-1", "status": "active", "tags": "env:prod,team:search", "size": "3 nodes", "instance_type": "m5.large.search", "instance_count": 3, "engine_version": "OpenSearch_2.5"},
    # SQS
    {"name": "prod-queue", "type": "SQS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    {"name": "retry-queue", "type": "SQS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    # SNS
    {"name": "order-notifications", "type": "SNS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    {"name": "alert-topic", "type": "SNS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:ops", "size": ""},
    # DynamoDB
    {"name": "sessions-table", "type": "DynamoDB", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": "4.2 GB", "item_count": 850000, "billing_mode": "PAY_PER_REQUEST"},
    {"name": "product-catalog", "type": "DynamoDB", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": "18.6 GB", "item_count": 120000, "billing_mode": "PROVISIONED"},
    # ECS
    {"name": "api-service", "type": "ECS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:api", "size": "", "running_tasks_count": 4, "active_services_count": 3},
    {"name": "worker-service", "type": "ECS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:data", "size": "", "running_tasks_count": 2, "active_services_count": 1},
    # EKS
    {"name": "prod-cluster", "type": "EKS", "region": "us-east-1", "status": "active", "tags": "env:prod,team:infra", "size": "5 nodes", "kubernetes_version": "1.28", "node_count": 5, "node_groups": 2},
    # ELB
    {"name": "app-load-balancer", "type": "ELB", "region": "us-east-1", "status": "active", "tags": "env:prod,team:web", "size": "", "lb_type": "application", "scheme": "internet-facing"},
    {"name": "api-nlb", "type": "ELB", "region": "us-east-1", "status": "active", "tags": "env:prod,team:api", "size": "", "lb_type": "network", "scheme": "internal"},
    # VPC
    {"name": "prod-vpc", "type": "VPC", "region": "us-east-1", "status": "available", "tags": "env:prod,team:infra",
     "size": "10.0.0.0/16", "cidr_block": "10.0.0.0/16", "is_default": False,
     "subnet_count": 4, "nat_gateway_count": 2, "igw_count": 1, "ec2_instance_count": 6,
     "subnets": [
         {"id": "subnet-001", "cidr": "10.0.1.0/24", "az": "us-east-1a", "public": True},
         {"id": "subnet-002", "cidr": "10.0.2.0/24", "az": "us-east-1b", "public": True},
         {"id": "subnet-003", "cidr": "10.0.3.0/24", "az": "us-east-1a", "public": False},
         {"id": "subnet-004", "cidr": "10.0.4.0/24", "az": "us-east-1b", "public": False},
     ],
     "nat_gateways": [
         {"id": "nat-001", "state": "available", "subnet_id": "subnet-001"},
         {"id": "nat-002", "state": "available", "subnet_id": "subnet-002"},
     ],
     "internet_gateways": ["igw-001"]},
    {"name": "staging-vpc", "type": "VPC", "region": "us-west-2", "status": "available", "tags": "env:staging,team:infra",
     "size": "10.1.0.0/16", "cidr_block": "10.1.0.0/16", "is_default": False,
     "subnet_count": 2, "nat_gateway_count": 1, "igw_count": 1, "ec2_instance_count": 1,
     "subnets": [
         {"id": "subnet-101", "cidr": "10.1.1.0/24", "az": "us-west-2a", "public": True},
         {"id": "subnet-102", "cidr": "10.1.2.0/24", "az": "us-west-2b", "public": False},
     ],
     "nat_gateways": [
         {"id": "nat-101", "state": "available", "subnet_id": "subnet-101"},
     ],
     "internet_gateways": ["igw-101"]},
    # CloudWatch
    {"name": "app-dashboard", "type": "CloudWatch", "region": "us-east-1", "status": "active", "tags": "env:prod,team:ops", "size": ""},
    {"name": "billing-alarm", "type": "CloudWatch", "region": "us-east-1", "status": "active", "tags": "env:prod,team:finance", "size": ""},
    # MSK (Managed Streaming for Kafka)
    {"name": "prod-kafka-cluster", "type": "MSK", "region": "us-east-1", "status": "active", "tags": "env:prod,team:data", "size": "3 brokers", "broker_count": 3, "broker_instance_type": "kafka.m5.large", "kafka_version": "3.4.0"},
    # AWS Glue
    {"name": "etl-pipeline", "type": "Glue", "region": "us-east-1", "status": "ready", "tags": "env:prod,team:data", "size": "", "worker_type": "G.1X", "max_workers": 10},
    {"name": "data-catalog", "type": "Glue", "region": "us-east-1", "status": "ready", "tags": "env:prod,team:data", "size": "", "worker_type": "Standard", "max_workers": 5},
    # Athena
    {"name": "analytics-workgroup", "type": "Athena", "region": "us-east-1", "status": "active", "tags": "env:prod,team:data", "size": ""},
    # API Gateway
    {"name": "rest-api-prod", "type": "API Gateway", "region": "us-east-1", "status": "active", "tags": "env:prod,team:api", "size": ""},
    {"name": "websocket-api", "type": "API Gateway", "region": "us-east-1", "status": "active", "tags": "env:prod,team:api", "size": ""},
    # Route 53
    {"name": "example.com-zone", "type": "Route 53", "region": "global", "status": "active", "tags": "env:prod,team:infra", "size": ""},
    # CloudFormation
    {"name": "prod-stack", "type": "CloudFormation", "region": "us-east-1", "status": "create_complete", "tags": "env:prod,team:infra", "size": ""},
    {"name": "network-stack", "type": "CloudFormation", "region": "us-east-1", "status": "create_complete", "tags": "env:prod,team:infra", "size": ""},
    # CloudTrail
    {"name": "org-trail", "type": "CloudTrail", "region": "us-east-1", "status": "logging", "tags": "env:prod,team:security", "size": ""},
    # KMS
    {"name": "data-encryption-key", "type": "KMS", "region": "us-east-1", "status": "enabled", "tags": "env:prod,team:security", "size": "256-bit"},
    {"name": "s3-encryption-key", "type": "KMS", "region": "us-east-1", "status": "enabled", "tags": "env:prod,team:security", "size": "256-bit"},
    # Secrets Manager
    {"name": "db-credentials", "type": "Secrets Manager", "region": "us-east-1", "status": "active", "tags": "env:prod,team:security", "size": ""},
    {"name": "api-keys", "type": "Secrets Manager", "region": "us-east-1", "status": "active", "tags": "env:prod,team:security", "size": ""},
    # Cognito
    {"name": "user-pool-prod", "type": "Cognito", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    # ECR
    {"name": "api-service-repo", "type": "ECR", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": "3.2 GB", "repository_uri": "123456789.dkr.ecr.us-east-1.amazonaws.com/api-service-repo", "image_count": 12},
    {"name": "worker-repo", "type": "ECR", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": "1.8 GB", "repository_uri": "123456789.dkr.ecr.us-east-1.amazonaws.com/worker-repo", "image_count": 8},
    # ECR Public
    {"name": "public-base-images", "type": "ECR Public", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": "5.4 GB"},
    # Step Functions
    {"name": "order-workflow", "type": "Step Functions", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    # EFS
    {"name": "shared-storage", "type": "EFS", "region": "us-east-1", "status": "available", "tags": "env:prod,team:ops", "size": "48.3 GB"},
    # SES
    {"name": "transactional-email", "type": "SES", "region": "us-east-1", "status": "active", "tags": "env:prod,team:marketing", "size": ""},
    # WAF
    {"name": "web-acl-prod", "type": "WAF", "region": "us-east-1", "status": "active", "tags": "env:prod,team:security", "size": ""},
    # CodeBuild
    {"name": "api-build-project", "type": "CodeBuild", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": ""},
    # CodePipeline
    {"name": "api-deploy-pipeline", "type": "CodePipeline", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": ""},
    # QuickSight
    {"name": "analytics-dashboard", "type": "QuickSight", "region": "us-east-1", "status": "active", "tags": "env:prod,team:data", "size": ""},
    # Inspector
    {"name": "ec2-assessment", "type": "Inspector", "region": "us-east-1", "status": "active", "tags": "env:prod,team:security", "size": ""},
    # X-Ray
    {"name": "api-tracing", "type": "X-Ray", "region": "us-east-1", "status": "active", "tags": "env:prod,team:devops", "size": ""},
    # Transfer Family
    {"name": "sftp-server", "type": "Transfer Family", "region": "us-east-1", "status": "online", "tags": "env:prod,team:ops", "size": ""},
    # CloudWatch Events / EventBridge
    {"name": "scheduled-jobs-bus", "type": "EventBridge", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},
    # Location Service
    {"name": "delivery-tracker", "type": "Location Service", "region": "us-east-1", "status": "active", "tags": "env:prod,team:backend", "size": ""},

    # ---------------------------------------------------------------------------
    # EC2 sub-resource types
    # ---------------------------------------------------------------------------
    # AMIs
    {"name": "ami-webserver-base", "type": "AMI", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:web", "size": "x86_64",
     "architecture": "x86_64", "platform": "Linux/UNIX", "virtualization_type": "hvm",
     "root_device_type": "ebs", "root_device_name": "/dev/xvda",
     "creation_date": "2024-01-10T12:00:00Z", "owner_id": "123456789012",
     "public": False, "description": "Base Amazon Linux 2 for web servers",
     "hypervisor": "xen", "image_type": "machine"},
    {"name": "ami-api-server", "type": "AMI", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:api", "size": "x86_64",
     "architecture": "x86_64", "platform": "Linux/UNIX", "virtualization_type": "hvm",
     "root_device_type": "ebs", "root_device_name": "/dev/xvda",
     "creation_date": "2024-02-05T08:30:00Z", "owner_id": "123456789012",
     "public": False, "description": "API server base image with pre-installed dependencies",
     "hypervisor": "xen", "image_type": "machine"},
    {"name": "ami-windows-2022", "type": "AMI", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:infra", "size": "x86_64",
     "architecture": "x86_64", "platform": "Windows", "virtualization_type": "hvm",
     "root_device_type": "ebs", "root_device_name": "/dev/sda1",
     "creation_date": "2024-03-01T06:00:00Z", "owner_id": "123456789012",
     "public": False, "description": "Windows Server 2022 base image",
     "hypervisor": "xen", "image_type": "machine"},

    # EBS Volumes
    {"name": "web-server-root", "type": "EBS Volume", "region": "us-east-1a", "status": "in-use",
     "tags": "env:prod,team:web", "size": "50 GiB",
     "volume_type": "gp3", "volume_size_gib": 50,
     "availability_zone": "us-east-1a", "iops": 3000, "throughput": 125,
     "encrypted": True, "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-001",
     "snapshot_id": "snap-001", "attached_to": "i-001", "attached_device": "/dev/xvda",
     "multi_attach": False, "creation_time": "2024-01-15T08:30:00Z"},
    {"name": "api-server-root", "type": "EBS Volume", "region": "us-east-1b", "status": "in-use",
     "tags": "env:prod,team:api", "size": "100 GiB",
     "volume_type": "gp3", "volume_size_gib": 100,
     "availability_zone": "us-east-1b", "iops": 3000, "throughput": 125,
     "encrypted": True, "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-001",
     "snapshot_id": "snap-002", "attached_to": "i-002", "attached_device": "/dev/xvda",
     "multi_attach": False, "creation_time": "2024-02-10T12:00:00Z"},
    {"name": "data-volume", "type": "EBS Volume", "region": "us-east-1a", "status": "available",
     "tags": "env:prod,team:data", "size": "500 GiB",
     "volume_type": "io2", "volume_size_gib": 500,
     "availability_zone": "us-east-1a", "iops": 10000, "throughput": 1000,
     "encrypted": True, "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-002",
     "snapshot_id": "", "attached_to": "", "attached_device": "",
     "multi_attach": False, "creation_time": "2024-03-01T06:00:00Z"},

    # EBS Snapshots
    {"name": "web-root-backup-daily", "type": "EBS Snapshot", "region": "us-east-1", "status": "completed",
     "tags": "env:prod,team:ops", "size": "50 GiB",
     "volume_id": "vol-001", "volume_size_gib": 50,
     "description": "Daily backup of web server root volume",
     "owner_id": "123456789012", "encrypted": True,
     "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-001",
     "start_time": "2024-03-14T02:00:00Z", "progress": "100%"},
    {"name": "api-root-backup-weekly", "type": "EBS Snapshot", "region": "us-east-1", "status": "completed",
     "tags": "env:prod,team:ops", "size": "100 GiB",
     "volume_id": "vol-002", "volume_size_gib": 100,
     "description": "Weekly backup of API server root volume",
     "owner_id": "123456789012", "encrypted": True,
     "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-001",
     "start_time": "2024-03-10T03:00:00Z", "progress": "100%"},
    {"name": "data-volume-snapshot", "type": "EBS Snapshot", "region": "us-east-1", "status": "pending",
     "tags": "env:prod,team:data", "size": "500 GiB",
     "volume_id": "vol-003", "volume_size_gib": 500,
     "description": "On-demand snapshot of data volume",
     "owner_id": "123456789012", "encrypted": True,
     "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/key-002",
     "start_time": "2024-03-15T10:30:00Z", "progress": "45%"},

    # Security Groups
    {"name": "web-sg", "type": "Security Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:web", "size": "",
     "group_id": "sg-001", "description": "Security group for web servers",
     "vpc_id": "vpc-001", "inbound_rules": 3, "outbound_rules": 1},
    {"name": "api-sg", "type": "Security Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:api", "size": "",
     "group_id": "sg-002", "description": "Security group for API servers",
     "vpc_id": "vpc-001", "inbound_rules": 4, "outbound_rules": 1},
    {"name": "db-sg", "type": "Security Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:backend", "size": "",
     "group_id": "sg-003", "description": "Security group for databases",
     "vpc_id": "vpc-001", "inbound_rules": 2, "outbound_rules": 1},
    {"name": "default", "type": "Security Group", "region": "us-east-1", "status": "active",
     "tags": "", "size": "",
     "group_id": "sg-000", "description": "Default VPC security group",
     "vpc_id": "vpc-001", "inbound_rules": 1, "outbound_rules": 1},

    # Elastic IPs
    {"name": "web-server-eip", "type": "Elastic IP", "region": "us-east-1", "status": "in-use",
     "tags": "env:prod,team:web", "size": "",
     "public_ip": "54.210.11.1", "private_ip": "10.0.1.10",
     "allocation_id": "eipalloc-001", "association_id": "eipassoc-001",
     "instance_id": "i-001", "network_interface_id": "eni-001", "domain": "vpc"},
    {"name": "nat-gateway-eip-1", "type": "Elastic IP", "region": "us-east-1", "status": "in-use",
     "tags": "env:prod,team:infra", "size": "",
     "public_ip": "52.2.100.50", "private_ip": "",
     "allocation_id": "eipalloc-002", "association_id": "eipassoc-002",
     "instance_id": "", "network_interface_id": "eni-nat-001", "domain": "vpc"},
    {"name": "spare-eip", "type": "Elastic IP", "region": "us-east-1", "status": "unassociated",
     "tags": "env:prod,team:ops", "size": "",
     "public_ip": "54.80.99.200", "private_ip": "",
     "allocation_id": "eipalloc-003", "association_id": "",
     "instance_id": "", "network_interface_id": "", "domain": "vpc"},

    # Key Pairs
    {"name": "prod-keypair", "type": "Key Pair", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:infra", "size": "",
     "key_pair_id": "key-001", "key_type": "rsa",
     "fingerprint": "1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f",
     "creation_time": "2023-06-01T00:00:00Z"},
    {"name": "staging-keypair", "type": "Key Pair", "region": "us-east-1", "status": "active",
     "tags": "env:staging,team:infra", "size": "",
     "key_pair_id": "key-002", "key_type": "rsa",
     "fingerprint": "2a:62:bf:39:c0:fa:0a:e9:2f:36:6e:48:3e:8e:c9:db",
     "creation_time": "2023-08-15T00:00:00Z"},
    {"name": "dev-ed25519-key", "type": "Key Pair", "region": "us-east-1", "status": "active",
     "tags": "env:dev,team:infra", "size": "",
     "key_pair_id": "key-003", "key_type": "ed25519",
     "fingerprint": "SHA256:OIiEBs/AdSb8UuHpKWMlpkz9LUjWKV9dBR2xkJNz3Q0",
     "creation_time": "2024-01-20T00:00:00Z"},

    # Network Interfaces
    {"name": "web-server-eni", "type": "Network Interface", "region": "us-east-1a", "status": "in-use",
     "tags": "env:prod,team:web", "size": "",
     "interface_type": "interface", "vpc_id": "vpc-001", "subnet_id": "subnet-001",
     "availability_zone": "us-east-1a", "private_ip": "10.0.1.10",
     "private_ips": "10.0.1.10", "public_ip": "54.210.11.1",
     "mac_address": "0e:1d:58:a2:9c:11",
     "security_groups": "web-sg (sg-001), default (sg-000)",
     "source_dest_check": True, "attached_to": "i-001",
     "description": "Primary ENI for web-server-prod"},
    {"name": "api-server-eni", "type": "Network Interface", "region": "us-east-1b", "status": "in-use",
     "tags": "env:prod,team:api", "size": "",
     "interface_type": "interface", "vpc_id": "vpc-001", "subnet_id": "subnet-002",
     "availability_zone": "us-east-1b", "private_ip": "10.0.1.11",
     "private_ips": "10.0.1.11, 10.0.1.50", "public_ip": "",
     "mac_address": "0e:1d:58:a2:9c:22",
     "security_groups": "api-sg (sg-002), default (sg-000)",
     "source_dest_check": True, "attached_to": "i-002",
     "description": "Primary ENI for api-server-1"},

    # Placement Groups
    {"name": "prod-cluster-pg", "type": "Placement Group", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:infra", "size": "",
     "strategy": "cluster", "partition_count": None, "spread_level": ""},
    {"name": "prod-spread-pg", "type": "Placement Group", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:infra", "size": "",
     "strategy": "spread", "partition_count": None, "spread_level": "rack"},
    {"name": "data-partition-pg", "type": "Placement Group", "region": "us-east-1", "status": "available",
     "tags": "env:prod,team:data", "size": "",
     "strategy": "partition", "partition_count": 3, "spread_level": ""},

    # Target Groups
    {"name": "web-tg", "type": "Target Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:web", "size": "",
     "protocol": "HTTP", "port": 80, "target_type": "instance",
     "vpc_id": "vpc-001", "load_balancers": "app-load-balancer",
     "healthy_threshold": 3, "unhealthy_threshold": 3,
     "health_check_path": "/health", "health_check_protocol": "HTTP"},
    {"name": "api-tg", "type": "Target Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:api", "size": "",
     "protocol": "HTTP", "port": 8080, "target_type": "instance",
     "vpc_id": "vpc-001", "load_balancers": "app-load-balancer",
     "healthy_threshold": 2, "unhealthy_threshold": 5,
     "health_check_path": "/api/health", "health_check_protocol": "HTTP"},
    {"name": "api-nlb-tg", "type": "Target Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:api", "size": "",
     "protocol": "TCP", "port": 443, "target_type": "ip",
     "vpc_id": "vpc-001", "load_balancers": "api-nlb",
     "healthy_threshold": 3, "unhealthy_threshold": 3,
     "health_check_path": "", "health_check_protocol": "TCP"},

    # Auto Scaling Groups
    {"name": "web-asg", "type": "Auto Scaling Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:web", "size": "3 instances",
     "min_size": 2, "max_size": 10, "desired_capacity": 3,
     "launch_template": "web-server-lt", "launch_config": "",
     "availability_zones": "us-east-1a, us-east-1b",
     "health_check_type": "ELB", "health_check_grace_period": 300,
     "vpc_zone_identifier": "subnet-001,subnet-002"},
    {"name": "api-asg", "type": "Auto Scaling Group", "region": "us-east-1", "status": "active",
     "tags": "env:prod,team:api", "size": "4 instances",
     "min_size": 2, "max_size": 20, "desired_capacity": 4,
     "launch_template": "api-server-lt", "launch_config": "",
     "availability_zones": "us-east-1a, us-east-1b, us-east-1c",
     "health_check_type": "ELB", "health_check_grace_period": 180,
     "vpc_zone_identifier": "subnet-001,subnet-002,subnet-003"},
]

AWS_RESOURCE_TYPES = [
    "EC2", "S3", "RDS", "Lambda", "ElastiCache", "OpenSearch", "SQS", "SNS",
    "DynamoDB", "ECS", "EKS", "ELB", "VPC", "CloudWatch", "MSK", "Glue",
    "Athena", "API Gateway", "Route 53", "CloudFormation", "CloudTrail", "KMS",
    "Secrets Manager", "Cognito", "ECR", "ECR Public", "Step Functions", "EFS",
    "SES", "WAF", "CodeBuild", "CodePipeline", "QuickSight", "Inspector",
    "X-Ray", "Transfer Family", "EventBridge", "Location Service",
    # EC2 sub-resources
    "AMI", "EBS Volume", "EBS Snapshot", "Security Group", "Elastic IP",
    "Key Pair", "Network Interface", "Placement Group", "Target Group",
    "Auto Scaling Group",
    # VPC sub-resources
    "Subnet", "Route Table", "Internet Gateway", "Egress-only Internet Gateway",
    "DHCP Option Set", "Managed Prefix List", "VPC Endpoint", "VPC Endpoint Service",
    "NAT Gateway", "VPC Peering Connection", "Network ACL",
    "DNS Firewall Rule Group", "DNS Firewall Domain List",
    "Network Firewall", "Firewall Policy", "Network Firewall Rule Group",
    "TLS Inspection Configuration",
    "Customer Gateway", "Virtual Private Gateway", "VPN Connection",
    "Transit Gateway", "Transit Gateway Attachment", "Transit Gateway Route Table",
    "Mirror Session", "Mirror Target", "Mirror Filter",
]

AWS_BILLING_BASE = {
    "EC2": 420.50,
    "S3": 85.20,
    "RDS": 310.75,
    "Lambda": 12.40,
    "ElastiCache": 95.00,
    "OpenSearch": 145.80,
    "SQS": 8.90,
    "SNS": 5.60,
    "DynamoDB": 75.30,
    "ECS": 130.20,
    "EKS": 180.00,
    "ELB": 55.40,
    "VPC": 18.70,
    "CloudWatch": 42.10,
    "MSK": 210.00,
    "Glue": 95.60,
    "Athena": 38.40,
    "API Gateway": 22.80,
    "Route 53": 9.50,
    "CloudFormation": 0.00,
    "CloudTrail": 14.20,
    "KMS": 11.30,
    "Secrets Manager": 8.40,
    "Cognito": 16.90,
    "ECR": 7.80,
    "ECR Public": 2.10,
    "Step Functions": 6.50,
    "EFS": 48.30,
    "SES": 4.20,
    "WAF": 19.60,
    "CodeBuild": 12.00,
    "CodePipeline": 3.00,
    "QuickSight": 24.00,
    "Inspector": 15.50,
    "X-Ray": 5.00,
    "Transfer Family": 36.00,
    "EventBridge": 3.80,
    "Location Service": 11.20,
}

# ---------------------------------------------------------------------------
# GCP mock data
# ---------------------------------------------------------------------------

GCP_RESOURCES = [
    # Compute Engine VMs — full configuration including disk names, NICs, IPs
    {"name": "web-vm-1", "type": "Compute Engine", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:web",
     "machine_type": "n1-standard-4", "zone": "us-central1-a", "cpu_platform": "Intel Broadwell",
     "boot_disk_name": "web-vm-1-disk", "boot_disk_size_gb": 100, "boot_disk_type": "pd-ssd",
     "disk_count": 2, "attached_disks": "web-vm-1-disk,data-vol-1",
     "network": "prod-vpc", "subnetwork": "prod-subnet-central",
     "network_ip": "10.128.0.5", "external_ip": "34.71.90.12",
     "preemptible": False, "deletion_protection": True,
     "service_account": "svc-account-app@myproject.iam.gserviceaccount.com",
     "can_ip_forward": False, "shielded_secure_boot": True,
     "min_cpu_platform": "Intel Broadwell"},
    {"name": "web-vm-2", "type": "Compute Engine", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:web",
     "machine_type": "n1-standard-2", "zone": "us-central1-b", "cpu_platform": "Intel Broadwell",
     "boot_disk_name": "web-vm-2-disk", "boot_disk_size_gb": 50, "boot_disk_type": "pd-ssd",
     "disk_count": 1, "attached_disks": "web-vm-2-disk",
     "network": "prod-vpc", "subnetwork": "prod-subnet-central",
     "network_ip": "10.128.0.6", "external_ip": None,
     "preemptible": True, "deletion_protection": False,
     "service_account": "svc-account-app@myproject.iam.gserviceaccount.com",
     "can_ip_forward": False, "shielded_secure_boot": False,
     "min_cpu_platform": "automatic"},
    {"name": "ml-vm-gpu", "type": "Compute Engine", "region": "us-east1", "status": "TERMINATED", "tags": "env:dev,team:ml",
     "machine_type": "n1-standard-8", "zone": "us-east1-b", "cpu_platform": "Intel Haswell",
     "boot_disk_name": "ml-vm-gpu-disk", "boot_disk_size_gb": 200, "boot_disk_type": "pd-standard",
     "disk_count": 3, "attached_disks": "ml-vm-gpu-disk,ml-data-disk-1,ml-data-disk-2",
     "network": "dev-vpc", "subnetwork": "dev-subnet-east",
     "network_ip": "10.140.0.10", "external_ip": None,
     "preemptible": True, "deletion_protection": False,
     "service_account": "ml-runner@myproject.iam.gserviceaccount.com",
     "can_ip_forward": False, "shielded_secure_boot": False,
     "min_cpu_platform": "Intel Haswell"},
    # Persistent Disks — full disk details
    {"name": "boot-disk-web-vm-1", "type": "Persistent Disk", "region": "us-central1", "status": "READY", "tags": "env:prod,team:web",
     "disk_size_gb": 100, "disk_type": "pd-ssd", "zone": "us-central1-a",
     "source_image": "projects/debian-cloud/global/images/debian-11-bullseye-v20231010",
     "in_use_by": "web-vm-1", "snapshot_schedule_count": 3,
     "encryption": "Google-managed", "physical_block_size_bytes": 4096},
    {"name": "data-disk-ml", "type": "Persistent Disk", "region": "us-east1", "status": "READY", "tags": "env:dev,team:ml",
     "disk_size_gb": 500, "disk_type": "pd-standard", "zone": "us-east1-b",
     "source_image": None, "in_use_by": "ml-vm-gpu",
     "snapshot_schedule_count": 0, "encryption": "Google-managed", "physical_block_size_bytes": 4096},
    # Cloud Storage — comprehensive bucket config
    {"name": "app-storage", "type": "Cloud Storage", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:web",
     "storage_class": "STANDARD", "location_type": "REGIONAL", "versioning": "Enabled",
     "lifecycle_rules": 2, "public_access": "Blocked",
     "uniform_bucket_level_access": True, "retention_policy_days": None,
     "encryption": "Google-managed", "logging": "Enabled",
     "requester_pays": False, "cors_rules": 1},
    {"name": "ml-datasets", "type": "Cloud Storage", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:ml",
     "storage_class": "NEARLINE", "location_type": "REGIONAL", "versioning": "Disabled",
     "lifecycle_rules": 1, "public_access": "Blocked",
     "uniform_bucket_level_access": True, "retention_policy_days": 90,
     "encryption": "Google-managed", "logging": "Disabled",
     "requester_pays": False, "cors_rules": 0},
    # BigQuery — dataset details
    {"name": "analytics-warehouse", "type": "BigQuery", "region": "us", "status": "ACTIVE", "tags": "env:prod,team:data",
     "location": "US", "default_table_expiration_ms": 2592000000, "description": "Main analytics warehouse",
     "dataset_id": "analytics_warehouse", "table_count": 42,
     "kms_key": None, "access_entries": 5,
     "default_partition_expiration_ms": 7776000000,
     "labels_count": 2},
    # Cloud SQL — full instance config
    {"name": "prod-database", "type": "Cloud SQL", "region": "us-central1", "status": "RUNNABLE", "tags": "env:prod,team:backend",
     "database_version": "POSTGRES_14", "tier": "db-n1-standard-4",
     "disk_size_gb": 100, "disk_type": "PD_SSD",
     "availability_type": "REGIONAL", "backup_enabled": True,
     "point_in_time_recovery": True, "connection_name": "myproject:us-central1:prod-database",
     "ip_address": "10.100.0.3", "public_ip": None,
     "maintenance_window": "Sunday 02:00", "deletion_protection": True,
     "database_flags": "max_connections=200"},
    {"name": "staging-database", "type": "Cloud SQL", "region": "us-east1", "status": "RUNNABLE", "tags": "env:staging,team:backend",
     "database_version": "MYSQL_8_0", "tier": "db-n1-standard-2",
     "disk_size_gb": 50, "disk_type": "PD_HDD",
     "availability_type": "ZONAL", "backup_enabled": True,
     "point_in_time_recovery": False, "connection_name": "myproject:us-east1:staging-database",
     "ip_address": "10.140.0.4", "public_ip": None,
     "maintenance_window": "Saturday 03:00", "deletion_protection": False,
     "database_flags": "slow_query_log=ON"},
    # GKE — full cluster config
    {"name": "app-cluster", "type": "GKE", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:infra",
     "current_master_version": "1.28.3-gke.1", "node_count": 3,
     "node_machine_type": "e2-standard-4", "network": "prod-vpc",
     "subnetwork": "prod-subnet-central",
     "node_disk_size_gb": 100, "node_disk_type": "pd-standard",
     "node_image_type": "COS_CONTAINERD", "node_pool_count": 2,
     "autopilot": False, "private_cluster": True,
     "release_channel": "REGULAR", "services_ipv4_cidr": "10.64.0.0/20",
     "cluster_ipv4_cidr": "10.60.0.0/14",
     "logging_service": "logging.googleapis.com/kubernetes",
     "monitoring_service": "monitoring.googleapis.com/kubernetes"},
    # Cloud Functions
    {"name": "trigger-pipeline", "type": "Cloud Functions", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:data",
     "runtime": "python310", "available_memory_mb": 256, "entry_point": "handle_event", "trigger_type": "HTTP",
     "timeout": "60s", "min_instances": 0, "max_instances": 5,
     "service_account": "trigger-sa@myproject.iam.gserviceaccount.com",
     "ingress_settings": "ALLOW_ALL", "vpc_connector": None,
     "build_worker_pool": None, "source_archive": "gs://myproject-source/trigger-pipeline.zip"},
    # Pub/Sub
    {"name": "event-bus", "type": "Pub/Sub", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:backend",
     "message_retention_duration": "604800s", "subscription_count": 3,
     "kms_key": None, "message_storage_policy": "US",
     "schema": None, "labels_count": 2},
    # Cloud CDN
    {"name": "cdn-backend", "type": "Cloud CDN", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:web",
     "cache_mode": "CACHE_ALL_STATIC", "protocol": "HTTPS",
     "negative_caching": True, "signed_url_key_count": 1,
     "cdn_policy_max_ttl": 86400, "cdn_policy_default_ttl": 3600,
     "compression_mode": "AUTOMATIC"},
    # Cloud Run
    {"name": "api-service", "type": "Cloud Run", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:api",
     "cpu": "1000m", "memory": "512Mi", "max_instances": 10,
     "container_image": "gcr.io/myproject/api-service:v2",
     "min_instances": 1, "service_account": "api-run-sa@myproject.iam.gserviceaccount.com",
     "port": 8080, "concurrency": 80, "timeout": "300s",
     "ingress": "INGRESS_TRAFFIC_ALL", "vpc_connector": "projects/myproject/locations/us-central1/connectors/vpc-con",
     "env_var_count": 5, "url": "https://api-service-xyz-uc.a.run.app"},
    # Cloud Memorystore Redis
    {"name": "app-cache", "type": "Cloud Memorystore", "region": "us-central1", "status": "READY", "tags": "env:prod,team:backend",
     "tier": "STANDARD_HA", "memory_size_gb": 4, "redis_version": "REDIS_7_0",
     "host": "10.50.0.3", "port": 6379,
     "network": "prod-vpc", "auth_enabled": True,
     "transit_encryption_mode": "SERVER_AUTHENTICATION",
     "connect_mode": "PRIVATE_SERVICE_ACCESS",
     "read_replicas_mode": "READ_REPLICAS_ENABLED", "replica_count": 1,
     "maintenance_day": "TUESDAY", "maintenance_hour": 2},
    # Cloud Spanner
    {"name": "analytics-spanner", "type": "Cloud Spanner", "region": "us-central1", "status": "READY", "tags": "env:prod,team:data",
     "node_count": 1, "config": "regional-us-central1",
     "processing_units": 1000, "database_count": 2,
     "display_name": "Analytics Spanner", "backup_count": 5,
     "default_backup_schedule_type": "AUTOMATIC"},
    # Firestore
    {"name": "prod-firestore", "type": "Firestore", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:backend",
     "type_detail": "FIRESTORE_NATIVE", "location_id": "us-central1",
     "concurrency_mode": "OPTIMISTIC", "app_engine_integration": "DISABLED",
     "point_in_time_recovery": "POINT_IN_TIME_RECOVERY_ENABLED",
     "delete_protection": "DELETE_PROTECTION_ENABLED"},
    # Cloud KMS
    {"name": "data-encryption-key", "type": "Cloud KMS", "region": "global", "status": "ENABLED", "tags": "env:prod,team:security",
     "purpose": "ENCRYPT_DECRYPT", "algorithm": "GOOGLE_SYMMETRIC_ENCRYPTION",
     "key_ring": "prod-keyring", "rotation_period": "7776000s",
     "next_rotation_time": "2024-04-15", "version_count": 3,
     "protection_level": "SOFTWARE",
     "destroy_scheduled_duration": "86400s"},
    # Secret Manager
    {"name": "db-credentials", "type": "Secret Manager", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:security",
     "replication": "AUTOMATIC", "version_count": 3,
     "rotation_period": None, "expire_time": None,
     "topics": None, "etag": "\"abc123\""},
    # Dataflow
    {"name": "etl-job", "type": "Dataflow", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:data",
     "job_type": "JOB_TYPE_STREAMING", "sdk_version": "2.50.0", "worker_count": 4,
     "max_workers": 20, "worker_machine_type": "n1-standard-4",
     "network": "prod-vpc", "subnetwork": "prod-subnet-central",
     "temp_location": "gs://myproject-temp/dataflow",
     "service_account": "dataflow-sa@myproject.iam.gserviceaccount.com"},
    # Dataproc
    {"name": "spark-cluster", "type": "Dataproc", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:data",
     "master_machine_type": "n1-standard-4", "num_workers": 5,
     "software_version": "2.1-debian11",
     "worker_machine_type": "n1-standard-4", "worker_disk_gb": 500,
     "master_disk_gb": 100, "preemptible_workers": 2,
     "network": "prod-vpc", "internal_ip_only": True,
     "component_gateway": True, "idle_delete_ttl": "1800s"},
    # Cloud DNS
    {"name": "prod-zone", "type": "Cloud DNS", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:infra",
     "dns_name": "prod.example.com.", "visibility": "public",
     "record_set_count": 15, "name_servers": "ns-cloud-a1.googledomains.com",
     "dnssec": "ON", "log_dns_queries": True},
    # App Engine
    {"name": "prod-app", "type": "App Engine", "region": "us-central1", "status": "SERVING", "tags": "env:prod,team:web",
     "runtime": "python311", "env": "standard",
     "serving_status": "SERVING", "instance_class": "F2",
     "automatic_scaling_min_instances": 1, "automatic_scaling_max_instances": 10,
     "inbound_services": "INBOUND_SERVICE_MAIL"},
    # Vertex AI
    {"name": "ml-models", "type": "Vertex AI", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:ml",
     "model_type": "custom-trained", "framework": "tensorflow",
     "artifact_uri": "gs://myproject-models/ml-models",
     "schema_title": "google.VertexDataset", "version_count": 4,
     "deployment_count": 2, "training_pipeline": "projects/myproject/locations/us-central1/trainingPipelines/123"},
    # Artifact Registry
    {"name": "container-images", "type": "Artifact Registry", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:devops",
     "format": "DOCKER", "image_count": 12,
     "size_bytes": 5368709120, "kms_key": None,
     "cleanup_policy_count": 2, "immutable_tags": False,
     "vulnerability_scanning": "AUTOMATIC"},
    # Cloud Build
    {"name": "api-build", "type": "Cloud Build", "region": "global", "status": "SUCCESS", "tags": "env:prod,team:devops",
     "machine_type": "N1_HIGHCPU_8", "timeout": "600s",
     "log_bucket": "gs://myproject_cloudbuild/logs",
     "service_account": "cloudbuild@myproject.iam.gserviceaccount.com",
     "worker_pool": None, "substitution_count": 3},
    # Service Account
    {"name": "svc-account-app", "type": "Service Account", "region": "global", "status": "ENABLED", "tags": "env:prod,team:security",
     "email": "svc-account-app@myproject.iam.gserviceaccount.com",
     "description": "Main application service account",
     "oauth2_client_id": "115818724",
     "key_count": 2, "disabled": False},
    # VPC Network
    {"name": "prod-vpc", "type": "VPC Network", "region": "global", "status": "READY", "tags": "env:prod,team:infra",
     "auto_create_subnetworks": False, "routing_mode": "REGIONAL",
     "subnet_count": 4, "peering_count": 1,
     "mtu": 1460, "internal_ipv6": False,
     "firewall_rule_count": 8, "route_count": 5},
    # Firewall Rule
    {"name": "web-fw-rule", "type": "Firewall Rule", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:infra",
     "direction": "INGRESS", "priority": 1000, "protocol": "tcp",
     "source_ranges": "0.0.0.0/0", "destination_ranges": None,
     "target_tags": "web-server", "ports": "80,443",
     "disabled": False, "log_config": "INCLUDE_ALL_METADATA"},
    # Load Balancer
    {"name": "frontend-lb", "type": "Load Balancer", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:web",
     "load_balancing_scheme": "EXTERNAL", "protocol": "HTTPS",
     "ip_address": "34.120.45.67", "port_range": "443",
     "backend_service": "web-backend-svc", "ssl_certificates": "prod-ssl-cert",
     "network_tier": "PREMIUM"},
    # IP Address
    {"name": "prod-external-ip", "type": "IP Address", "region": "us-central1", "status": "IN_USE", "tags": "env:prod,team:infra",
     "address_type": "EXTERNAL", "ip_version": "IPV4",
     "address": "34.120.45.67", "network_tier": "PREMIUM",
     "prefix_length": None, "in_use_by": "frontend-lb"},
    # Cloud Composer
    {"name": "pipeline-orchestrator", "type": "Cloud Composer", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:data",
     "airflow_version": "2.6.3", "environment_size": "ENVIRONMENT_SIZE_MEDIUM",
     "python_version": "3", "gke_cluster": "projects/myproject/locations/us-central1/clusters/composer-cluster",
     "dag_gcs_prefix": "gs://us-central1-pipeline-bucket/dags",
     "node_count": 3, "scheduler_count": 1,
     "web_server_network_access_control": "allUsers"},
    # Cloud Scheduler
    {"name": "prod-scheduler", "type": "Cloud Scheduler", "region": "us-central1", "status": "ENABLED", "tags": "env:prod,team:backend",
     "schedule": "0 */6 * * *", "timezone": "UTC",
     "target_type": "HTTP", "http_method": "POST",
     "uri": "https://api-service-xyz-uc.a.run.app/jobs/run",
     "retry_count": 3, "attempt_deadline": "180s"},
    # Cloud Tasks
    {"name": "task-queue", "type": "Cloud Tasks", "region": "us-central1", "status": "RUNNING", "tags": "env:prod,team:backend",
     "max_dispatches_per_second": 500, "max_concurrent_dispatches": 1000,
     "max_attempts": 5, "max_retry_duration": "3600s",
     "min_backoff": "0.100s", "max_backoff": "3600s",
     "max_doublings": 16, "task_count": 124},
    # Cloud Monitoring
    {"name": "billing-alert", "type": "Cloud Monitoring", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:ops",
     "condition_count": 2, "notification_channels": 1,
     "combiner": "OR", "alert_strategy": "AUTO",
     "severity": "WARNING",
     "documentation_content": "Billing threshold exceeded"},
    # Cloud Logging
    {"name": "audit-log-sink", "type": "Cloud Logging", "region": "global", "status": "ACTIVE", "tags": "env:prod,team:security",
     "destination": "bigquery.googleapis.com/projects/myproject/datasets/audit_logs",
     "filter": "logName:cloudaudit.googleapis.com", "sink_type": "bigquery",
     "include_children": True, "writer_identity": "serviceAccount:p12345@gcp-sa-logging.iam.gserviceaccount.com"},
    # API Gateway
    {"name": "api-gw", "type": "API Gateway", "region": "us-central1", "status": "ACTIVE", "tags": "env:prod,team:api",
     "default_hostname": "api-gw-xyz.uc.gateway.dev",
     "managed_service": "api-gw-xyz.apigateway.myproject.cloud.goog",
     "config_id": "api-gw-config-v3",
     "labels_count": 2},
    # Filestore
    {"name": "shared-filestore", "type": "Filestore", "region": "us-central1", "status": "READY", "tags": "env:prod,team:ops",
     "tier": "STANDARD", "capacity_gb": 1024, "file_shares": 1,
     "share_name": "shared_data", "network": "prod-vpc",
     "ip_addresses": "10.200.0.2", "modes": "MODE_IPV4",
     "snapshot_count": 4, "kms_key": None},
    # Cloud Bigtable
    {"name": "bigtable-main", "type": "Cloud Bigtable", "region": "us-central1", "status": "READY", "tags": "env:prod,team:data",
     "cluster_count": 1, "storage_type": "SSD",
     "node_count": 3, "cluster_id": "bigtable-main-c1",
     "kms_key": None, "deletion_protection": True,
     "table_count": 8, "backup_count": 5},
]

GCP_RESOURCE_TYPES = [
    "Compute Engine", "Persistent Disk", "Cloud Storage", "BigQuery", "Cloud SQL",
    "GKE", "Cloud Functions", "Pub/Sub", "Cloud CDN", "Cloud Run",
    "Cloud Memorystore", "Cloud Spanner", "Firestore", "Cloud KMS", "Secret Manager",
    "Dataflow", "Dataproc", "Cloud DNS", "App Engine", "Vertex AI",
    "Artifact Registry", "Cloud Build", "Service Account", "VPC Network",
    "Firewall Rule", "Load Balancer", "IP Address", "Cloud Composer",
    "Cloud Scheduler", "Cloud Tasks", "Cloud Monitoring", "Cloud Logging",
    "API Gateway", "Filestore", "Cloud Bigtable",
]

GCP_BILLING_BASE = {
    "Compute Engine": 380.00,
    "Persistent Disk": 45.00,
    "Cloud Storage": 65.40,
    "BigQuery": 220.10,
    "Cloud SQL": 290.00,
    "GKE": 175.50,
    "Cloud Functions": 9.80,
    "Pub/Sub": 14.20,
    "Cloud CDN": 42.60,
    "Cloud Run": 25.00,
    "Cloud Memorystore": 95.00,
    "Cloud Spanner": 280.00,
    "Firestore": 35.00,
    "Cloud KMS": 12.00,
    "Secret Manager": 3.50,
    "Dataflow": 85.00,
    "Dataproc": 120.00,
    "Cloud DNS": 8.50,
    "App Engine": 45.00,
    "Vertex AI": 250.00,
    "Artifact Registry": 15.00,
    "Cloud Build": 18.00,
    "Cloud Composer": 140.00,
    "Cloud Scheduler": 2.00,
    "Cloud Tasks": 3.00,
    "Cloud Monitoring": 15.00,
    "Cloud Logging": 25.00,
    "API Gateway": 20.00,
    "Filestore": 65.00,
    "Cloud Bigtable": 180.00,
    "Load Balancer": 38.00,
    "IP Address": 7.20,
    "VPC Network": 5.00,
    "Vertex AI Notebooks": 60.00,
    "Dataform": 5.00,
    "Dataplex": 30.00,
    "Cloud Data Fusion": 90.00,
    "AlloyDB": 310.00,
    "Cloud Armor": 25.00,
    "VPN Gateway": 20.00,
    "Interconnect": 150.00,
    "Cloud Router": 10.00,
    "Cloud Source Repositories": 5.00,
    "Cloud Workflows": 3.00,
    "Certificate Manager": 4.00,
}

# ---------------------------------------------------------------------------
# Azure mock data
# ---------------------------------------------------------------------------

AZURE_RESOURCES = [
    {"name": "prod-web-vm", "type": "Virtual Machines", "region": "East US", "status": "Running", "tags": "env:prod,team:web"},
    {"name": "staging-vm", "type": "Virtual Machines", "region": "West US", "status": "Stopped", "tags": "env:staging,team:web"},
    {"name": "prod-storage", "type": "Storage Accounts", "region": "East US", "status": "Available", "tags": "env:prod,team:ops"},
    {"name": "backup-storage", "type": "Storage Accounts", "region": "West Europe", "status": "Available", "tags": "env:prod,team:ops"},
    {"name": "app-sql-db", "type": "SQL Database", "region": "East US", "status": "Online", "tags": "env:prod,team:backend"},
    {"name": "analytics-sql", "type": "SQL Database", "region": "East US", "status": "Online", "tags": "env:prod,team:data"},
    {"name": "app-func", "type": "Azure Functions", "region": "East US", "status": "Running", "tags": "env:prod,team:backend"},
    {"name": "aks-cluster", "type": "AKS", "region": "East US", "status": "Running", "tags": "env:prod,team:infra"},
    {"name": "cosmos-main", "type": "Cosmos DB", "region": "East US", "status": "Online", "tags": "env:prod,team:backend"},
    {"name": "redis-cache", "type": "Azure Cache for Redis", "region": "East US", "status": "Running", "tags": "env:prod,team:backend"},
    {"name": "service-bus", "type": "Service Bus", "region": "East US", "status": "Active", "tags": "env:prod,team:backend"},
    {"name": "app-insights", "type": "Application Insights", "region": "East US", "status": "Active", "tags": "env:prod,team:devops"},
]

AZURE_RESOURCE_TYPES = [
    "Virtual Machines", "Storage Accounts", "SQL Database",
    "Azure Functions", "AKS", "Cosmos DB", "Azure Cache for Redis", "Service Bus", "Application Insights"
]

AZURE_BILLING_BASE = {
    "Virtual Machines": 510.00,
    "Storage Accounts": 45.80,
    "SQL Database": 360.50,
    "Azure Functions": 7.20,
    "AKS": 195.00,
    "Cosmos DB": 275.30,
    "Azure Cache for Redis": 88.40,
    "Service Bus": 11.60,
    "Application Insights": 18.90,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROVIDER_MAP = {
    "aws": (AWS_RESOURCES, AWS_RESOURCE_TYPES, AWS_BILLING_BASE),
    "gcp": (GCP_RESOURCES, GCP_RESOURCE_TYPES, GCP_BILLING_BASE),
    "azure": (AZURE_RESOURCES, AZURE_RESOURCE_TYPES, AZURE_BILLING_BASE),
}


def _make_seed(*parts: str) -> int:
    """Return a stable integer seed from an arbitrary set of string parts.

    Uses MD5 (not for security – purely for determinism) so that the same
    provider/date range always produces the same random sequence regardless of
    Python's hash-randomisation setting.
    """
    key = "|".join(parts)
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


def get_resources(provider: str) -> list[dict]:
    resources, _, _ = _PROVIDER_MAP[provider.lower()]
    return [dict(r, id=f"{provider}-{i+1:03d}") for i, r in enumerate(resources)]


def get_resource_types(provider: str) -> list[str]:
    _, types, _ = _PROVIDER_MAP[provider.lower()]
    return types


def _daily_costs(base: float, start: date, end: date, seed: int) -> list[dict]:
    """Generate deterministic, realistic daily cost data between start and end.

    The same (base, start, end, seed) arguments always produce identical output.
    """
    rng = random.Random(seed)
    result = []
    running = base
    current = start
    while current <= end:
        running = max(0.0, running + rng.uniform(-base * 0.05, base * 0.05))
        result.append({"date": current.isoformat(), "cost": round(running / 30, 2)})
        current += timedelta(days=1)
    return result


def get_overall_billing(provider: str, start: date, end: date) -> dict:
    _, _, billing_base = _PROVIDER_MAP[provider.lower()]
    total_base = sum(billing_base.values())
    seed = _make_seed(provider, start.isoformat(), end.isoformat())
    daily = _daily_costs(total_base, start, end, seed)
    total = round(sum(d["cost"] for d in daily), 2)

    # Derive each service's cost proportionally from the actual total so that
    # the breakdown bars always add up to exactly the displayed total.
    breakdown = [
        {"service": svc, "cost": round(total * cost / total_base, 2)}
        for svc, cost in billing_base.items()
    ]
    breakdown.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "total": total,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": daily,
        "breakdown": breakdown,
    }


def get_billing_by_resource_type(provider: str, resource_type: str, start: date, end: date) -> dict:
    _, _, billing_base = _PROVIDER_MAP[provider.lower()]
    base = billing_base.get(resource_type, 50.0)
    seed = _make_seed(provider, resource_type, start.isoformat(), end.isoformat())
    daily = _daily_costs(base, start, end, seed)
    days = (end - start).days + 1
    total = round(sum(d["cost"] for d in daily), 2)
    return {
        "resource_type": resource_type,
        "total": total,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": daily,
        "average_daily": round(total / max(days, 1), 2),
    }
