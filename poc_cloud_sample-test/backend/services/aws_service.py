"""AWS service – attempts real boto3 calls, falls back to mock data on error."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from . import mock_service
from .vertexai_suggestions import generate_vertexai_suggestions

# Mapping from our simplified resource type names to AWS Cost Explorer SERVICE dimension names.
_CE_SERVICE_MAP: dict[str, str] = {
    "EC2": "Amazon Elastic Compute Cloud - Compute",
    "S3": "Amazon Simple Storage Service",
    "RDS": "Amazon Relational Database Service",
    "Lambda": "AWS Lambda",
    "ElastiCache": "Amazon ElastiCache",
    "OpenSearch": "Amazon OpenSearch Service",
    "SQS": "Amazon Simple Queue Service",
    "SNS": "Amazon Simple Notification Service",
    "DynamoDB": "Amazon DynamoDB",
    "ECS": "Amazon Elastic Container Service",
    "EKS": "Amazon Elastic Kubernetes Service",
    "ELB": "AWS Elastic Load Balancing",
    "VPC": "Amazon Virtual Private Cloud",
    "CloudWatch": "Amazon CloudWatch",
    "MSK": "Amazon Managed Streaming for Apache Kafka",
    "Glue": "AWS Glue",
    "Athena": "Amazon Athena",
    "API Gateway": "Amazon API Gateway",
    "Route 53": "Amazon Route 53",
    "CloudFormation": "AWS CloudFormation",
    "CloudTrail": "AWS CloudTrail",
    "KMS": "AWS Key Management Service",
    "Secrets Manager": "AWS Secrets Manager",
    "Cognito": "Amazon Cognito",
    "ECR": "Amazon EC2 Container Registry (Amazon ECR)",
    "ECR Public": "Amazon ECR Public",
    "Step Functions": "AWS Step Functions",
    "EFS": "Amazon Elastic File System",
    "SES": "Amazon Simple Email Service",
    "WAF": "AWS WAF",
    "CodeBuild": "AWS CodeBuild",
    "CodePipeline": "AWS CodePipeline",
    "QuickSight": "Amazon QuickSight",
    "Inspector": "Amazon Inspector",
    "X-Ray": "AWS X-Ray",
    "Transfer Family": "AWS Transfer Family",
    "EventBridge": "Amazon EventBridge",
    "Location Service": "Amazon Location Service",
}


def _make_clients(credentials: dict):
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    # Increase connection pool so concurrent threads don't stall waiting for a slot.
    config = Config(
        max_pool_connections=50,
        connect_timeout=5,
        read_timeout=10,
        retries={"max_attempts": 2},
    )
    session = boto3.Session(
        aws_access_key_id=credentials.get("access_key_id"),
        aws_secret_access_key=credentials.get("secret_access_key"),
        region_name=credentials.get("region", "us-east-1"),
    )
    return session, config



def _fetch_type(session, resource_type: str, region: str, config=None) -> list[dict]:  # noqa: C901
    """Fetch resources for a single AWS resource type. Returns [] on any error."""
    def _client(service, region_name=None):
        kwargs = {"region_name": region_name or region}
        if config is not None:
            kwargs["config"] = config
        return session.client(service, **kwargs)

    try:
        if resource_type == "EC2":
            ec2 = _client("ec2")
            items = []
            for reservation in ec2.describe_instances().get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    name = next(
                        (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                        inst["InstanceId"],
                    )
                    instance_type = inst.get("InstanceType", "")
                    placement = inst.get("Placement", {})
                    availability_zone = placement.get("AvailabilityZone", region)
                    cpu_opts = inst.get("CpuOptions", {})
                    security_groups = ", ".join(
                        f"{sg['GroupName']} ({sg['GroupId']})"
                        for sg in inst.get("SecurityGroups", [])
                    )
                    iam_profile = inst.get("IamInstanceProfile", {})
                    iam_role = iam_profile.get("Arn", "").split("/")[-1] if iam_profile else ""
                    block_devices = ", ".join(
                        f"{bd['DeviceName']} ({bd['Ebs']['VolumeId']})"
                        for bd in inst.get("BlockDeviceMappings", [])
                        if "Ebs" in bd
                    )
                    launch_time = inst.get("LaunchTime")
                    launch_time_str = launch_time.strftime("%Y-%m-%d %H:%M:%S UTC") if launch_time else ""
                    items.append({
                        "id": inst["InstanceId"],
                        "name": name,
                        "type": "EC2",
                        "region": availability_zone,
                        "status": inst["State"]["Name"],
                        "size": instance_type,
                        # --- Core ---
                        "instance_type": instance_type,
                        "ami_id": inst.get("ImageId", ""),
                        "launch_time": launch_time_str,
                        "platform": inst.get("Platform", "Linux/UNIX"),
                        "architecture": inst.get("Architecture", ""),
                        # --- Network ---
                        "availability_zone": availability_zone,
                        "vpc_id": inst.get("VpcId", ""),
                        "subnet_id": inst.get("SubnetId", ""),
                        "private_ip": inst.get("PrivateIpAddress", ""),
                        "private_dns_name": inst.get("PrivateDnsName", ""),
                        "public_ip": inst.get("PublicIpAddress", ""),
                        "public_dns_name": inst.get("PublicDnsName", ""),
                        "security_groups": security_groups,
                        "source_dest_check": inst.get("SourceDestCheck"),
                        # --- Storage ---
                        "root_device_type": inst.get("RootDeviceType", ""),
                        "root_device_name": inst.get("RootDeviceName", ""),
                        "ebs_optimized": inst.get("EbsOptimized"),
                        "block_devices": block_devices,
                        # --- Security ---
                        "key_name": inst.get("KeyName", ""),
                        "iam_role": iam_role,
                        "tenancy": placement.get("Tenancy", "default"),
                        # --- Performance & Monitoring ---
                        "monitoring_state": inst.get("Monitoring", {}).get("State", ""),
                        "cpu_core_count": cpu_opts.get("CoreCount"),
                        "cpu_threads_per_core": cpu_opts.get("ThreadsPerCore"),
                        "hypervisor": inst.get("Hypervisor", ""),
                        "virtualization_type": inst.get("VirtualizationType", ""),
                        # --- State ---
                        "state_transition_reason": inst.get("StateTransitionReason", ""),
                        "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in inst.get("Tags", [])),
                    })
            return items

        if resource_type == "VPC":
            ec2 = _client("ec2")
            vpcs = ec2.describe_vpcs().get("Vpcs", [])
            all_subnets = ec2.describe_subnets().get("Subnets", [])
            all_nat_gws = ec2.describe_nat_gateways().get("NatGateways", [])
            all_igws = ec2.describe_internet_gateways().get("InternetGateways", [])
            vpc_instance_counts: dict[str, int] = {}
            for reservation in ec2.describe_instances().get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    vid = inst.get("VpcId", "")
                    if vid:
                        vpc_instance_counts[vid] = vpc_instance_counts.get(vid, 0) + 1
            items = []
            for vpc in vpcs:
                vpc_id = vpc["VpcId"]
                name = next((t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"), vpc_id)
                subnets = [
                    {
                        "id": s["SubnetId"],
                        "cidr": s["CidrBlock"],
                        "az": s["AvailabilityZone"],
                        "public": s.get("MapPublicIpOnLaunch", False),
                    }
                    for s in all_subnets if s.get("VpcId") == vpc_id
                ]
                nat_gateways = [
                    {
                        "id": n["NatGatewayId"],
                        "state": n.get("State", "unknown"),
                        "subnet_id": n.get("SubnetId", ""),
                    }
                    for n in all_nat_gws
                    if n.get("VpcId") == vpc_id and n.get("State") != "deleted"
                ]
                igws = [
                    igw["InternetGatewayId"]
                    for igw in all_igws
                    if any(a.get("VpcId") == vpc_id for a in igw.get("Attachments", []))
                ]
                items.append({
                    "id": vpc_id, "name": name, "type": "VPC", "region": region,
                    "status": vpc.get("State", "available"),
                    "size": vpc.get("CidrBlock", ""),
                    "cidr_block": vpc.get("CidrBlock", ""),
                    "is_default": vpc.get("IsDefault", False),
                    "subnet_count": len(subnets),
                    "nat_gateway_count": len(nat_gateways),
                    "igw_count": len(igws),
                    "ec2_instance_count": vpc_instance_counts.get(vpc_id, 0),
                    "subnets": subnets,
                    "nat_gateways": nat_gateways,
                    "internet_gateways": igws,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in vpc.get("Tags", [])),
                })
            return items

        if resource_type == "S3":
            from datetime import datetime, timedelta  # noqa: PLC0415
            s3 = _client("s3")
            cw = _client("cloudwatch", "us-east-1")
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=2)
            buckets = s3.list_buckets().get("Buckets", [])

            def _get_bucket_size(bucket_name: str) -> str:
                try:
                    metrics = cw.get_metric_statistics(
                        Namespace="AWS/S3",
                        MetricName="BucketSizeBytes",
                        Dimensions=[
                            {"Name": "BucketName", "Value": bucket_name},
                            {"Name": "StorageType", "Value": "StandardStorage"},
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=["Average"],
                    )
                    if metrics.get("Datapoints"):
                        latest = sorted(metrics["Datapoints"], key=lambda x: x["Timestamp"])[-1]
                        size_bytes = latest["Average"]
                        if size_bytes >= 1024 ** 4:
                            return f"{size_bytes / 1024 ** 4:.2f} TB"
                        if size_bytes >= 1024 ** 3:
                            return f"{size_bytes / 1024 ** 3:.2f} GB"
                        return f"{size_bytes / 1024 ** 2:.2f} MB"
                except Exception:
                    pass
                return ""

            bucket_names = [b["Name"] for b in buckets]
            if bucket_names:
                with ThreadPoolExecutor(max_workers=min(len(bucket_names), 20)) as pool:
                    sizes = list(pool.map(_get_bucket_size, bucket_names))
            else:
                sizes = []
            return [
                {
                    "id": b["Name"], "name": b["Name"], "type": "S3",
                    "region": "global", "status": "active",
                    "size": sz, "storage_size": sz, "tags": "",
                }
                for b, sz in zip(buckets, sizes)
            ]

        if resource_type == "RDS":
            rds = _client("rds")
            return [
                {"id": db["DBInstanceIdentifier"], "name": db["DBInstanceIdentifier"], "type": "RDS",
                 "region": region, "status": db.get("DBInstanceStatus", "unknown"),
                 "size": f"{db.get('AllocatedStorage', '')} GB" if db.get("AllocatedStorage") else "",
                 "instance_class": db.get("DBInstanceClass", ""),
                 "engine": db.get("Engine", ""),
                 "engine_version": db.get("EngineVersion", ""),
                 "multi_az": db.get("MultiAZ", False),
                 "storage_gb": str(db.get("AllocatedStorage", "")) if db.get("AllocatedStorage") else "",
                 "tags": ""}
                for db in rds.describe_db_instances().get("DBInstances", [])
            ]

        if resource_type == "Lambda":
            lmb = _client("lambda")
            items = []
            for page in lmb.get_paginator("list_functions").paginate():
                for fn in page.get("Functions", []):
                    memory = fn.get("MemorySize", "")
                    items.append({"id": fn["FunctionArn"], "name": fn["FunctionName"], "type": "Lambda",
                                  "region": region, "status": "active",
                                  "size": f"{memory} MB" if memory else "",
                                  "runtime": fn.get("Runtime", ""),
                                  "timeout": fn.get("Timeout", ""),
                                  "tags": ""})
            return items

        if resource_type == "ElastiCache":
            ec = _client("elasticache")
            return [
                {"id": c["CacheClusterId"], "name": c["CacheClusterId"], "type": "ElastiCache",
                 "region": region, "status": c.get("CacheClusterStatus", "unknown"),
                 "size": c.get("CacheNodeType", ""),
                 "engine": c.get("Engine", ""),
                 "engine_version": c.get("EngineVersion", ""),
                 "num_nodes": c.get("NumCacheNodes", 0),
                 "tags": ""}
                for c in ec.describe_cache_clusters().get("CacheClusters", [])
            ]

        if resource_type == "OpenSearch":
            oss = _client("opensearch")
            items = []
            for d in oss.list_domain_names().get("DomainNames", []):
                domain_name = d["DomainName"]
                try:
                    domain = oss.describe_domain(DomainName=domain_name)["DomainStatus"]
                    cluster_cfg = domain.get("ClusterConfig", {})
                    instance_type = cluster_cfg.get("InstanceType", "")
                    instance_count = cluster_cfg.get("InstanceCount", 0)
                    items.append({
                        "id": domain_name, "name": domain_name, "type": "OpenSearch",
                        "region": region, "status": "active",
                        "size": f"{instance_count} x {instance_type}" if instance_type else str(instance_count),
                        "instance_type": instance_type,
                        "instance_count": instance_count,
                        "engine_version": domain.get("EngineVersion", ""),
                        "tags": "",
                    })
                except Exception:
                    items.append({
                        "id": domain_name, "name": domain_name, "type": "OpenSearch",
                        "region": region, "status": "active", "tags": "",
                    })
            return items

        if resource_type == "SQS":
            sqs = _client("sqs")
            return [
                {"id": url, "name": url.split("/")[-1], "type": "SQS",
                 "region": region, "status": "active", "tags": ""}
                for url in sqs.list_queues().get("QueueUrls", [])
            ]

        if resource_type == "SNS":
            sns = _client("sns")
            return [
                {"id": t["TopicArn"], "name": t["TopicArn"].split(":")[-1], "type": "SNS",
                 "region": region, "status": "active", "tags": ""}
                for t in sns.list_topics().get("Topics", [])
            ]

        if resource_type == "DynamoDB":
            ddb = _client("dynamodb")
            items = []
            for page in ddb.get_paginator("list_tables").paginate():
                for table_name in page.get("TableNames", []):
                    try:
                        tbl = ddb.describe_table(TableName=table_name)["Table"]
                        size_bytes = tbl.get("TableSizeBytes", 0)
                        item_count = tbl.get("ItemCount", 0)
                        if size_bytes >= 1024 ** 3:
                            size_str = f"{size_bytes / 1024 ** 3:.2f} GB"
                        elif size_bytes >= 1024 ** 2:
                            size_str = f"{size_bytes / 1024 ** 2:.2f} MB"
                        elif size_bytes:
                            size_str = f"{size_bytes / 1024:.2f} KB"
                        else:
                            size_str = ""
                        items.append({
                            "id": table_name, "name": table_name, "type": "DynamoDB",
                            "region": region, "status": tbl.get("TableStatus", "active").lower(),
                            "size": size_str,
                            "item_count": item_count,
                            "billing_mode": tbl.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED"),
                            "tags": "",
                        })
                    except Exception:
                        items.append({"id": table_name, "name": table_name, "type": "DynamoDB",
                                      "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "ECS":
            ecs = _client("ecs")
            items = []
            for arn in ecs.list_clusters().get("clusterArns", []):
                cluster_name = arn.split("/")[-1]
                try:
                    details = ecs.describe_clusters(clusters=[arn]).get("clusters", [{}])[0]
                    items.append({
                        "id": arn, "name": cluster_name, "type": "ECS",
                        "region": region, "status": details.get("status", "active").lower(),
                        "running_tasks_count": details.get("runningTasksCount", 0),
                        "active_services_count": details.get("activeServicesCount", 0),
                        "tags": "",
                    })
                except Exception:
                    items.append({"id": arn, "name": cluster_name, "type": "ECS",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "EKS":
            eks = _client("eks")
            items = []
            for cluster_name in eks.list_clusters().get("clusters", []):
                try:
                    cluster = eks.describe_cluster(name=cluster_name)["cluster"]
                    nodegroups = eks.list_nodegroups(clusterName=cluster_name).get("nodegroups", [])
                    total_nodes = 0
                    for ng_name in nodegroups:
                        try:
                            ng = eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)["nodegroup"]
                            total_nodes += ng.get("scalingConfig", {}).get("desiredSize", 0)
                        except Exception:
                            pass
                    items.append({
                        "id": cluster_name, "name": cluster_name, "type": "EKS", "region": region,
                        "status": cluster.get("status", "active").lower(),
                        "size": f"{total_nodes} nodes" if total_nodes else "",
                        "kubernetes_version": cluster.get("version", ""),
                        "node_count": total_nodes,
                        "node_groups": len(nodegroups),
                        "tags": "",
                    })
                except Exception:
                    items.append({"id": cluster_name, "name": cluster_name, "type": "EKS",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "ELB":
            elbv2 = _client("elbv2")
            return [
                {"id": lb["LoadBalancerArn"], "name": lb["LoadBalancerName"], "type": "ELB",
                 "region": region, "status": lb.get("State", {}).get("Code", "unknown"),
                 "lb_type": lb.get("Type", ""),
                 "scheme": lb.get("Scheme", ""),
                 "dns_name": lb.get("DNSName", ""),
                 "tags": ""}
                for lb in elbv2.describe_load_balancers().get("LoadBalancers", [])
            ]

        if resource_type == "CloudWatch":
            cw = _client("cloudwatch")
            items = []
            for page in cw.get_paginator("describe_alarms").paginate():
                for alarm in page.get("MetricAlarms", []):
                    items.append({"id": alarm["AlarmArn"], "name": alarm["AlarmName"], "type": "CloudWatch",
                                  "region": region, "status": alarm.get("StateValue", "unknown").lower(), "tags": ""})
            return items

        if resource_type == "MSK":
            msk = _client("kafka")
            items = []
            for c in msk.list_clusters().get("ClusterInfoList", []):
                broker_info = c.get("BrokerNodeGroupInfo", {})
                broker_count = c.get("NumberOfBrokerNodes", 0)
                instance_type = broker_info.get("InstanceType", "")
                items.append({
                    "id": c["ClusterArn"], "name": c["ClusterName"], "type": "MSK",
                    "region": region, "status": c.get("State", "unknown").lower(),
                    "size": f"{broker_count} brokers" if broker_count else "",
                    "broker_count": broker_count,
                    "broker_instance_type": instance_type,
                    "kafka_version": c.get("CurrentBrokerSoftwareInfo", {}).get("KafkaVersion", ""),
                    "tags": "",
                })
            return items

        if resource_type == "Glue":
            glue = _client("glue")
            items = []
            for page in glue.get_paginator("get_jobs").paginate():
                for job in page.get("Jobs", []):
                    items.append({"id": job["Name"], "name": job["Name"], "type": "Glue",
                                  "region": region, "status": "ready",
                                  "worker_type": job.get("WorkerType", ""),
                                  "max_workers": job.get("MaxCapacity", ""),
                                  "tags": ""})
            return items

        if resource_type == "Athena":
            athena = _client("athena")
            return [
                {"id": wg["Name"], "name": wg["Name"], "type": "Athena",
                 "region": region, "status": wg.get("State", "enabled").lower(), "tags": ""}
                for wg in athena.list_work_groups().get("WorkGroups", [])
            ]

        if resource_type == "API Gateway":
            apigw = _client("apigateway")
            return [
                {"id": api["id"], "name": api["name"], "type": "API Gateway",
                 "region": region, "status": "active", "tags": ""}
                for api in apigw.get_rest_apis().get("items", [])
            ]

        if resource_type == "Route 53":
            r53 = _client("route53")
            return [
                {"id": z["Id"], "name": z["Name"], "type": "Route 53",
                 "region": "global", "status": "active", "tags": ""}
                for z in r53.list_hosted_zones().get("HostedZones", [])
            ]

        if resource_type == "CloudFormation":
            cfn = _client("cloudformation")
            items = []
            for page in cfn.get_paginator("list_stacks").paginate(
                StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE"]
            ):
                for stack in page.get("StackSummaries", []):
                    items.append({"id": stack["StackId"], "name": stack["StackName"], "type": "CloudFormation",
                                  "region": region, "status": stack.get("StackStatus", "unknown").lower(), "tags": ""})
            return items

        if resource_type == "CloudTrail":
            ct = _client("cloudtrail")
            return [
                {"id": t["TrailARN"], "name": t["Name"], "type": "CloudTrail",
                 "region": t.get("HomeRegion", region), "status": "logging", "tags": ""}
                for t in ct.describe_trails().get("trailList", [])
            ]

        if resource_type == "KMS":
            kms = _client("kms")
            items = []
            for page in kms.get_paginator("list_keys").paginate():
                for key in page.get("Keys", []):
                    items.append({"id": key["KeyId"], "name": key["KeyId"], "type": "KMS",
                                  "region": region, "status": "enabled", "tags": ""})
            return items

        if resource_type == "Secrets Manager":
            sm = _client("secretsmanager")
            items = []
            for page in sm.get_paginator("list_secrets").paginate():
                for secret in page.get("SecretList", []):
                    items.append({"id": secret["ARN"], "name": secret["Name"], "type": "Secrets Manager",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "Cognito":
            cognito = _client("cognito-idp")
            items = []
            for page in cognito.get_paginator("list_user_pools").paginate(MaxResults=60):
                for pool in page.get("UserPools", []):
                    items.append({"id": pool["Id"], "name": pool["Name"], "type": "Cognito",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "ECR":
            ecr = _client("ecr")
            repos = []
            for page in ecr.get_paginator("describe_repositories").paginate():
                repos.extend(page.get("repositories", []))

            def _count_images(repo_name: str) -> int:
                try:
                    total = 0
                    for pg in ecr.get_paginator("describe_images").paginate(repositoryName=repo_name):
                        total += len(pg.get("imageDetails", []))
                    return total
                except Exception:
                    return 0

            if repos:
                with ThreadPoolExecutor(max_workers=min(len(repos), 10)) as pool:
                    image_counts = list(pool.map(_count_images, [r["repositoryName"] for r in repos]))
            else:
                image_counts = []
            return [
                {
                    "id": repo["repositoryArn"], "name": repo["repositoryName"], "type": "ECR",
                    "region": region, "status": "active",
                    "repository_uri": repo.get("repositoryUri", ""),
                    "image_count": cnt, "tags": "",
                }
                for repo, cnt in zip(repos, image_counts)
            ]

        if resource_type == "ECR Public":
            ecr_public = _client("ecr-public", "us-east-1")
            items = []
            for page in ecr_public.get_paginator("describe_repositories").paginate():
                for repo in page.get("repositories", []):
                    items.append({"id": repo["repositoryArn"], "name": repo["repositoryName"], "type": "ECR Public",
                                  "region": "us-east-1", "status": "active", "tags": ""})
            return items

        if resource_type == "Step Functions":
            sfn = _client("stepfunctions")
            items = []
            for page in sfn.get_paginator("list_state_machines").paginate():
                for sm in page.get("stateMachines", []):
                    items.append({"id": sm["stateMachineArn"], "name": sm["name"], "type": "Step Functions",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "EFS":
            efs = _client("efs")
            items = []
            for fs in efs.describe_file_systems().get("FileSystems", []):
                name = next((t["Value"] for t in fs.get("Tags", []) if t["Key"] == "Name"), fs["FileSystemId"])
                size_bytes = fs.get("SizeInBytes", {}).get("Value", 0)
                size_str = f"{round(size_bytes / (1024 ** 3), 2)} GB" if size_bytes else ""
                items.append({"id": fs["FileSystemId"], "name": name, "type": "EFS",
                              "region": region, "status": fs.get("LifeCycleState", "unknown"),
                              "size": size_str,
                              "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in fs.get("Tags", []))})
            return items

        if resource_type == "SES":
            ses = _client("ses")
            return [
                {"id": identity, "name": identity, "type": "SES",
                 "region": region, "status": "active", "tags": ""}
                for identity in ses.list_identities().get("Identities", [])
            ]

        if resource_type == "WAF":
            items = []
            for scope, scope_region in (("REGIONAL", region), ("CLOUDFRONT", "us-east-1")):
                wafv2 = _client("wafv2", scope_region)
                for acl in wafv2.list_web_acls(Scope=scope).get("WebACLs", []):
                    items.append({"id": acl["ARN"], "name": acl["Name"], "type": "WAF",
                                  "region": scope_region, "status": "active", "tags": ""})
            return items

        if resource_type == "CodeBuild":
            cb = _client("codebuild")
            return [
                {"id": name, "name": name, "type": "CodeBuild", "region": region, "status": "active", "tags": ""}
                for name in cb.list_projects().get("projects", [])
            ]

        if resource_type == "CodePipeline":
            cp = _client("codepipeline")
            items = []
            for page in cp.get_paginator("list_pipelines").paginate():
                for pipeline in page.get("pipelines", []):
                    items.append({"id": pipeline["name"], "name": pipeline["name"], "type": "CodePipeline",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "QuickSight":
            qs = _client("quicksight")
            account_id = _client("sts").get_caller_identity()["Account"]
            items = []
            for page in qs.get_paginator("list_dashboards").paginate(AwsAccountId=account_id):
                for dashboard in page.get("DashboardSummaryList", []):
                    items.append({"id": dashboard["DashboardId"], "name": dashboard["Name"], "type": "QuickSight",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "Inspector":
            inspector = _client("inspector2")
            return [
                {"id": r.get("resourceId", ""), "name": r.get("resourceId", ""), "type": "Inspector",
                 "region": region, "status": "active", "tags": ""}
                for r in inspector.list_coverage().get("coveredResources", [])
            ]

        if resource_type == "X-Ray":
            xray = _client("xray")
            return [
                {"id": g["GroupARN"], "name": g["GroupName"], "type": "X-Ray",
                 "region": region, "status": "active", "tags": ""}
                for g in xray.get_groups().get("Groups", [])
            ]

        if resource_type == "Transfer Family":
            transfer = _client("transfer")
            return [
                {"id": s["ServerId"],
                 "name": next((t["Value"] for t in s.get("Tags", []) if t.get("Key") == "Name"), s["ServerId"]),
                 "type": "Transfer Family", "region": region,
                 "status": s.get("State", "unknown").lower(), "tags": ""}
                for s in transfer.list_servers().get("Servers", [])
            ]

        if resource_type == "EventBridge":
            events = _client("events")
            items = []
            for page in events.get_paginator("list_event_buses").paginate():
                for bus in page.get("EventBuses", []):
                    items.append({"id": bus["Arn"], "name": bus["Name"], "type": "EventBridge",
                                  "region": region, "status": "active", "tags": ""})
            return items

        if resource_type == "Location Service":
            location = _client("location")
            return [
                {"id": t["TrackerName"], "name": t["TrackerName"], "type": "Location Service",
                 "region": region, "status": "active", "tags": ""}
                for t in location.list_trackers().get("Entries", [])
            ]

        # ---------------------------------------------------------------
        # EC2 sub-resource types (accessed via EC2 category navigation)
        # ---------------------------------------------------------------

        if resource_type == "AMI":
            ec2 = _client("ec2")
            items = []
            for image in ec2.describe_images(Owners=["self"]).get("Images", []):
                name = image.get("Name") or image["ImageId"]
                tags_str = ",".join(
                    f"{t['Key']}:{t['Value']}" for t in image.get("Tags", [])
                )
                items.append({
                    "id": image["ImageId"],
                    "name": name,
                    "type": "AMI",
                    "region": region,
                    "status": image.get("State", "available"),
                    "size": image.get("Architecture", ""),
                    "architecture": image.get("Architecture", ""),
                    "platform": image.get("PlatformDetails", "Linux/UNIX"),
                    "virtualization_type": image.get("VirtualizationType", ""),
                    "root_device_type": image.get("RootDeviceType", ""),
                    "root_device_name": image.get("RootDeviceName", ""),
                    "creation_date": image.get("CreationDate", ""),
                    "owner_id": image.get("OwnerId", ""),
                    "public": image.get("Public", False),
                    "description": image.get("Description", ""),
                    "hypervisor": image.get("Hypervisor", ""),
                    "image_type": image.get("ImageType", "machine"),
                    "tags": tags_str,
                })
            return items

        if resource_type == "EBS Volume":
            ec2 = _client("ec2")
            items = []
            for vol in ec2.describe_volumes().get("Volumes", []):
                name = next(
                    (t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"),
                    vol["VolumeId"],
                )
                attachments = vol.get("Attachments", [])
                attached_to = ", ".join(a.get("InstanceId", "") for a in attachments)
                attached_device = ", ".join(a.get("Device", "") for a in attachments)
                items.append({
                    "id": vol["VolumeId"],
                    "name": name,
                    "type": "EBS Volume",
                    "region": vol.get("AvailabilityZone", region),
                    "status": vol.get("State", "available"),
                    "size": f"{vol.get('Size', '')} GiB",
                    "volume_type": vol.get("VolumeType", ""),
                    "volume_size_gib": vol.get("Size"),
                    "availability_zone": vol.get("AvailabilityZone", region),
                    "iops": vol.get("Iops"),
                    "throughput": vol.get("Throughput"),
                    "encrypted": vol.get("Encrypted", False),
                    "kms_key_id": vol.get("KmsKeyId", ""),
                    "snapshot_id": vol.get("SnapshotId", ""),
                    "attached_to": attached_to,
                    "attached_device": attached_device,
                    "multi_attach": vol.get("MultiAttachEnabled", False),
                    "creation_time": str(vol.get("CreateTime", "")),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in vol.get("Tags", [])),
                })
            return items

        if resource_type == "EBS Snapshot":
            ec2 = _client("ec2")
            items = []
            for snap in ec2.describe_snapshots(OwnerIds=["self"]).get("Snapshots", []):
                name = next(
                    (t["Value"] for t in snap.get("Tags", []) if t["Key"] == "Name"),
                    snap["SnapshotId"],
                )
                items.append({
                    "id": snap["SnapshotId"],
                    "name": name,
                    "type": "EBS Snapshot",
                    "region": region,
                    "status": snap.get("State", "completed"),
                    "size": f"{snap.get('VolumeSize', '')} GiB",
                    "volume_id": snap.get("VolumeId", ""),
                    "volume_size_gib": snap.get("VolumeSize"),
                    "description": snap.get("Description", ""),
                    "owner_id": snap.get("OwnerId", ""),
                    "encrypted": snap.get("Encrypted", False),
                    "kms_key_id": snap.get("KmsKeyId", ""),
                    "start_time": str(snap.get("StartTime", "")),
                    "progress": snap.get("Progress", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in snap.get("Tags", [])),
                })
            return items

        if resource_type == "Security Group":
            ec2 = _client("ec2")
            items = []
            for sg in ec2.describe_security_groups().get("SecurityGroups", []):
                inbound_count = len(sg.get("IpPermissions", []))
                outbound_count = len(sg.get("IpPermissionsEgress", []))
                items.append({
                    "id": sg["GroupId"],
                    "name": sg.get("GroupName", sg["GroupId"]),
                    "type": "Security Group",
                    "region": region,
                    "status": "active",
                    "size": "",
                    "group_id": sg["GroupId"],
                    "description": sg.get("Description", ""),
                    "vpc_id": sg.get("VpcId", ""),
                    "inbound_rules": inbound_count,
                    "outbound_rules": outbound_count,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in sg.get("Tags", [])),
                })
            return items

        if resource_type == "Elastic IP":
            ec2 = _client("ec2")
            items = []
            for addr in ec2.describe_addresses().get("Addresses", []):
                name = next(
                    (t["Value"] for t in addr.get("Tags", []) if t["Key"] == "Name"),
                    addr.get("PublicIp", ""),
                )
                items.append({
                    "id": addr.get("AllocationId", addr.get("PublicIp", "")),
                    "name": name,
                    "type": "Elastic IP",
                    "region": region,
                    "status": "in-use" if addr.get("AssociationId") else "unassociated",
                    "size": "",
                    "public_ip": addr.get("PublicIp", ""),
                    "private_ip": addr.get("PrivateIpAddress", ""),
                    "allocation_id": addr.get("AllocationId", ""),
                    "association_id": addr.get("AssociationId", ""),
                    "instance_id": addr.get("InstanceId", ""),
                    "network_interface_id": addr.get("NetworkInterfaceId", ""),
                    "domain": addr.get("Domain", "vpc"),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in addr.get("Tags", [])),
                })
            return items

        if resource_type == "Key Pair":
            ec2 = _client("ec2")
            items = []
            for kp in ec2.describe_key_pairs().get("KeyPairs", []):
                items.append({
                    "id": kp.get("KeyPairId", kp["KeyName"]),
                    "name": kp["KeyName"],
                    "type": "Key Pair",
                    "region": region,
                    "status": "active",
                    "size": "",
                    "key_pair_id": kp.get("KeyPairId", ""),
                    "key_type": kp.get("KeyType", "rsa"),
                    "fingerprint": kp.get("KeyFingerprint", ""),
                    "creation_time": str(kp.get("CreateTime", "")),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in kp.get("Tags", [])),
                })
            return items

        if resource_type == "Network Interface":
            ec2 = _client("ec2")
            items = []
            for eni in ec2.describe_network_interfaces().get("NetworkInterfaces", []):
                name = next(
                    (t["Value"] for t in eni.get("TagSet", []) if t["Key"] == "Name"),
                    eni["NetworkInterfaceId"],
                )
                private_ips = ", ".join(
                    a.get("PrivateIpAddress", "") for a in eni.get("PrivateIpAddresses", [])
                )
                security_groups = ", ".join(
                    f"{sg['GroupName']} ({sg['GroupId']})"
                    for sg in eni.get("Groups", [])
                )
                items.append({
                    "id": eni["NetworkInterfaceId"],
                    "name": name,
                    "type": "Network Interface",
                    "region": eni.get("AvailabilityZone", region),
                    "status": eni.get("Status", "available"),
                    "size": "",
                    "interface_type": eni.get("InterfaceType", "interface"),
                    "vpc_id": eni.get("VpcId", ""),
                    "subnet_id": eni.get("SubnetId", ""),
                    "availability_zone": eni.get("AvailabilityZone", region),
                    "private_ip": eni.get("PrivateIpAddress", ""),
                    "private_ips": private_ips,
                    "public_ip": eni.get("Association", {}).get("PublicIp", ""),
                    "mac_address": eni.get("MacAddress", ""),
                    "security_groups": security_groups,
                    "source_dest_check": eni.get("SourceDestCheck"),
                    "attached_to": eni.get("Attachment", {}).get("InstanceId", ""),
                    "description": eni.get("Description", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in eni.get("TagSet", [])),
                })
            return items

        if resource_type == "Placement Group":
            ec2 = _client("ec2")
            items = []
            for pg in ec2.describe_placement_groups().get("PlacementGroups", []):
                items.append({
                    "id": pg.get("GroupId", pg["GroupName"]),
                    "name": pg["GroupName"],
                    "type": "Placement Group",
                    "region": region,
                    "status": pg.get("State", "available"),
                    "size": "",
                    "strategy": pg.get("Strategy", ""),
                    "partition_count": pg.get("PartitionCount"),
                    "spread_level": pg.get("SpreadLevel", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in pg.get("Tags", [])),
                })
            return items

        if resource_type == "Target Group":
            elbv2 = _client("elbv2")
            items = []
            for tg in elbv2.describe_target_groups().get("TargetGroups", []):
                lbs = ", ".join(
                    arn.split("/")[2] for arn in tg.get("LoadBalancerArns", [])
                )
                items.append({
                    "id": tg["TargetGroupArn"],
                    "name": tg["TargetGroupName"],
                    "type": "Target Group",
                    "region": region,
                    "status": "active",
                    "size": "",
                    "protocol": tg.get("Protocol", ""),
                    "port": tg.get("Port"),
                    "target_type": tg.get("TargetType", ""),
                    "vpc_id": tg.get("VpcId", ""),
                    "load_balancers": lbs,
                    "healthy_threshold": tg.get("HealthyThresholdCount"),
                    "unhealthy_threshold": tg.get("UnhealthyThresholdCount"),
                    "health_check_path": tg.get("HealthCheckPath", ""),
                    "health_check_protocol": tg.get("HealthCheckProtocol", ""),
                    "tags": "",
                })
            return items

        if resource_type == "Auto Scaling Group":
            asg = _client("autoscaling")
            items = []
            for group in asg.describe_auto_scaling_groups().get("AutoScalingGroups", []):
                azs = ", ".join(group.get("AvailabilityZones", []))
                items.append({
                    "id": group["AutoScalingGroupARN"],
                    "name": group["AutoScalingGroupName"],
                    "type": "Auto Scaling Group",
                    "region": region,
                    "status": group.get("Status", "active") or "active",
                    "size": f"{group.get('DesiredCapacity', 0)} instances",
                    "min_size": group.get("MinSize"),
                    "max_size": group.get("MaxSize"),
                    "desired_capacity": group.get("DesiredCapacity"),
                    "launch_template": group.get("LaunchTemplate", {}).get("LaunchTemplateName", ""),
                    "launch_config": group.get("LaunchConfigurationName", ""),
                    "availability_zones": azs,
                    "health_check_type": group.get("HealthCheckType", ""),
                    "health_check_grace_period": group.get("HealthCheckGracePeriod"),
                    "vpc_zone_identifier": group.get("VPCZoneIdentifier", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in group.get("Tags", [])),
                })
            return items

        # ---------------------------------------------------------------
        # VPC sub-resource types
        # ---------------------------------------------------------------

        if resource_type == "Subnet":
            ec2 = _client("ec2")
            items = []
            for s in ec2.describe_subnets().get("Subnets", []):
                name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), s["SubnetId"])
                items.append({
                    "id": s["SubnetId"], "name": name, "type": "Subnet",
                    "region": s.get("AvailabilityZone", region),
                    "status": s.get("State", "available"),
                    "size": s.get("CidrBlock", ""),
                    "cidr_block": s.get("CidrBlock", ""),
                    "vpc_id": s.get("VpcId", ""),
                    "availability_zone": s.get("AvailabilityZone", region),
                    "available_ips": s.get("AvailableIpAddressCount"),
                    "public": s.get("MapPublicIpOnLaunch", False),
                    "default_for_az": s.get("DefaultForAz", False),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in s.get("Tags", [])),
                })
            return items

        if resource_type == "Route Table":
            ec2 = _client("ec2")
            items = []
            for rt in ec2.describe_route_tables().get("RouteTables", []):
                name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), rt["RouteTableId"])
                assoc_subnets = [
                    a.get("SubnetId", "") for a in rt.get("Associations", []) if a.get("SubnetId")
                ]
                main = any(a.get("Main", False) for a in rt.get("Associations", []))
                items.append({
                    "id": rt["RouteTableId"], "name": name, "type": "Route Table",
                    "region": region, "status": "active",
                    "size": f"{len(rt.get('Routes', []))} routes",
                    "vpc_id": rt.get("VpcId", ""),
                    "route_count": len(rt.get("Routes", [])),
                    "associated_subnets": len(assoc_subnets),
                    "main": main,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in rt.get("Tags", [])),
                })
            return items

        if resource_type == "Internet Gateway":
            ec2 = _client("ec2")
            items = []
            for igw in ec2.describe_internet_gateways().get("InternetGateways", []):
                name = next((t["Value"] for t in igw.get("Tags", []) if t["Key"] == "Name"), igw["InternetGatewayId"])
                attachments = igw.get("Attachments", [])
                vpc_id = attachments[0].get("VpcId", "") if attachments else ""
                status = attachments[0].get("State", "detached") if attachments else "detached"
                items.append({
                    "id": igw["InternetGatewayId"], "name": name, "type": "Internet Gateway",
                    "region": region, "status": status,
                    "size": "",
                    "vpc_id": vpc_id,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in igw.get("Tags", [])),
                })
            return items

        if resource_type == "Egress-only Internet Gateway":
            ec2 = _client("ec2")
            items = []
            for eigw in ec2.describe_egress_only_internet_gateways().get("EgressOnlyInternetGateways", []):
                name = next((t["Value"] for t in eigw.get("Tags", []) if t["Key"] == "Name"), eigw["EgressOnlyInternetGatewayId"])
                attachments = eigw.get("Attachments", [])
                vpc_id = attachments[0].get("VpcId", "") if attachments else ""
                status = attachments[0].get("State", "detached") if attachments else "detached"
                items.append({
                    "id": eigw["EgressOnlyInternetGatewayId"], "name": name,
                    "type": "Egress-only Internet Gateway",
                    "region": region, "status": status,
                    "size": "", "vpc_id": vpc_id,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in eigw.get("Tags", [])),
                })
            return items

        if resource_type == "DHCP Option Set":
            ec2 = _client("ec2")
            items = []
            for dhcp in ec2.describe_dhcp_options().get("DhcpOptions", []):
                name = next((t["Value"] for t in dhcp.get("Tags", []) if t["Key"] == "Name"), dhcp["DhcpOptionsId"])
                configs = {
                    c["Key"]: ", ".join(v.get("Value", "") for v in c.get("Values", []))
                    for c in dhcp.get("DhcpConfigurations", [])
                }
                items.append({
                    "id": dhcp["DhcpOptionsId"], "name": name, "type": "DHCP Option Set",
                    "region": region, "status": "active", "size": "",
                    "domain_name": configs.get("domain-name", ""),
                    "domain_name_servers": configs.get("domain-name-servers", ""),
                    "ntp_servers": configs.get("ntp-servers", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in dhcp.get("Tags", [])),
                })
            return items

        if resource_type == "Managed Prefix List":
            ec2 = _client("ec2")
            items = []
            for pl in ec2.describe_managed_prefix_lists().get("PrefixLists", []):
                items.append({
                    "id": pl.get("PrefixListId", ""), "name": pl.get("PrefixListName", ""),
                    "type": "Managed Prefix List", "region": region,
                    "status": pl.get("State", "").lower(),
                    "size": f"{pl.get('MaxEntries', '')} max entries",
                    "address_family": pl.get("AddressFamily", ""),
                    "max_entries": pl.get("MaxEntries"),
                    "owner_id": pl.get("OwnerId", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in pl.get("Tags", [])),
                })
            return items

        if resource_type == "VPC Endpoint":
            ec2 = _client("ec2")
            items = []
            for ep in ec2.describe_vpc_endpoints().get("VpcEndpoints", []):
                if ep.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in ep.get("Tags", []) if t["Key"] == "Name"), ep["VpcEndpointId"])
                items.append({
                    "id": ep["VpcEndpointId"], "name": name, "type": "VPC Endpoint",
                    "region": region, "status": ep.get("State", "unknown"),
                    "size": ep.get("VpcEndpointType", ""),
                    "vpc_id": ep.get("VpcId", ""),
                    "service_name": ep.get("ServiceName", ""),
                    "endpoint_type": ep.get("VpcEndpointType", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in ep.get("Tags", [])),
                })
            return items

        if resource_type == "VPC Endpoint Service":
            ec2 = _client("ec2")
            items = []
            for svc in ec2.describe_vpc_endpoint_services(Filters=[{"Name": "owner", "Values": ["self"]}]).get("ServiceDetails", []):
                items.append({
                    "id": svc.get("ServiceId", svc.get("ServiceName", "")),
                    "name": svc.get("ServiceName", ""),
                    "type": "VPC Endpoint Service",
                    "region": region, "status": "available",
                    "size": svc.get("ServiceType", [{}])[0].get("ServiceType", "") if svc.get("ServiceType") else "",
                    "acceptance_required": svc.get("AcceptanceRequired", False),
                    "availability_zones": ", ".join(svc.get("AvailabilityZones", [])),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in svc.get("Tags", [])),
                })
            return items

        if resource_type == "NAT Gateway":
            ec2 = _client("ec2")
            items = []
            for nat in ec2.describe_nat_gateways().get("NatGateways", []):
                if nat.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in nat.get("Tags", []) if t["Key"] == "Name"), nat["NatGatewayId"])
                nat_ips = nat.get("NatGatewayAddresses", [])
                public_ip = nat_ips[0].get("PublicIp", "") if nat_ips else ""
                items.append({
                    "id": nat["NatGatewayId"], "name": name, "type": "NAT Gateway",
                    "region": region, "status": nat.get("State", "unknown"),
                    "size": nat.get("ConnectivityType", "public"),
                    "vpc_id": nat.get("VpcId", ""),
                    "subnet_id": nat.get("SubnetId", ""),
                    "public_ip": public_ip,
                    "connectivity_type": nat.get("ConnectivityType", "public"),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in nat.get("Tags", [])),
                })
            return items

        if resource_type == "VPC Peering Connection":
            ec2 = _client("ec2")
            items = []
            for peer in ec2.describe_vpc_peering_connections().get("VpcPeeringConnections", []):
                if peer.get("Status", {}).get("Code") == "deleted":
                    continue
                name = next((t["Value"] for t in peer.get("Tags", []) if t["Key"] == "Name"), peer["VpcPeeringConnectionId"])
                requester = peer.get("RequesterVpcInfo", {})
                accepter = peer.get("AccepterVpcInfo", {})
                items.append({
                    "id": peer["VpcPeeringConnectionId"], "name": name, "type": "VPC Peering Connection",
                    "region": region,
                    "status": peer.get("Status", {}).get("Code", "unknown"),
                    "size": "",
                    "requester_vpc": requester.get("VpcId", ""),
                    "requester_cidr": requester.get("CidrBlock", ""),
                    "accepter_vpc": accepter.get("VpcId", ""),
                    "accepter_cidr": accepter.get("CidrBlock", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in peer.get("Tags", [])),
                })
            return items

        if resource_type == "Network ACL":
            ec2 = _client("ec2")
            items = []
            for acl in ec2.describe_network_acls().get("NetworkAcls", []):
                name = next((t["Value"] for t in acl.get("Tags", []) if t["Key"] == "Name"), acl["NetworkAclId"])
                assoc_subnets = len(acl.get("Associations", []))
                inbound = len([r for r in acl.get("Entries", []) if not r.get("Egress")])
                outbound = len([r for r in acl.get("Entries", []) if r.get("Egress")])
                items.append({
                    "id": acl["NetworkAclId"], "name": name, "type": "Network ACL",
                    "region": region, "status": "active",
                    "size": f"{inbound} inbound, {outbound} outbound",
                    "vpc_id": acl.get("VpcId", ""),
                    "default": acl.get("IsDefault", False),
                    "inbound_rules": inbound, "outbound_rules": outbound,
                    "associated_subnets": assoc_subnets,
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in acl.get("Tags", [])),
                })
            return items

        if resource_type == "DNS Firewall Rule Group":
            r53resolver = _client("route53resolver")
            items = []
            for page in r53resolver.get_paginator("list_firewall_rule_groups").paginate():
                for rg in page.get("FirewallRuleGroups", []):
                    items.append({
                        "id": rg["Id"], "name": rg["Name"], "type": "DNS Firewall Rule Group",
                        "region": region, "status": rg.get("Status", "").lower(),
                        "size": f"{rg.get('RuleCount', 0)} rules",
                        "rule_count": rg.get("RuleCount", 0),
                        "owner_id": rg.get("OwnerId", ""),
                        "share_status": rg.get("ShareStatus", ""),
                        "tags": "",
                    })
            return items

        if resource_type == "DNS Firewall Domain List":
            r53resolver = _client("route53resolver")
            items = []
            for page in r53resolver.get_paginator("list_firewall_domain_lists").paginate():
                for dl in page.get("FirewallDomainLists", []):
                    items.append({
                        "id": dl["Id"], "name": dl["Name"], "type": "DNS Firewall Domain List",
                        "region": region, "status": dl.get("Status", "").lower(),
                        "size": f"{dl.get('DomainCount', 0)} domains",
                        "domain_count": dl.get("DomainCount", 0),
                        "owner_id": dl.get("OwnerId", ""),
                        "tags": "",
                    })
            return items

        if resource_type == "Network Firewall":
            nfw = _client("network-firewall")
            items = []
            for page in nfw.get_paginator("list_firewalls").paginate():
                for fw in page.get("Firewalls", []):
                    items.append({
                        "id": fw.get("FirewallArn", ""), "name": fw.get("FirewallName", ""),
                        "type": "Network Firewall", "region": region, "status": "active",
                        "size": "",
                        "vpc_id": fw.get("VpcId", ""),
                        "tags": "",
                    })
            return items

        if resource_type == "Firewall Policy":
            nfw = _client("network-firewall")
            items = []
            for page in nfw.get_paginator("list_firewall_policies").paginate():
                for fp in page.get("FirewallPolicies", []):
                    items.append({
                        "id": fp.get("Arn", ""), "name": fp.get("Name", ""),
                        "type": "Firewall Policy", "region": region, "status": "active",
                        "size": "", "tags": "",
                    })
            return items

        if resource_type == "Network Firewall Rule Group":
            nfw = _client("network-firewall")
            items = []
            for page in nfw.get_paginator("list_rule_groups").paginate():
                for rg in page.get("RuleGroups", []):
                    items.append({
                        "id": rg.get("Arn", ""), "name": rg.get("Name", ""),
                        "type": "Network Firewall Rule Group", "region": region, "status": "active",
                        "size": rg.get("Type", ""), "tags": "",
                    })
            return items

        if resource_type == "TLS Inspection Configuration":
            nfw = _client("network-firewall")
            items = []
            for page in nfw.get_paginator("list_tls_inspection_configurations").paginate():
                for cfg in page.get("TLSInspectionConfigurations", []):
                    items.append({
                        "id": cfg.get("Arn", ""), "name": cfg.get("Name", ""),
                        "type": "TLS Inspection Configuration", "region": region, "status": "active",
                        "size": "", "tags": "",
                    })
            return items

        if resource_type == "Customer Gateway":
            ec2 = _client("ec2")
            items = []
            for cgw in ec2.describe_customer_gateways().get("CustomerGateways", []):
                if cgw.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in cgw.get("Tags", []) if t["Key"] == "Name"), cgw["CustomerGatewayId"])
                items.append({
                    "id": cgw["CustomerGatewayId"], "name": name, "type": "Customer Gateway",
                    "region": region, "status": cgw.get("State", "unknown"),
                    "size": cgw.get("Type", ""),
                    "ip_address": cgw.get("IpAddress", ""),
                    "bgp_asn": cgw.get("BgpAsn", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in cgw.get("Tags", [])),
                })
            return items

        if resource_type == "Virtual Private Gateway":
            ec2 = _client("ec2")
            items = []
            for vgw in ec2.describe_vpn_gateways().get("VpnGateways", []):
                if vgw.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in vgw.get("Tags", []) if t["Key"] == "Name"), vgw["VpnGatewayId"])
                attached_vpcs = [a["VpcId"] for a in vgw.get("VpcAttachments", []) if a.get("State") == "attached"]
                items.append({
                    "id": vgw["VpnGatewayId"], "name": name, "type": "Virtual Private Gateway",
                    "region": region, "status": vgw.get("State", "unknown"),
                    "size": vgw.get("Type", ""),
                    "amazon_side_asn": str(vgw.get("AmazonSideAsn", "")),
                    "attached_vpcs": ", ".join(attached_vpcs),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in vgw.get("Tags", [])),
                })
            return items

        if resource_type == "VPN Connection":
            ec2 = _client("ec2")
            items = []
            for vpn in ec2.describe_vpn_connections().get("VpnConnections", []):
                if vpn.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in vpn.get("Tags", []) if t["Key"] == "Name"), vpn["VpnConnectionId"])
                items.append({
                    "id": vpn["VpnConnectionId"], "name": name, "type": "VPN Connection",
                    "region": region, "status": vpn.get("State", "unknown"),
                    "size": vpn.get("Type", ""),
                    "customer_gateway_id": vpn.get("CustomerGatewayId", ""),
                    "vpn_gateway_id": vpn.get("VpnGatewayId", ""),
                    "transit_gateway_id": vpn.get("TransitGatewayId", ""),
                    "category": vpn.get("Category", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in vpn.get("Tags", [])),
                })
            return items

        if resource_type == "Transit Gateway":
            ec2 = _client("ec2")
            items = []
            for tgw in ec2.describe_transit_gateways().get("TransitGateways", []):
                if tgw.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in tgw.get("Tags", []) if t["Key"] == "Name"), tgw["TransitGatewayId"])
                items.append({
                    "id": tgw["TransitGatewayId"], "name": name, "type": "Transit Gateway",
                    "region": region, "status": tgw.get("State", "unknown"),
                    "size": "",
                    "owner_id": tgw.get("OwnerId", ""),
                    "amazon_side_asn": str(tgw.get("Options", {}).get("AmazonSideAsn", "")),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in tgw.get("Tags", [])),
                })
            return items

        if resource_type == "Transit Gateway Attachment":
            ec2 = _client("ec2")
            items = []
            for att in ec2.describe_transit_gateway_attachments().get("TransitGatewayAttachments", []):
                if att.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in att.get("Tags", []) if t["Key"] == "Name"), att["TransitGatewayAttachmentId"])
                items.append({
                    "id": att["TransitGatewayAttachmentId"], "name": name,
                    "type": "Transit Gateway Attachment",
                    "region": region, "status": att.get("State", "unknown"),
                    "size": att.get("ResourceType", ""),
                    "transit_gateway_id": att.get("TransitGatewayId", ""),
                    "resource_type": att.get("ResourceType", ""),
                    "resource_id": att.get("ResourceId", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in att.get("Tags", [])),
                })
            return items

        if resource_type == "Transit Gateway Route Table":
            ec2 = _client("ec2")
            items = []
            for tgw_rt in ec2.describe_transit_gateway_route_tables().get("TransitGatewayRouteTables", []):
                if tgw_rt.get("State") == "deleted":
                    continue
                name = next((t["Value"] for t in tgw_rt.get("Tags", []) if t["Key"] == "Name"), tgw_rt["TransitGatewayRouteTableId"])
                items.append({
                    "id": tgw_rt["TransitGatewayRouteTableId"], "name": name,
                    "type": "Transit Gateway Route Table",
                    "region": region, "status": tgw_rt.get("State", "unknown"),
                    "size": "",
                    "transit_gateway_id": tgw_rt.get("TransitGatewayId", ""),
                    "default_association": tgw_rt.get("DefaultAssociationRouteTable", False),
                    "default_propagation": tgw_rt.get("DefaultPropagationRouteTable", False),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in tgw_rt.get("Tags", [])),
                })
            return items

        if resource_type == "Mirror Session":
            ec2 = _client("ec2")
            items = []
            for ms in ec2.describe_traffic_mirror_sessions().get("TrafficMirrorSessions", []):
                name = next((t["Value"] for t in ms.get("Tags", []) if t["Key"] == "Name"), ms["TrafficMirrorSessionId"])
                items.append({
                    "id": ms["TrafficMirrorSessionId"], "name": name, "type": "Mirror Session",
                    "region": region, "status": "active",
                    "size": f"session {ms.get('SessionNumber', '')}",
                    "traffic_mirror_target_id": ms.get("TrafficMirrorTargetId", ""),
                    "traffic_mirror_filter_id": ms.get("TrafficMirrorFilterId", ""),
                    "network_interface_id": ms.get("NetworkInterfaceId", ""),
                    "session_number": ms.get("SessionNumber"),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in ms.get("Tags", [])),
                })
            return items

        if resource_type == "Mirror Target":
            ec2 = _client("ec2")
            items = []
            for mt in ec2.describe_traffic_mirror_targets().get("TrafficMirrorTargets", []):
                name = next((t["Value"] for t in mt.get("Tags", []) if t["Key"] == "Name"), mt["TrafficMirrorTargetId"])
                items.append({
                    "id": mt["TrafficMirrorTargetId"], "name": name, "type": "Mirror Target",
                    "region": region, "status": "active",
                    "size": mt.get("Type", ""),
                    "target_type": mt.get("Type", ""),
                    "network_interface_id": mt.get("NetworkInterfaceId", ""),
                    "network_load_balancer_arn": mt.get("NetworkLoadBalancerArn", ""),
                    "owner_id": mt.get("OwnerId", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in mt.get("Tags", [])),
                })
            return items

        if resource_type == "Mirror Filter":
            ec2 = _client("ec2")
            items = []
            for mf in ec2.describe_traffic_mirror_filters().get("TrafficMirrorFilters", []):
                name = next((t["Value"] for t in mf.get("Tags", []) if t["Key"] == "Name"), mf["TrafficMirrorFilterId"])
                items.append({
                    "id": mf["TrafficMirrorFilterId"], "name": name, "type": "Mirror Filter",
                    "region": region, "status": "active",
                    "size": f"{len(mf.get('IngressFilterRules', []))} ingress, {len(mf.get('EgressFilterRules', []))} egress rules",
                    "ingress_rules": len(mf.get("IngressFilterRules", [])),
                    "egress_rules": len(mf.get("EgressFilterRules", [])),
                    "description": mf.get("Description", ""),
                    "tags": ",".join(f"{t['Key']}:{t['Value']}" for t in mf.get("Tags", [])),
                })
            return items

    except Exception:
        pass
    return []

# Maximum number of concurrent AWS API calls when fetching multiple resource types.
_MAX_CONCURRENT_FETCHES = 20

_ALL_RESOURCE_TYPES = [
    "EC2", "VPC", "S3", "RDS", "Lambda", "ElastiCache", "OpenSearch",
    "SQS", "SNS", "DynamoDB", "ECS", "EKS", "ELB", "CloudWatch", "MSK",
    "Glue", "Athena", "API Gateway", "Route 53", "CloudFormation", "CloudTrail",
    "KMS", "Secrets Manager", "Cognito", "ECR", "ECR Public", "Step Functions",
    "EFS", "SES", "WAF", "CodeBuild", "CodePipeline", "QuickSight", "Inspector",
    "X-Ray", "Transfer Family", "EventBridge", "Location Service",
    # EC2 sub-resources (AMI, EBS Volume, EBS Snapshot, Security Group, Elastic IP,
    # Key Pair, Network Interface, Placement Group, Target Group, Auto Scaling Group)
    # are intentionally excluded here.  They are fetched on-demand only when
    # explicitly requested via the EC2 Dashboard sub-category panel, so they do
    # not slow down the initial resource summary fetch.
]


def get_resources(
    credentials: dict,
    resource_types: list[str] | None = None,
    region: str | None = None,
) -> list[dict]:
    _last_resources_error.clear()
    if not credentials.get("access_key_id") or not credentials.get("secret_access_key"):
        result = mock_service.get_resources("aws")
        if resource_types:
            wanted = set(resource_types)
            result = [r for r in result if r.get("type") in wanted]
        return result
    try:
        session, config = _make_clients(credentials)
        effective_region = region or credentials.get("region", "us-east-1")
        types_to_fetch = resource_types if resource_types else _ALL_RESOURCE_TYPES

        resources: list[dict] = []
        max_workers = min(len(types_to_fetch), _MAX_CONCURRENT_FETCHES)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_type, session, t, effective_region, config): t for t in types_to_fetch}
            for future in as_completed(futures):
                try:
                    resources.extend(future.result())
                except Exception:
                    pass

        return resources
    except Exception as exc:
        _last_resources_error["error"] = str(exc)
        return []


# Stores the most recent error from get_resources so the router can surface it.
_last_resources_error: dict[str, str] = {}


def get_resource_types(credentials: dict) -> list[str]:
    """Return all known AWS resource types so the dropdown always shows every option."""
    return mock_service.get_resource_types("aws")


def get_overall_billing(credentials: dict, start: date, end: date, region: str | None = None) -> dict:
    _last_billing_error.clear()
    if not credentials.get("access_key_id") or not credentials.get("secret_access_key"):
        return mock_service.get_overall_billing("aws", start, end)
    try:
        import boto3  # type: ignore

        ce = boto3.client(
            "ce",
            aws_access_key_id=credentials.get("access_key_id"),
            aws_secret_access_key=credentials.get("secret_access_key"),
            region_name="us-east-1",
        )
        ce_kwargs: dict = {
            "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        }
        if region:
            ce_kwargs["Filter"] = {"Dimensions": {"Key": "REGION", "Values": [region]}}
        resp = ce.get_cost_and_usage(**ce_kwargs)
        daily_map: dict[str, float] = {}
        service_totals: dict[str, float] = {}
        for result in resp.get("ResultsByTime", []):
            day = result["TimePeriod"]["Start"]
            day_total = 0.0
            for group in result.get("Groups", []):
                svc = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                service_totals[svc] = service_totals.get(svc, 0.0) + cost
                day_total += cost
            daily_map[day] = daily_map.get(day, 0.0) + day_total

        if daily_map:
            daily = [{"date": d, "cost": round(c, 2)} for d, c in sorted(daily_map.items())]
            total = round(sum(daily_map.values()), 2)
            breakdown = sorted(
                [{"service": svc, "cost": round(cost, 2)} for svc, cost in service_totals.items()],
                key=lambda x: x["cost"],
                reverse=True,
            )
            return {
                "total": total,
                "currency": "USD",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily_costs": daily,
                "breakdown": breakdown,
            }
        # Cost Explorer returned no data for the period — return zero-cost result
        return {
            "total": 0.0,
            "currency": "USD",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily_costs": [],
            "breakdown": [],
        }
    except Exception as exc:
        _last_billing_error["error"] = str(exc)
    return {
        "total": 0.0,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": [],
        "breakdown": [],
    }


def get_billing_by_resource_type(credentials: dict, resource_type: str, start: date, end: date, region: str | None = None) -> dict:
    _last_billing_error.clear()
    if not credentials.get("access_key_id") or not credentials.get("secret_access_key"):
        return mock_service.get_billing_by_resource_type("aws", resource_type, start, end)
    try:
        import boto3  # type: ignore

        ce = boto3.client(
            "ce",
            aws_access_key_id=credentials.get("access_key_id"),
            aws_secret_access_key=credentials.get("secret_access_key"),
            region_name="us-east-1",
        )
        svc_filter: dict = {"Dimensions": {"Key": "SERVICE", "Values": [_CE_SERVICE_MAP.get(resource_type, resource_type)]}}
        if region:
            region_filter: dict = {"Dimensions": {"Key": "REGION", "Values": [region]}}
            ce_filter: dict = {"And": [svc_filter, region_filter]}
        else:
            ce_filter = svc_filter
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            Filter=ce_filter,
        )
        daily = []
        total = 0.0
        for result in resp.get("ResultsByTime", []):
            cost = float(result["Total"]["UnblendedCost"]["Amount"])
            daily.append({"date": result["TimePeriod"]["Start"], "cost": round(cost, 2)})
            total += cost
        if daily:
            days = len(daily)
            return {
                "resource_type": resource_type,
                "total": round(total, 2),
                "currency": "USD",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily_costs": daily,
                "average_daily": round(total / max(days, 1), 2),
            }
        # No cost data found — return zero-cost result
        return {
            "resource_type": resource_type,
            "total": 0.0,
            "currency": "USD",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily_costs": [],
            "average_daily": 0.0,
        }
    except Exception as exc:
        _last_billing_error["error"] = str(exc)
    return {
        "resource_type": resource_type,
        "total": 0.0,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": [],
        "average_daily": 0.0,
    }


# Stores the most recent billing errors so the router can surface them.
_last_billing_error: dict[str, str] = {}


# ---------------------------------------------------------------------------
# IAM – list users, roles, groups and their attached policies
# ---------------------------------------------------------------------------

def get_iam_roles(credentials: dict) -> dict:
    """Return IAM summary for the AWS account.

    Uses ``get_account_authorization_details`` to fetch all users, roles, and
    groups with their attached/inline policies in a single paginated scan
    (instead of N separate API calls per entity).  MFA checks for each user
    are then executed concurrently.  Customer-managed and attached AWS-managed
    policies are fetched in parallel.

    Returns a dict with:
      - ``account_id``   : the AWS account ID
      - ``users``        : list of IAM users (name, arn, mfa_enabled, groups, policies)
      - ``roles``        : list of IAM roles (name, arn, policies)
      - ``groups``       : list of IAM groups (name, arn, policies)
      - ``policies``     : list of IAM managed policies (name, arn, type, attachment_count)
      - ``error``        : error message if the call failed (instead of the above)
    """
    if not credentials.get("access_key_id") or not credentials.get("secret_access_key"):
        return _mock_iam_data()
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore

        boto_config = Config(
            max_pool_connections=30,
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2},
        )
        boto_session = boto3.Session(
            aws_access_key_id=credentials.get("access_key_id"),
            aws_secret_access_key=credentials.get("secret_access_key"),
            region_name=credentials.get("region", "us-east-1"),
        )
        iam = boto_session.client("iam", config=boto_config)
        sts = boto_session.client("sts", config=boto_config)

        # ── Fetch account ID and full IAM authorization details in parallel ────
        def _get_account_id() -> str:
            return sts.get_caller_identity()["Account"]

        def _get_auth_details():
            """Single paginated scan returns users, roles, groups + their policies."""
            user_details: list[dict] = []
            role_details: list[dict] = []
            group_details: list[dict] = []
            paginator = iam.get_paginator("get_account_authorization_details")
            for page in paginator.paginate():
                user_details.extend(page.get("UserDetailList", []))
                role_details.extend(page.get("RoleDetailList", []))
                group_details.extend(page.get("GroupDetailList", []))
            return user_details, role_details, group_details

        def _get_policies():
            """Fetch customer-managed and in-use AWS-managed policies."""
            policies: list[dict] = []
            # Customer-managed policies
            for page in iam.get_paginator("list_policies").paginate(Scope="Local"):
                for p in page.get("Policies", []):
                    create_date = p.get("CreateDate", "")
                    update_date = p.get("UpdateDate", "")
                    policies.append({
                        "name": p["PolicyName"],
                        "arn": p["Arn"],
                        "policy_id": p.get("PolicyId", ""),
                        "type": "Customer managed",
                        "attachment_count": p.get("AttachmentCount", 0),
                        "description": p.get("Description", ""),
                        "path": p.get("Path", "/"),
                        "default_version_id": p.get("DefaultVersionId", ""),
                        "create_date": create_date.isoformat() if hasattr(create_date, "isoformat") else str(create_date),
                        "update_date": update_date.isoformat() if hasattr(update_date, "isoformat") else str(update_date),
                    })
            # AWS-managed policies that are currently attached to at least one entity
            for page in iam.get_paginator("list_policies").paginate(Scope="AWS", OnlyAttached=True):
                for p in page.get("Policies", []):
                    create_date = p.get("CreateDate", "")
                    update_date = p.get("UpdateDate", "")
                    policies.append({
                        "name": p["PolicyName"],
                        "arn": p["Arn"],
                        "policy_id": p.get("PolicyId", ""),
                        "type": "AWS managed",
                        "attachment_count": p.get("AttachmentCount", 0),
                        "description": p.get("Description", ""),
                        "path": p.get("Path", "/"),
                        "default_version_id": p.get("DefaultVersionId", ""),
                        "create_date": create_date.isoformat() if hasattr(create_date, "isoformat") else str(create_date),
                        "update_date": update_date.isoformat() if hasattr(update_date, "isoformat") else str(update_date),
                    })
            return policies

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_acct = pool.submit(_get_account_id)
            f_details = pool.submit(_get_auth_details)
            f_policies = pool.submit(_get_policies)
            account_id = f_acct.result()
            user_details, role_details, group_details = f_details.result()
            policies_list = f_policies.result()

        # ── Check MFA for all users concurrently ───────────────────────────────
        def _has_mfa(username: str) -> bool:
            try:
                return len(iam.list_mfa_devices(UserName=username).get("MFADevices", [])) > 0
            except Exception:
                return False

        usernames = [u["UserName"] for u in user_details]
        if usernames:
            with ThreadPoolExecutor(max_workers=min(len(usernames), 20)) as pool:
                mfa_flags = dict(zip(usernames, pool.map(_has_mfa, usernames)))
        else:
            mfa_flags = {}

        # ── Derive group member counts from user data (no extra API calls) ──────
        group_member_counts: dict[str, int] = {}
        for u in user_details:
            for g in u.get("GroupList", []):
                group_member_counts[g] = group_member_counts.get(g, 0) + 1

        # ── Build users ────────────────────────────────────────────────────────
        users: list[dict] = []
        for u in user_details:
            username = u["UserName"]
            attached = [p["PolicyName"] for p in u.get("AttachedManagedPolicies", [])]
            inline = [p["PolicyName"] for p in u.get("UserPolicyList", [])]
            create_date = u.get("CreateDate", "")
            pwd_used = u.get("PasswordLastUsed", "")
            users.append({
                "name": username,
                "arn": u["Arn"],
                "user_id": u["UserId"],
                "mfa_enabled": mfa_flags.get(username, False),
                "groups": u.get("GroupList", []),
                "policies": attached + inline,
                "create_date": create_date.isoformat() if hasattr(create_date, "isoformat") else str(create_date),
                "password_last_used": pwd_used.isoformat() if hasattr(pwd_used, "isoformat") else str(pwd_used),
            })

        # ── Build roles ────────────────────────────────────────────────────────
        roles: list[dict] = []
        for r in role_details:
            attached = [p["PolicyName"] for p in r.get("AttachedManagedPolicies", [])]
            inline = [p["PolicyName"] for p in r.get("RolePolicyList", [])]
            create_date = r.get("CreateDate", "")
            roles.append({
                "name": r["RoleName"],
                "arn": r["Arn"],
                "policies": attached + inline,
                "create_date": create_date.isoformat() if hasattr(create_date, "isoformat") else str(create_date),
                "description": r.get("Description", ""),
            })

        # ── Build groups ───────────────────────────────────────────────────────
        groups_list: list[dict] = []
        for g in group_details:
            attached = [p["PolicyName"] for p in g.get("AttachedManagedPolicies", [])]
            inline = [p["PolicyName"] for p in g.get("GroupPolicyList", [])]
            groups_list.append({
                "name": g["GroupName"],
                "arn": g["Arn"],
                "policies": attached + inline,
                "member_count": group_member_counts.get(g["GroupName"], 0),
            })

        return {
            "account_id": account_id,
            "users": users,
            "roles": roles,
            "groups": groups_list,
            "policies": policies_list,
        }
    except Exception as exc:
        return {"error": str(exc)[:500]}


def _mock_iam_data() -> dict:
    """Return realistic mock IAM data for demo/mock sessions."""
    return {
        "account_id": "123456789012",
        "users": [
            {
                "name": "admin-user",
                "arn": "arn:aws:iam::123456789012:user/admin-user",
                "user_id": "AIDAI3PRZYKŁADOWY1",
                "mfa_enabled": True,
                "groups": ["Administrators"],
                "policies": ["AdministratorAccess"],
                "create_date": "2022-01-15",
                "password_last_used": "2024-03-01",
            },
            {
                "name": "developer-alice",
                "arn": "arn:aws:iam::123456789012:user/developer-alice",
                "user_id": "AIDAI3PRZYKŁADOWY2",
                "mfa_enabled": False,
                "groups": ["Developers"],
                "policies": ["AmazonS3ReadOnlyAccess", "AWSLambdaFullAccess"],
                "create_date": "2023-03-10",
                "password_last_used": "2024-02-28",
            },
            {
                "name": "ci-cd-user",
                "arn": "arn:aws:iam::123456789012:user/ci-cd-user",
                "user_id": "AIDAI3PRZYKŁADOWY3",
                "mfa_enabled": False,
                "groups": [],
                "policies": ["AmazonECRFullAccess", "AWSCodeDeployFullAccess"],
                "create_date": "2023-06-01",
                "password_last_used": "",
            },
            {
                "name": "data-analyst",
                "arn": "arn:aws:iam::123456789012:user/data-analyst",
                "user_id": "AIDAI3PRZYKŁADOWY4",
                "mfa_enabled": False,
                "groups": ["DataTeam"],
                "policies": ["AmazonAthenaFullAccess", "AmazonS3ReadOnlyAccess"],
                "create_date": "2023-09-20",
                "password_last_used": "2024-01-15",
            },
        ],
        "roles": [
            {
                "name": "LambdaExecutionRole",
                "arn": "arn:aws:iam::123456789012:role/LambdaExecutionRole",
                "policies": ["AWSLambdaBasicExecutionRole", "AmazonDynamoDBReadOnlyAccess"],
                "create_date": "2022-05-01",
                "description": "Execution role for Lambda functions",
            },
            {
                "name": "ECSTaskRole",
                "arn": "arn:aws:iam::123456789012:role/ECSTaskRole",
                "policies": ["AmazonS3FullAccess", "AmazonSQSFullAccess"],
                "create_date": "2022-07-15",
                "description": "Task role for ECS services",
            },
            {
                "name": "EC2AdminRole",
                "arn": "arn:aws:iam::123456789012:role/EC2AdminRole",
                "policies": ["AdministratorAccess"],
                "create_date": "2021-11-01",
                "description": "Admin role for EC2 instances",
            },
        ],
        "groups": [
            {
                "name": "Administrators",
                "arn": "arn:aws:iam::123456789012:group/Administrators",
                "policies": ["AdministratorAccess"],
                "member_count": 1,
            },
            {
                "name": "Developers",
                "arn": "arn:aws:iam::123456789012:group/Developers",
                "policies": ["AmazonS3ReadOnlyAccess", "AWSLambdaFullAccess", "AmazonEC2ReadOnlyAccess"],
                "member_count": 1,
            },
            {
                "name": "DataTeam",
                "arn": "arn:aws:iam::123456789012:group/DataTeam",
                "policies": ["AmazonAthenaFullAccess", "AmazonS3ReadOnlyAccess"],
                "member_count": 1,
            },
        ],
        "policies": [
            {
                "name": "AdminPolicy",
                "arn": "arn:aws:iam::123456789012:policy/AdminPolicy",
                "policy_id": "ANPAI3PRZYKŁADOWY1",
                "type": "Customer managed",
                "attachment_count": 1,
                "description": "Custom admin policy for internal use",
                "path": "/",
                "default_version_id": "v1",
                "create_date": "2022-01-15",
                "update_date": "2023-06-01",
            },
            {
                "name": "DeveloperPolicy",
                "arn": "arn:aws:iam::123456789012:policy/DeveloperPolicy",
                "policy_id": "ANPAI3PRZYKŁADOWY2",
                "type": "Customer managed",
                "attachment_count": 2,
                "description": "Policy granting developer access to common services",
                "path": "/",
                "default_version_id": "v3",
                "create_date": "2022-03-20",
                "update_date": "2024-01-10",
            },
            {
                "name": "AdministratorAccess",
                "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                "policy_id": "ANPAIFIR6V6BVTRAHWINE",
                "type": "AWS managed",
                "attachment_count": 2,
                "description": "Provides full access to AWS services and resources.",
                "path": "/",
                "default_version_id": "v1",
                "create_date": "2015-02-06",
                "update_date": "2015-02-06",
            },
            {
                "name": "AmazonS3ReadOnlyAccess",
                "arn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
                "policy_id": "ANPAIFIR6V6BVTRAHWINS3",
                "type": "AWS managed",
                "attachment_count": 3,
                "description": "Provides read-only access to Amazon S3.",
                "path": "/",
                "default_version_id": "v2",
                "create_date": "2015-02-06",
                "update_date": "2021-09-27",
            },
            {
                "name": "AWSLambdaFullAccess",
                "arn": "arn:aws:iam::aws:policy/AWSLambdaFullAccess",
                "policy_id": "ANPAIFIR6V6BVTRAHWINLAMBDA",
                "type": "AWS managed",
                "attachment_count": 2,
                "description": "Provides full access to AWS Lambda.",
                "path": "/",
                "default_version_id": "v1",
                "create_date": "2015-02-06",
                "update_date": "2020-11-18",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Suggestions – analyse resources, billing, and IAM for actionable items
# ---------------------------------------------------------------------------

# EC2 instance type families/sizes considered large (likely over-provisioned)
_LARGE_INSTANCE_TYPES: frozenset[str] = frozenset({
    "m5.4xlarge", "m5.8xlarge", "m5.12xlarge", "m5.16xlarge", "m5.24xlarge",
    "m6i.4xlarge", "m6i.8xlarge", "m6i.12xlarge", "m6i.16xlarge", "m6i.24xlarge",
    "c5.4xlarge", "c5.9xlarge", "c5.12xlarge", "c5.18xlarge", "c5.24xlarge",
    "c6i.4xlarge", "c6i.8xlarge", "c6i.12xlarge", "c6i.16xlarge", "c6i.24xlarge",
    "r5.4xlarge", "r5.8xlarge", "r5.12xlarge", "r5.16xlarge", "r5.24xlarge",
    "r6i.4xlarge", "r6i.8xlarge", "r6i.12xlarge", "r6i.16xlarge", "r6i.24xlarge",
    "x1.16xlarge", "x1.32xlarge", "x1e.8xlarge", "x1e.16xlarge", "x1e.32xlarge",
    "p3.8xlarge", "p3.16xlarge", "p4d.24xlarge",
    "t3.2xlarge", "t3a.2xlarge",
})

# IAM policies that grant full admin access
_ADMIN_POLICIES: frozenset[str] = frozenset({
    "AdministratorAccess",
    "PowerUserAccess",
})

# Number of consecutive inactive days before an IAM user account triggers a suggestion.
_IAM_INACTIVE_THRESHOLD_DAYS: int = 90

# Billing spend percentages used to classify severity in billing suggestions.
_BILLING_SEVERITY_CRITICAL_PCT: float = 40.0
_BILLING_SEVERITY_WARNING_PCT: float = 20.0
_BILLING_SIGNIFICANT_SPEND_PCT: float = 10.0

# Service-specific cost-reduction tips for billing suggestions.
# Each entry: (tuple of lowercase keywords to match against the CE service name,
#              short action title,
#              detailed numbered recommendation).
_SERVICE_COST_TIPS: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("ec2", "elastic compute cloud"),
        "Right-size instances and use Reserved/Spot capacity",
        "1. Run AWS Compute Optimizer to identify over-provisioned instances and right-size them.\n"
        "2. Purchase EC2 Reserved Instances (1- or 3-year) for steady-state workloads — savings up to 72%.\n"
        "3. Use EC2 Spot Instances for fault-tolerant, batch, or dev/test workloads — savings up to 90%.\n"
        "4. Enable EC2 Auto Scaling to scale down during off-peak hours automatically.\n"
        "5. Terminate stopped instances or snapshot their EBS volumes — stopped instances still incur EBS charges.\n"
        "6. Review large instance types (e.g. m5.4xlarge+) and verify CPU/memory utilisation in CloudWatch.",
    ),
    (
        ("s3", "simple storage service"),
        "Enable S3 Intelligent-Tiering and lifecycle policies",
        "1. Enable S3 Intelligent-Tiering on buckets with unpredictable access patterns to move objects to cheaper tiers automatically.\n"
        "2. Add lifecycle rules: transition objects to S3 Standard-IA after 30 days, Glacier Instant Retrieval after 90 days.\n"
        "3. Create a lifecycle rule to abort incomplete multipart uploads after 7 days.\n"
        "4. Configure non-current version expiration to remove stale object versions automatically.\n"
        "5. Use S3 Storage Lens to get account-wide visibility into storage usage and activity.\n"
        "6. Audit all buckets and delete data that is no longer required.",
    ),
    (
        ("rds", "relational database"),
        "Reserve RDS capacity, right-size instances, or use Aurora Serverless",
        "1. Purchase RDS Reserved Instances for production databases — savings up to 69%.\n"
        "2. Switch dev/test databases to Aurora Serverless v2 so they scale to zero when idle.\n"
        "3. Use RDS Performance Insights to identify under-utilised instances and downsize them.\n"
        "4. Disable Multi-AZ for non-production environments — reduces cost by approximately 50%.\n"
        "5. Shorten automated backup retention to the minimum required by your compliance policy.\n"
        "6. Enable storage autoscaling to avoid over-allocating a large fixed storage size at creation time.",
    ),
    (
        ("lambda",),
        "Tune Lambda memory and timeout, reduce unnecessary invocations",
        "1. Use AWS Lambda Power Tuning to find the cheapest memory setting for each function.\n"
        "2. Set the function timeout to the minimum needed plus a small buffer to prevent runaway executions.\n"
        "3. Use SQS batch windows to reduce invocation frequency for queue-triggered functions.\n"
        "4. Delete or disable Lambda functions that are no longer in use.\n"
        "5. Switch to arm64 (Graviton2) architecture — up to 20% better price/performance for most runtimes.\n"
        "6. Audit Lambda@Edge functions — they are billed per request at every CloudFront point of presence.",
    ),
    (
        ("eks", "elastic kubernetes service"),
        "Rightsize EKS nodes, use Spot capacity, and enable autoscaling",
        "1. Deploy Karpenter or Cluster Autoscaler to scale nodes down to actual pod demand.\n"
        "2. Use EC2 Spot Instances for non-critical node groups — savings up to 90%.\n"
        "3. Set accurate CPU and memory requests on all pods to improve node bin-packing efficiency.\n"
        "4. Use Fargate profiles for burstable workloads to avoid paying for idle EC2 node capacity.\n"
        "5. Apply cost-allocation tags to identify expensive namespaces or teams.\n"
        "6. Remove unused PersistentVolumeClaims and orphaned EBS volumes.",
    ),
    (
        ("ecs", "elastic container service"),
        "Use Fargate Spot, rightsize tasks, and enable ECS autoscaling",
        "1. Use Fargate Spot for fault-tolerant or stateless tasks — savings up to 70%.\n"
        "2. Review task CPU/memory definitions; right-size tasks that are consistently under-utilised.\n"
        "3. Enable ECS Service Auto Scaling to reduce the desired count during off-peak periods.\n"
        "4. Use Graviton2 instances for EC2-launch-type clusters for better price/performance.\n"
        "5. Consolidate low-traffic services onto shared task definitions where possible.",
    ),
    (
        ("elasticache",),
        "Reserve ElastiCache nodes and rightsize the cluster",
        "1. Purchase ElastiCache Reserved Nodes for production clusters — savings up to 55%.\n"
        "2. Analyse cache hit rate and eviction metrics; a low hit rate suggests inefficient key design.\n"
        "3. Downsize node types if memory utilisation is consistently below 50%.\n"
        "4. Enable cluster mode to spread data across shards and use smaller, cheaper node types.\n"
        "5. Disable Multi-AZ replication for non-production clusters.",
    ),
    (
        ("dynamodb",),
        "Optimise DynamoDB billing mode, indexes, and use TTL",
        "1. Switch tables with unpredictable traffic to On-Demand billing to avoid paying for unused capacity.\n"
        "2. For predictable, steady workloads use Provisioned capacity with Auto Scaling.\n"
        "3. Enable Time-to-Live (TTL) to automatically delete expired items at no extra cost.\n"
        "4. Audit Global Secondary Indexes and remove those that are unused or over-provisioned.\n"
        "5. Use the DynamoDB Standard-IA table class for tables with lower access frequency.\n"
        "6. Archive old items to S3 via DynamoDB Streams to keep hot tables lean.",
    ),
    (
        ("cloudwatch",),
        "Reduce log retention and remove unused alarms and dashboards",
        "1. Set CloudWatch log group retention to the minimum required (e.g. 7–30 days for non-audit logs).\n"
        "2. Export logs older than 30 days to S3 using subscription filters for cheap long-term storage.\n"
        "3. Replace full log ingestion with metric filters for alerting to reduce ingestion volume.\n"
        "4. Delete unused alarms, dashboards, and Contributor Insights rules.\n"
        "5. Switch from 1-second high-resolution metrics to 1-minute standard metrics where precision is not critical.",
    ),
    (
        ("elb", "load balancing", "elastic load"),
        "Consolidate idle load balancers and remove unused targets",
        "1. Identify and delete idle ALBs/NLBs with no active targets or traffic.\n"
        "2. Consolidate multiple ALBs using host-based and path-based routing rules on a single load balancer.\n"
        "3. Remove unused HTTPS listeners to reduce Load Balancer Capacity Unit (LCU) charges.\n"
        "4. Use AWS Global Accelerator instead of maintaining NLBs in every region.",
    ),
    (
        ("msk", "managed streaming"),
        "Enable MSK tiered storage and rightsize brokers",
        "1. Enable MSK Tiered Storage to offload cold partition data to S3 — significant storage savings.\n"
        "2. Rightsize broker instance types based on CPU, network throughput, and disk I/O metrics.\n"
        "3. Use MSK Serverless for variable or unpredictable Kafka workloads.\n"
        "4. Reduce the replication factor for non-critical topics from 3 to 2.\n"
        "5. Set topic retention (time and size) limits to prevent unbounded disk usage.",
    ),
    (
        ("opensearch",),
        "Move cold indices to UltraWarm/Cold storage and rightsize nodes",
        "1. Move indices older than 30 days to UltraWarm storage — up to 90% cheaper than hot nodes.\n"
        "2. Move rarely queried indices to OpenSearch Cold Storage for the lowest-cost retention.\n"
        "3. Reduce the replica count for non-production domains.\n"
        "4. Rightsize data nodes using JVM heap pressure and search latency metrics.\n"
        "5. Enable Auto-Tune to let OpenSearch automatically optimise settings for cost and performance.",
    ),
    (
        ("glue",),
        "Optimise Glue DPU allocation and use Flex execution class",
        "1. Profile Glue jobs and reduce DPU allocation — many jobs run well with 2–5 DPUs.\n"
        "2. Use the Glue Flex execution class for non-time-sensitive ETL jobs — up to 34% savings.\n"
        "3. Enable job bookmarks so Glue only processes new or changed data.\n"
        "4. Replace heavy Glue jobs with incremental Athena queries where possible.\n"
        "5. Delete unused crawlers, databases, and jobs from the Glue Data Catalog.",
    ),
    (
        ("athena",),
        "Partition data and use columnar formats to cut Athena scan costs",
        "1. Partition tables by date or other high-cardinality dimensions to reduce bytes scanned per query.\n"
        "2. Convert raw data to Parquet or ORC columnar format — reduces scanned bytes by up to 87%.\n"
        "3. Enable Athena query result reuse to avoid re-running identical recent queries.\n"
        "4. Use workgroup data usage controls to cap the scan volume per query.\n"
        "5. Delete stale query result files from S3 query result locations on a regular schedule.",
    ),
    (
        ("efs", "elastic file system"),
        "Enable EFS lifecycle policies and remove idle filesystems",
        "1. Enable EFS Intelligent-Tiering or a lifecycle policy to move files to EFS-IA after 30 days.\n"
        "2. Identify and delete EFS filesystems not mounted by any instance or Lambda function.\n"
        "3. Switch from EFS Standard to EFS One Zone for data that does not need multi-AZ durability.\n"
        "4. Use EFS Access Points to isolate application data for easier lifecycle management.",
    ),
    (
        ("vpc", "virtual private cloud", "nat gateway"),
        "Remove idle NAT Gateways and replace with VPC endpoints",
        "1. Delete unused NAT Gateways — each costs approximately $0.045/hr plus $0.045/GB data transfer.\n"
        "2. Create VPC Gateway Endpoints for S3 and DynamoDB to eliminate data-transfer costs through NAT.\n"
        "3. Review and delete idle VPC Interface Endpoints that are no longer in use.\n"
        "4. Consolidate VPCs where possible to reduce the total number of NAT Gateways required.",
    ),
    (
        ("api gateway",),
        "Switch to HTTP API and enable caching where applicable",
        "1. Migrate REST APIs to HTTP API where advanced features are not needed — up to 71% cost savings.\n"
        "2. Enable API Gateway caching for frequently requested, idempotent endpoints.\n"
        "3. Delete unused API stages, custom domain mappings, and deprecated deployments.\n"
        "4. Use usage plans and request throttling to prevent unexpected traffic spikes.",
    ),
]


def _match_service_cost_tip(svc_name: str) -> tuple[str, str] | None:
    """Return (action_title, recommendation) for a known AWS service, or None."""
    low = svc_name.lower()
    for keywords, action, rec in _SERVICE_COST_TIPS:
        if any(kw in low for kw in keywords):
            return action, rec
    return None


# Estimated maximum cost-savings percentage achievable for each AWS service
# when all recommended optimisations are applied.  These are conservative
# industry estimates used only to give users an order-of-magnitude guide.
_SAVINGS_POTENTIAL_PCT: list[tuple[tuple[str, ...], float]] = [
    (("ec2", "elastic compute cloud"), 50.0),   # RI/Spot + right-size
    (("s3", "simple storage service"), 40.0),   # lifecycle + tiering
    (("rds", "relational database"),   40.0),   # RI + right-size
    (("lambda",),                      25.0),   # memory tuning + arm64
    (("eks", "elastic kubernetes"),    45.0),   # spot + karpenter
    (("ecs", "elastic container"),     40.0),   # Fargate spot
    (("elasticache",),                 30.0),   # reserved nodes
    (("dynamodb",),                    35.0),   # on-demand/TTL
    (("cloudwatch",),                  50.0),   # log retention
    (("elb", "load balancing", "elastic load"), 30.0),
    (("msk", "managed streaming"),     40.0),   # tiered storage
    (("opensearch",),                  60.0),   # UltraWarm/Cold
    (("glue",),                        34.0),   # Flex class
    (("athena",),                      80.0),   # columnar format
    (("efs", "elastic file system"),   50.0),   # lifecycle + cleanup
    (("vpc", "virtual private cloud", "nat gateway"), 30.0),
    (("api gateway",),                 71.0),   # HTTP API migration
]


def _estimate_savings_pct(svc_name: str) -> float | None:
    """Return the estimated maximum savings percentage for a service, or None."""
    low = svc_name.lower()
    for keywords, pct in _SAVINGS_POTENTIAL_PCT:
        if any(kw in low for kw in keywords):
            return pct
    return None


def _aws_suggestion(
    sid: str,
    category: str,
    severity: str,
    suggestion_type: str,
    resource_name: str,
    resource_type: str,
    title: str,
    description: str,
    current_value: str,
    recommendation: str,
    current_cost: float | None = None,
    estimated_savings: float | None = None,
    estimated_savings_pct: float | None = None,
) -> dict:
    result: dict = {
        "id": sid,
        "category": category,
        "severity": severity,
        "type": suggestion_type,
        "resource_name": resource_name,
        "resource_type": resource_type,
        "title": title,
        "description": description,
        "current_value": current_value,
        "recommendation": recommendation,
    }
    if current_cost is not None:
        result["current_cost"] = round(current_cost, 2)
    if estimated_savings is not None:
        result["estimated_savings"] = round(estimated_savings, 2)
    if estimated_savings_pct is not None:
        result["estimated_savings_pct"] = round(estimated_savings_pct, 1)
    return result


def _suggestions_from_resources(resources: list[dict]) -> list[dict]:
    """Analyse AWS resource configurations and return a list of suggestions."""
    suggestions: list[dict] = []

    for r in resources:
        name = r.get("name", "unknown")
        rtype = r.get("type", "")

        # ── EC2 Instances ──────────────────────────────────────────────────────
        if rtype == "EC2":
            instance_type = r.get("instance_type") or r.get("size") or ""

            # Over-provisioned: large instance type
            if instance_type.lower() in _LARGE_INSTANCE_TYPES:
                suggestions.append(_aws_suggestion(
                    sid=f"res-ec2-large-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Large instance type may be over-provisioned",
                    description=(
                        f"EC2 instance '{name}' uses type '{instance_type}', which has a high "
                        "vCPU/memory footprint. If CPU and memory utilisation are consistently low, "
                        "consider right-sizing to a smaller instance type."
                    ),
                    current_value=instance_type,
                    recommendation=(
                        "Review CloudWatch CPU/memory metrics. Use AWS Compute Optimizer "
                        "for automated right-sizing recommendations."
                    ),
                ))

            # Underused: stopped instance still incurring EBS charges
            if r.get("status") == "stopped":
                suggestions.append(_aws_suggestion(
                    sid=f"res-ec2-stopped-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Stopped EC2 instance – EBS charges still apply",
                    description=(
                        f"EC2 instance '{name}' is stopped. Stopped instances do not incur "
                        "compute charges but attached EBS volumes continue to accrue costs."
                    ),
                    current_value="status: stopped",
                    recommendation=(
                        "If the instance is no longer needed, terminate it and snapshot its "
                        "EBS volumes for backup. Use AWS Instance Scheduler for periodic workloads."
                    ),
                ))

            # Security: public IP exposed
            if r.get("public_ip"):
                suggestions.append(_aws_suggestion(
                    sid=f"res-ec2-pubip-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="EC2 instance has a public IP address",
                    description=(
                        f"Instance '{name}' has a public IP '{r.get('public_ip')}'. "
                        "Directly exposing instances to the internet increases the attack surface."
                    ),
                    current_value=f"public_ip: {r.get('public_ip')}",
                    recommendation=(
                        "Place the instance behind an Application Load Balancer or use AWS "
                        "PrivateLink. Remove the public IP unless the instance must be directly "
                        "reachable from the internet."
                    ),
                ))

        # ── RDS Instances ──────────────────────────────────────────────────────
        elif rtype == "RDS":
            # Underused: Multi-AZ not enabled
            if r.get("multi_az") is False:
                suggestions.append(_aws_suggestion(
                    sid=f"res-rds-multiaz-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="RDS instance is not configured for Multi-AZ",
                    description=(
                        f"RDS instance '{name}' does not have Multi-AZ enabled. "
                        "A single-AZ deployment will have downtime during maintenance or AZ failure."
                    ),
                    current_value="multi_az: false",
                    recommendation=(
                        "Enable Multi-AZ for production databases to provide automatic failover "
                        "and minimise downtime during maintenance windows."
                    ),
                ))

            # Over-provisioned: large instance class
            instance_class = r.get("instance_class") or ""
            _large_rds_prefixes = ("db.r5", "db.r6g", "db.r6i", "db.x2g", "db.m5.4x", "db.m6g.4x")
            if any(instance_class.startswith(prefix) for prefix in _large_rds_prefixes):
                suggestions.append(_aws_suggestion(
                    sid=f"res-rds-large-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Large RDS instance class – verify workload requirements",
                    description=(
                        f"RDS instance '{name}' uses class '{instance_class}', which is a "
                        "memory-optimised or large class. If CPU and memory utilisation are low, "
                        "consider right-sizing to a smaller class."
                    ),
                    current_value=f"instance_class: {instance_class}",
                    recommendation=(
                        "Review CloudWatch RDS metrics (CPUUtilization, FreeableMemory). "
                        "Use AWS Compute Optimizer or RDS Performance Insights for rightsizing guidance."
                    ),
                ))

            # Over-provisioned: large fixed storage allocation
            try:
                storage_gb = int(r.get("storage_gb") or 0)
            except (TypeError, ValueError):
                storage_gb = 0
            if storage_gb > 1000:
                suggestions.append(_aws_suggestion(
                    sid=f"res-rds-storage-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Large RDS storage allocation",
                    description=(
                        f"RDS instance '{name}' has {storage_gb} GB of allocated storage. "
                        "Over-allocated storage incurs unnecessary cost even if mostly unused."
                    ),
                    current_value=f"storage_gb: {storage_gb}",
                    recommendation=(
                        "Enable RDS Storage Auto Scaling with a max threshold instead of "
                        "pre-allocating a large fixed storage size."
                    ),
                ))

        # ── S3 Buckets ─────────────────────────────────────────────────────────
        elif rtype == "S3":
            public_access_blocked = r.get("public_access_blocked")
            lifecycle_rules = r.get("lifecycle_rules") or 0
            versioning = r.get("versioning") or ""
            storage_size = (r.get("storage_size") or r.get("size") or "").strip()

            # Security: public access not blocked
            if public_access_blocked is False:
                suggestions.append(_aws_suggestion(
                    sid=f"res-s3-public-{name}",
                    category="resources",
                    severity="critical",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="S3 bucket public access is not blocked",
                    description=(
                        f"S3 bucket '{name}' does not have Block Public Access enabled. "
                        "Objects may be inadvertently exposed to the internet."
                    ),
                    current_value="public_access_blocked: false",
                    recommendation=(
                        "1. Enable all four Block Public Access settings on the bucket unless it intentionally hosts a public static website.\n"
                        "2. Use S3 bucket policies and ACLs to limit access to specific principals.\n"
                        "3. Enable Amazon Macie to automatically discover and protect sensitive data in S3.\n"
                        "4. Review the bucket's CORS configuration to ensure it does not expose sensitive data cross-origin."
                    ),
                ))

            # Unused: bucket with no stored data
            def _is_effectively_zero(size: str) -> bool:
                """Return True if a size string represents zero or near-zero storage."""
                if not size:
                    return True
                # Parse the leading numeric part and compare to a small threshold.
                import re as _re  # noqa: PLC0415
                m = _re.match(r"([\d.]+)", size.strip())
                if m:
                    try:
                        return float(m.group(1)) < 0.01
                    except ValueError:
                        pass
                return False
            is_empty = _is_effectively_zero(storage_size)
            if is_empty:
                suggestions.append(_aws_suggestion(
                    sid=f"res-s3-empty-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title=f"S3 bucket '{name}' appears to be empty",
                    description=(
                        f"S3 bucket '{name}' has no stored data. Empty buckets may represent "
                        "forgotten resources left over from old projects or migrations. "
                        "While an empty S3 bucket does not incur storage costs, associated "
                        "requests and replication configurations may still generate charges."
                    ),
                    current_value=f"size: {storage_size or 'unknown (empty)'}",
                    recommendation=(
                        "1. Verify whether this bucket is still actively used by any application or process.\n"
                        "2. If the bucket is no longer needed, delete it to remove an unnecessary attack surface.\n"
                        "3. Check for any S3 Event Notifications, Replication rules, or Inventory configurations that may still be running.\n"
                        "4. Use S3 Storage Lens to get account-wide visibility into bucket usage."
                    ),
                ))

            # Cost: no lifecycle policy on a large or standard bucket
            if lifecycle_rules == 0 and not is_empty:
                suggestions.append(_aws_suggestion(
                    sid=f"res-s3-lifecycle-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="No lifecycle policy on S3 bucket",
                    description=(
                        f"S3 bucket '{name}' has no lifecycle rules configured. "
                        "Infrequently accessed objects could be transitioned to S3-IA or "
                        "S3 Glacier to reduce storage costs."
                    ),
                    current_value="lifecycle_rules: 0",
                    recommendation=(
                        "1. Add a lifecycle rule to transition objects to S3 Standard-IA after 30 days.\n"
                        "2. Transition to S3 Glacier Instant Retrieval after 90 days for archival cost savings.\n"
                        "3. Enable S3 Intelligent-Tiering if the access pattern is unpredictable.\n"
                        "4. Add a rule to delete incomplete multipart uploads after 7 days."
                    ),
                ))

            # Cost: versioning without expiry
            if versioning == "Enabled" and lifecycle_rules == 0:
                suggestions.append(_aws_suggestion(
                    sid=f"res-s3-versioning-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="S3 versioning enabled with no lifecycle rule to expire old versions",
                    description=(
                        f"S3 bucket '{name}' has versioning enabled but no lifecycle rules. "
                        "Non-current object versions accumulate indefinitely, increasing costs."
                    ),
                    current_value="versioning: Enabled, lifecycle_rules: 0",
                    recommendation=(
                        "1. Add a lifecycle rule to expire non-current object versions after 30 days.\n"
                        "2. Add a rule to permanently delete objects after a suitable retention period.\n"
                        "3. Review the current storage size to understand the cost impact of accumulated versions."
                    ),
                ))

        # ── Lambda Functions ───────────────────────────────────────────────────
        elif rtype == "Lambda":
            # Over-provisioned: very high memory
            try:
                mem_mb_str = (r.get("size") or "").replace(" MB", "").strip()
                mem_mb = int(mem_mb_str) if mem_mb_str.isdigit() else 0
            except (TypeError, ValueError):
                mem_mb = 0
            if mem_mb > 1024:
                suggestions.append(_aws_suggestion(
                    sid=f"res-lambda-memory-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Lambda function memory may be over-provisioned",
                    description=(
                        f"Lambda function '{name}' is allocated {mem_mb} MB of memory. "
                        "If actual peak memory usage is much lower, this results in unnecessary cost."
                    ),
                    current_value=f"memory: {mem_mb} MB",
                    recommendation=(
                        "Use AWS Lambda Power Tuning tool or CloudWatch Lambda Insights to "
                        "identify the optimal memory setting for cost and performance."
                    ),
                ))

            # Over-provisioned: very long timeout
            try:
                timeout = int(r.get("timeout") or 0)
            except (TypeError, ValueError):
                timeout = 0
            if timeout > 300:
                suggestions.append(_aws_suggestion(
                    sid=f"res-lambda-timeout-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Lambda function has a very long timeout configured",
                    description=(
                        f"Lambda function '{name}' has a timeout of {timeout}s. "
                        "Excessively long timeouts allow runaway executions to accumulate charges."
                    ),
                    current_value=f"timeout: {timeout}s",
                    recommendation=(
                        "Set the timeout to the minimum required for normal execution plus a "
                        "reasonable buffer. Use Step Functions for long-running workflows."
                    ),
                ))

        # ── EKS Clusters ───────────────────────────────────────────────────────
        elif rtype == "EKS":
            try:
                node_count = int(r.get("node_count") or 0)
            except (TypeError, ValueError):
                node_count = 0
            if node_count > 20:
                suggestions.append(_aws_suggestion(
                    sid=f"res-eks-nodes-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="High EKS node count – verify cluster utilisation",
                    description=(
                        f"EKS cluster '{name}' has {node_count} nodes. "
                        "A large number of nodes may indicate over-provisioning if pod CPU/memory "
                        "requests do not fully utilise available capacity."
                    ),
                    current_value=f"node_count: {node_count}",
                    recommendation=(
                        "Enable Cluster Autoscaler or Karpenter to automatically scale nodes "
                        "based on actual pod scheduling demand."
                    ),
                ))

        # ── ELB Load Balancers ─────────────────────────────────────────────────
        elif rtype == "ELB":
            if r.get("scheme") == "internet-facing":
                suggestions.append(_aws_suggestion(
                    sid=f"res-elb-public-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Internet-facing load balancer – review access controls",
                    description=(
                        f"Load balancer '{name}' is internet-facing (public). "
                        "Ensure security groups, WAF rules, and listener configurations "
                        "are tightly scoped to prevent unauthorised access."
                    ),
                    current_value="scheme: internet-facing",
                    recommendation=(
                        "Attach an AWS WAF Web ACL to filter malicious traffic. "
                        "Restrict security group ingress rules to expected source IPs/CIDRs."
                    ),
                ))

        # ── VPC ────────────────────────────────────────────────────────────────
        elif rtype == "VPC":
            if r.get("is_default") is True:
                suggestions.append(_aws_suggestion(
                    sid=f"res-vpc-default-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Default VPC is in use",
                    description=(
                        f"VPC '{name}' is the AWS default VPC. Default VPCs have permissive "
                        "settings and resources deployed into them may have unexpected public "
                        "reachability."
                    ),
                    current_value="is_default: true",
                    recommendation=(
                        "Use a custom VPC with explicit subnet, route table, and security group "
                        "configurations. Consider deleting the default VPC in regions where it "
                        "is not used."
                    ),
                ))
        # ── EFS File Systems ───────────────────────────────────────────────────
        elif rtype == "EFS":
            size_str = (r.get("size") or "").strip()
            # EFS filesystem with no data stored (empty or near-zero size)
            import re as _re2  # noqa: PLC0415
            _m = _re2.match(r"([\d.]+)", size_str)
            efs_is_empty = not size_str or (bool(_m) and float(_m.group(1)) < 0.01)
            if efs_is_empty:
                suggestions.append(_aws_suggestion(
                    sid=f"res-efs-empty-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title=f"EFS filesystem '{name}' appears to have no data stored",
                    description=(
                        f"EFS filesystem '{name}' reports no stored data. An idle filesystem "
                        "that is not mounted by any instance or Lambda function still incurs "
                        "the monthly storage minimum charge and wastes capacity."
                    ),
                    current_value=f"size: {size_str or 'unknown'}",
                    recommendation=(
                        "1. Check whether any EC2 instance or Lambda function still mounts this filesystem.\n"
                        "2. If the filesystem is no longer needed, delete it to avoid ongoing charges.\n"
                        "3. If data is expected, verify that the application is writing correctly.\n"
                        "4. Enable EFS lifecycle policies so future data is automatically tiered to EFS-IA after 30 days."
                    ),
                ))
    return suggestions


def _suggestions_from_billing(billing_data: dict) -> list[dict]:
    """Analyse AWS billing data and return cost-optimisation suggestions.

    For services that are significant cost drivers the function emits a
    service-specific suggestion with concrete, actionable steps tailored to
    that service.  Generic fallback advice is used when no service-specific
    tips are available.
    """
    suggestions: list[dict] = []

    breakdown: list[dict] = billing_data.get("breakdown", [])
    total: float = billing_data.get("total", 0.0)
    if not breakdown or total <= 0:
        return suggestions

    for item in breakdown:
        svc = item.get("service", "Unknown")
        cost = item.get("cost", 0.0)
        pct = round(cost / total * 100, 1) if total > 0 else 0

        # ── Significant spenders: generate a service-specific suggestion ──────
        # Trigger for services that account for ≥ _BILLING_SIGNIFICANT_SPEND_PCT of total spend.
        if pct >= _BILLING_SIGNIFICANT_SPEND_PCT and cost > 0:
            severity = (
                "critical" if pct >= _BILLING_SEVERITY_CRITICAL_PCT
                else "warning" if pct >= _BILLING_SEVERITY_WARNING_PCT
                else "info"
            )
            tip = _match_service_cost_tip(svc)
            savings_pct = _estimate_savings_pct(svc)
            est_savings = round(cost * savings_pct / 100, 2) if savings_pct is not None else None
            if tip:
                action_title, recommendation = tip
                title = f"'{svc}' is a top cost driver ({pct}% of spend) — {action_title}"
                description = (
                    f"'{svc}' accounts for {pct}% (${cost:.2f}) of the ${total:.2f} total spend. "
                    "Review the steps below to reduce this service's cost."
                )
            else:
                title = f"'{svc}' accounts for {pct}% of total spend"
                description = (
                    f"The service '{svc}' is responsible for {pct}% (${cost:.2f}) of the "
                    f"${total:.2f} total spend. A high concentration of spend in one service "
                    "may indicate over-provisioning or unoptimised usage."
                )
                recommendation = (
                    "Review resource utilisation for this service in CloudWatch. "
                    "Consider Reserved Instances or Savings Plans for predictable workloads. "
                    "Use AWS Cost Explorer to drill into usage dimensions and identify waste."
                )
            suggestions.append(_aws_suggestion(
                sid=f"bill-top-{svc.replace(' ', '_').lower()[:40]}",
                category="billing",
                severity=severity,
                suggestion_type="overused",
                resource_name=svc,
                resource_type="Billing",
                title=title,
                description=description,
                current_value=f"${cost:.2f} / ${total:.2f} total ({pct}%)",
                recommendation=recommendation,
                current_cost=cost,
                estimated_savings=est_savings,
                estimated_savings_pct=savings_pct,
            ))

        # ── Near-zero spend: possibly a forgotten / lingering resource ────────
        elif 0 < cost < 1.0:
            suggestions.append(_aws_suggestion(
                sid=f"bill-low-{svc.replace(' ', '_').lower()[:40]}",
                category="billing",
                severity="info",
                suggestion_type="underused",
                resource_name=svc,
                resource_type="Billing",
                title=f"'{svc}' has very low spend — may be an unused service",
                description=(
                    f"Service '{svc}' shows a cost of ${cost:.2f} in the selected period. "
                    "A very small charge often indicates a lingering resource (e.g. static IP, "
                    "idle NAT Gateway, or an unused API stage) that can safely be removed."
                ),
                current_value=f"${cost:.2f}",
                recommendation=(
                    f"Open the '{svc}' console and list all active resources. "
                    "Delete or disable anything that is no longer in use. "
                    "Use AWS Resource Explorer to find orphaned resources across regions."
                ),
                current_cost=cost,
                estimated_savings=cost,
                estimated_savings_pct=100.0,
            ))

    # ── Detect rapid cost growth across the period ────────────────────────────
    daily_costs: list[dict] = billing_data.get("daily_costs", [])
    if len(daily_costs) >= 4:
        mid = len(daily_costs) // 2
        first_avg = sum(d.get("cost", 0) for d in daily_costs[:mid]) / mid
        second_avg = sum(d.get("cost", 0) for d in daily_costs[mid:]) / (len(daily_costs) - mid)
        if first_avg > 0 and second_avg > first_avg * 1.5:
            growth_pct = round((second_avg - first_avg) / first_avg * 100, 1)
            suggestions.append(_aws_suggestion(
                sid="bill-cost-growth",
                category="billing",
                severity="warning",
                suggestion_type="overused",
                resource_name="Overall",
                resource_type="Billing",
                title=f"Daily spend growing rapidly (+{growth_pct}% in second half of period)",
                description=(
                    f"Average daily spend increased by {growth_pct}% in the second half of the "
                    "selected billing period. This may signal new workloads, a misconfiguration, "
                    "or runaway auto-scaling."
                ),
                current_value=f"avg daily: ${first_avg:.2f} → ${second_avg:.2f}",
                recommendation=(
                    "1. Set up AWS Budgets alerts to notify you when spend exceeds a threshold.\n"
                    "2. Enable AWS Cost Anomaly Detection to automatically flag unusual spend.\n"
                    "3. Use Cost Explorer to inspect recently created or scaled resources.\n"
                    "4. Check for unintentional data-transfer charges (cross-region or internet egress)."
                ),
            ))

    return suggestions


def _suggestions_from_iam(iam_data: dict) -> list[dict]:
    """Analyse AWS IAM data and return security / hygiene suggestions."""
    from datetime import datetime, timezone  # noqa: PLC0415

    suggestions: list[dict] = []

    users: list[dict] = iam_data.get("users", [])
    roles: list[dict] = iam_data.get("roles", [])

    # Users without MFA
    for user in users:
        if not user.get("mfa_enabled", True):
            suggestions.append(_aws_suggestion(
                sid=f"iam-no-mfa-{user['name'][:40]}",
                category="iam",
                severity="critical",
                suggestion_type="security",
                resource_name=user["name"],
                resource_type="IAM User",
                title=f"IAM user '{user['name']}' does not have MFA enabled",
                description=(
                    f"User '{user['name']}' does not have multi-factor authentication (MFA) "
                    "enabled. Without MFA, a compromised password gives an attacker full "
                    "access to the account."
                ),
                current_value="mfa_enabled: false",
                recommendation=(
                    "1. Enable a virtual or hardware MFA device for this user in the IAM console.\n"
                    "2. Add an IAM policy condition (aws:MultiFactorAuthPresent: true) to enforce MFA for sensitive operations.\n"
                    "3. Consider using AWS IAM Identity Center (SSO) with MFA for centralised access management.\n"
                    "4. Use hardware MFA tokens (e.g. YubiKey) for privileged / admin accounts."
                ),
            ))

    # Users or roles with AdministratorAccess
    for user in users:
        policies = user.get("policies", [])
        admin_policies = [p for p in policies if p in _ADMIN_POLICIES]
        if admin_policies:
            suggestions.append(_aws_suggestion(
                sid=f"iam-admin-user-{user['name'][:40]}",
                category="iam",
                severity="warning",
                suggestion_type="security",
                resource_name=user["name"],
                resource_type="IAM User",
                title=f"IAM user '{user['name']}' has broad admin policy",
                description=(
                    f"User '{user['name']}' has the policy/policies: {', '.join(admin_policies)}. "
                    "These policies grant unrestricted access to all AWS services and resources, "
                    "violating the principle of least privilege."
                ),
                current_value=f"policies: {', '.join(admin_policies)}",
                recommendation=(
                    "1. Replace AdministratorAccess with a custom IAM policy scoped to the specific services this user needs.\n"
                    "2. Use AWS IAM Access Analyzer to identify which permissions are actually used and remove the rest.\n"
                    "3. Reserve admin access for break-glass emergency accounts, protected by MFA and tightly audited.\n"
                    "4. Enable AWS CloudTrail to log all API calls made by this user for audit purposes."
                ),
            ))

    # Roles with AdministratorAccess
    for role in roles:
        policies = role.get("policies", [])
        admin_policies = [p for p in policies if p in _ADMIN_POLICIES]
        if admin_policies:
            suggestions.append(_aws_suggestion(
                sid=f"iam-admin-role-{role['name'][:40]}",
                category="iam",
                severity="warning",
                suggestion_type="security",
                resource_name=role["name"],
                resource_type="IAM Role",
                title=f"IAM role '{role['name']}' has broad admin policy",
                description=(
                    f"Role '{role['name']}' has the policy/policies: {', '.join(admin_policies)}. "
                    "Roles with AdministratorAccess can be assumed to gain unrestricted AWS access."
                ),
                current_value=f"policies: {', '.join(admin_policies)}",
                recommendation=(
                    "1. Scope the role to only the permissions it genuinely requires.\n"
                    "2. Use IAM Access Analyzer to identify unused permissions and tighten the policy.\n"
                    "3. Add a condition to the trust policy restricting which principals or services can assume the role.\n"
                    "4. Enable AWS CloudTrail and set alerts for any AssumeRole calls on this role."
                ),
            ))

    # Users with no groups (direct policy attachment – harder to audit)
    for user in users:
        if not user.get("groups") and user.get("policies"):
            suggestions.append(_aws_suggestion(
                sid=f"iam-no-group-{user['name'][:40]}",
                category="iam",
                severity="info",
                suggestion_type="security",
                resource_name=user["name"],
                resource_type="IAM User",
                title=f"IAM user '{user['name']}' has policies attached directly (not via a group)",
                description=(
                    f"User '{user['name']}' has policies attached directly rather than through "
                    "a group. Direct policy attachments make it harder to audit and manage "
                    "permissions at scale."
                ),
                current_value=f"groups: none, policies: {', '.join(user.get('policies', [])[:3])}",
                recommendation=(
                    "1. Create or assign an appropriate IAM group with the required policies.\n"
                    "2. Add the user to that group and detach the directly attached policies.\n"
                    "3. Managing permissions at the group level makes audits and permission changes much easier.\n"
                    "4. Use AWS IAM Identity Center (SSO) for centralised, scalable permission management."
                ),
            ))

    # ── Inactive users: no console login for 90+ days ─────────────────────────
    now = datetime.now(timezone.utc)
    for user in users:
        last_used_raw = user.get("password_last_used", "")
        if not last_used_raw:
            continue  # No password / programmatic-only user — handled separately below
        last_used_str = str(last_used_raw)
        try:
            # Replace trailing 'Z' only (not any 'Z' within timezone offsets).
            if last_used_str.endswith("Z"):
                last_used_str = last_used_str[:-1] + "+00:00"
            last_used = datetime.fromisoformat(last_used_str)
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            days_inactive = (now - last_used).days
        except (ValueError, TypeError):
            # Try parsing a date-only string (YYYY-MM-DD)
            date_part = last_used_str[:10]
            if len(date_part) < 10:
                continue
            try:
                last_used = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_inactive = (now - last_used).days
            except (ValueError, TypeError):
                continue
        if days_inactive >= _IAM_INACTIVE_THRESHOLD_DAYS:
            last_used_display = last_used_str[:10] if len(last_used_str) >= 10 else last_used_str
            suggestions.append(_aws_suggestion(
                sid=f"iam-inactive-user-{user['name'][:40]}",
                category="iam",
                severity="warning",
                suggestion_type="underused",
                resource_name=user["name"],
                resource_type="IAM User",
                title=f"IAM user '{user['name']}' has not logged in for {days_inactive} days",
                description=(
                    f"User '{user['name']}' last logged into the AWS console {days_inactive} days ago "
                    f"(last active: {last_used_display}). Long-inactive accounts are a security risk "
                    "because they represent an unused attack surface with potentially broad permissions."
                ),
                current_value=f"password_last_used: {last_used_display}, days_inactive: {days_inactive}",
                recommendation=(
                    "1. Disable the console login (delete the login profile) for this user if they no longer need AWS console access.\n"
                    "2. Review any active access keys for this user and rotate or deactivate them.\n"
                    "3. If the user account is no longer needed, remove it entirely after verifying no services depend on it.\n"
                    "4. Use AWS IAM credential report (aws iam generate-credential-report) regularly to audit inactive accounts."
                ),
            ))

    # ── Programmatic-only users with no recent activity ───────────────────────
    for user in users:
        last_used_raw = user.get("password_last_used", "")
        policies = user.get("policies", [])
        groups = user.get("groups", [])
        # A user with policies but no password last used and no groups is likely a service/CI account
        if not last_used_raw and (policies or groups):
            suggestions.append(_aws_suggestion(
                sid=f"iam-no-login-{user['name'][:40]}",
                category="iam",
                severity="info",
                suggestion_type="underused",
                resource_name=user["name"],
                resource_type="IAM User",
                title=f"IAM user '{user['name']}' has never used the AWS console",
                description=(
                    f"User '{user['name']}' has never logged into the AWS Management Console. "
                    "If this is a service or CI/CD account, consider replacing it with an IAM role "
                    "or using AWS IAM Identity Center for better security and auditability."
                ),
                current_value="password_last_used: never",
                recommendation=(
                    "1. If this is a machine/service account, replace it with an IAM role assumed via EC2 instance profile, ECS task role, or GitHub OIDC.\n"
                    "2. Roles are more secure than long-lived access keys because they issue short-term credentials.\n"
                    "3. If access keys are present, audit when they were last used (aws iam list-access-keys) and rotate or deactivate unused keys.\n"
                    "4. Consider using AWS Secrets Manager or Parameter Store to securely distribute credentials if keys are required."
                ),
            ))

    return suggestions


def get_suggestions(credentials: dict) -> dict:
    """Analyse AWS resources, billing, and IAM to produce actionable suggestions.

    Resources, billing, and IAM data are fetched concurrently so the total
    latency is bounded by the slowest of the three rather than their sum.

    Returns a dict with keys:
      - ``suggestions``      : list of suggestion dicts
      - ``summary``          : counts per category and severity
      - ``resources_error``  : error string if resource fetch failed (or None)
      - ``billing_error``    : error string if billing fetch failed (or None)
      - ``iam_error``        : error string if IAM fetch failed (or None)
    """
    from datetime import date, timedelta  # noqa: PLC0415

    end = date.today()
    start = end - timedelta(days=89)

    resources_error: str | None = None
    billing_error: str | None = None
    iam_error: str | None = None

    # ── Fetch resources, billing, and IAM concurrently ────────────────────────
    def _fetch_resources():
        try:
            resources = get_resources(credentials)
            err = _last_resources_error.get("error")
            return resources, _suggestions_from_resources(resources), err
        except Exception as exc:
            return [], [], str(exc)[:300]

    def _fetch_billing():
        try:
            billing_data = get_overall_billing(credentials, start, end)
            err = _last_billing_error.get("error")
            return billing_data, _suggestions_from_billing(billing_data), err
        except Exception as exc:
            return {}, [], str(exc)[:300]

    def _fetch_iam():
        try:
            iam_data = get_iam_roles(credentials)
            if "error" in iam_data:
                return iam_data, [], iam_data["error"]
            return iam_data, _suggestions_from_iam(iam_data), None
        except Exception as exc:
            return {}, [], str(exc)[:300]

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_res = pool.submit(_fetch_resources)
        f_bill = pool.submit(_fetch_billing)
        f_iam = pool.submit(_fetch_iam)
        resources_data, res_suggestions, resources_error = f_res.result()
        billing_data, bill_suggestions, billing_error = f_bill.result()
        iam_data, iam_suggestions, iam_error = f_iam.result()

    heuristic_suggestions = res_suggestions + bill_suggestions + iam_suggestions
    vertex_suggestions, vertex_error = generate_vertexai_suggestions(
        provider="aws",
        resources_data=resources_data,
        billing_data=billing_data,
        iam_data=iam_data,
        heuristic_suggestions=heuristic_suggestions,
        billing_start=start,
        billing_end=end,
    )
    all_suggestions = vertex_suggestions + heuristic_suggestions
    if vertex_error and not billing_error:
        billing_error = f"Vertex AI fallback: {vertex_error}"

    # ── Deduplicate by id (keep first occurrence) ──────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for s in all_suggestions:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)

    # ── Summary counts ─────────────────────────────────────────────────────────
    summary: dict[str, dict[str, int]] = {
        "resources": {"total": 0, "critical": 0, "warning": 0, "info": 0},
        "billing":   {"total": 0, "critical": 0, "warning": 0, "info": 0},
        "iam":       {"total": 0, "critical": 0, "warning": 0, "info": 0},
    }
    for s in unique:
        cat = s.get("category", "resources")
        sev = s.get("severity", "info")
        if cat in summary:
            summary[cat]["total"] += 1
            if sev in summary[cat]:
                summary[cat][sev] += 1

    return {
        "suggestions": unique,
        "summary": summary,
        "resources_error": resources_error,
        "billing_error": billing_error,
        "iam_error": iam_error,
        "billing_period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
    }
