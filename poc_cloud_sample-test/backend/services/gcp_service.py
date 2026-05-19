"""GCP service – attempts real SDK calls, falls back to mock data on error.

Resources: uses Cloud Asset Inventory (v1) to list ALL resource types in the
project, not just Compute Engine instances.

Billing: GCP does not expose historical cost data via a simple REST API
(it requires a BigQuery billing export).  We call the Cloud Billing API to
verify the billing account linked to the project, then use deterministic mock
figures for cost amounts.  The response includes the real billing account name
when available so the UI can display it.
"""
from __future__ import annotations

import json
from datetime import date

from . import mock_service
from .vertexai_suggestions import generate_vertexai_suggestions

# ---------------------------------------------------------------------------
# Friendly display names for Cloud Asset Inventory asset types
# ---------------------------------------------------------------------------

_ASSET_TYPE_MAP: dict[str, str] = {
    # Compute
    "compute.googleapis.com/Instance": "Compute Engine",
    "compute.googleapis.com/Disk": "Persistent Disk",
    "compute.googleapis.com/Snapshot": "Disk Snapshot",
    "compute.googleapis.com/Image": "Compute Image",
    "compute.googleapis.com/Network": "VPC Network",
    "compute.googleapis.com/Subnetwork": "Subnet",
    "compute.googleapis.com/Firewall": "Firewall Rule",
    "compute.googleapis.com/Route": "Route",
    "compute.googleapis.com/Router": "Cloud Router",
    "compute.googleapis.com/Address": "IP Address",
    "compute.googleapis.com/ForwardingRule": "Load Balancer",
    "compute.googleapis.com/BackendService": "Backend Service",
    "compute.googleapis.com/HealthCheck": "Health Check",
    "compute.googleapis.com/TargetHttpProxy": "HTTP Proxy",
    "compute.googleapis.com/TargetHttpsProxy": "HTTPS Proxy",
    "compute.googleapis.com/UrlMap": "URL Map",
    "compute.googleapis.com/SslCertificate": "SSL Certificate",
    "compute.googleapis.com/InstanceTemplate": "Instance Template",
    "compute.googleapis.com/InstanceGroupManager": "Instance Group",
    "compute.googleapis.com/Autoscaler": "Autoscaler",
    "compute.googleapis.com/VpnGateway": "VPN Gateway",
    "compute.googleapis.com/VpnTunnel": "VPN Tunnel",
    "compute.googleapis.com/InterconnectAttachment": "Interconnect",
    "compute.googleapis.com/SecurityPolicy": "Cloud Armor",
    # Storage
    "storage.googleapis.com/Bucket": "Cloud Storage",
    "file.googleapis.com/Instance": "Filestore",
    # Databases
    "sqladmin.googleapis.com/Instance": "Cloud SQL",
    "bigtable.googleapis.com/Instance": "Cloud Bigtable",
    "bigtable.googleapis.com/Cluster": "Cloud Bigtable",
    "spanner.googleapis.com/Instance": "Cloud Spanner",
    "spanner.googleapis.com/Database": "Cloud Spanner",
    "firestore.googleapis.com/Database": "Firestore",
    "redis.googleapis.com/Instance": "Cloud Memorystore",
    "memcache.googleapis.com/Instance": "Cloud Memorystore",
    "alloydb.googleapis.com/Cluster": "AlloyDB",
    # Containers
    "container.googleapis.com/Cluster": "GKE",
    "run.googleapis.com/Service": "Cloud Run",
    # Serverless
    "cloudfunctions.googleapis.com/CloudFunction": "Cloud Functions",
    "cloudfunctions.googleapis.com/Function": "Cloud Functions",
    # Big Data
    "bigquery.googleapis.com/Dataset": "BigQuery",
    "bigquery.googleapis.com/Table": "BigQuery Table",
    "bigquery.googleapis.com/Reservation": "BigQuery Reservation",
    "dataflow.googleapis.com/Job": "Dataflow",
    "dataproc.googleapis.com/Cluster": "Dataproc",
    "composer.googleapis.com/Environment": "Cloud Composer",
    "dataform.googleapis.com/Repository": "Dataform",
    "dataplex.googleapis.com/Lake": "Dataplex",
    "datafusion.googleapis.com/Instance": "Cloud Data Fusion",
    # Messaging
    "pubsub.googleapis.com/Topic": "Pub/Sub",
    "pubsub.googleapis.com/Subscription": "Pub/Sub Subscription",
    "pubsublite.googleapis.com/Topic": "Pub/Sub Lite",
    # App Platform
    "appengine.googleapis.com/Application": "App Engine",
    "appengine.googleapis.com/Service": "App Engine Service",
    # Networking
    "dns.googleapis.com/ManagedZone": "Cloud DNS",
    "vpcaccess.googleapis.com/Connector": "VPC Connector",
    "networkconnectivity.googleapis.com/Hub": "Network Connectivity",
    # AI / ML
    "aiplatform.googleapis.com/Dataset": "Vertex AI",
    "aiplatform.googleapis.com/Endpoint": "Vertex AI",
    "aiplatform.googleapis.com/Model": "Vertex AI",
    "notebooks.googleapis.com/Instance": "Vertex AI Notebooks",
    "notebooks.googleapis.com/Runtime": "Vertex AI Notebooks",
    # DevOps / Artifact
    "cloudbuild.googleapis.com/Build": "Cloud Build",
    "artifactregistry.googleapis.com/Repository": "Artifact Registry",
    "sourcerepo.googleapis.com/Repo": "Cloud Source Repositories",
    # Security
    "iam.googleapis.com/ServiceAccount": "Service Account",
    "cloudkms.googleapis.com/CryptoKey": "Cloud KMS",
    "cloudkms.googleapis.com/KeyRing": "Cloud KMS",
    "secretmanager.googleapis.com/Secret": "Secret Manager",
    "binaryauthorization.googleapis.com/Policy": "Binary Authorization",
    # Monitoring / Logging
    "monitoring.googleapis.com/AlertPolicy": "Cloud Monitoring",
    "monitoring.googleapis.com/UptimeCheckConfig": "Cloud Monitoring",
    "logging.googleapis.com/LogSink": "Cloud Logging",
    "logging.googleapis.com/LogMetric": "Cloud Logging",
    # API / Scheduler / Workflows
    "apigateway.googleapis.com/Gateway": "API Gateway",
    "apigateway.googleapis.com/Api": "API Gateway",
    "endpoints.googleapis.com/Service": "Cloud Endpoints",
    "cloudscheduler.googleapis.com/Job": "Cloud Scheduler",
    "cloudtasks.googleapis.com/Queue": "Cloud Tasks",
    "workflows.googleapis.com/Workflow": "Cloud Workflows",
    "certificatemanager.googleapis.com/Certificate": "Certificate Manager",
}

# Resource types that are infrastructure constructs and carry no direct cost.
# They are excluded from the billing breakdown to keep it meaningful.
_FREE_RESOURCE_TYPES: frozenset[str] = frozenset({
    "Service Account",
    "Firewall Rule",
    "Route",
    "Subnet",
    "URL Map",
    "HTTP Proxy",
    "HTTPS Proxy",
    "Backend Service",
    "Health Check",
    "SSL Certificate",
    "Instance Template",
    "Autoscaler",
    "Compute Image",
    "Disk Snapshot",
    "VPC Connector",
    "Binary Authorization",
    "Cloud Endpoints",
    "Dataform",
    "Network Connectivity",
    "App Engine Service",
    "Pub/Sub Subscription",
    "BigQuery Table",
    "BigQuery Reservation",
})


def _build_creds(credentials: dict):
    """Return Google credentials from the stored dict.

    Supports two authentication types:
    - ``auth_type == "oauth"``: uses an OAuth 2.0 user access token obtained via
      the GCP OAuth login flow.
    - default: uses a service-account JSON key (legacy / service-account flow).
    """
    if credentials.get("auth_type") == "oauth":
        from google.oauth2.credentials import Credentials  # type: ignore

        return Credentials(
            token=credentials.get("token"),
            refresh_token=credentials.get("refresh_token"),
            token_uri=credentials.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            scopes=credentials.get("scopes"),
        )

    from google.oauth2 import service_account  # type: ignore

    sa_info = json.loads(credentials.get("service_account_json", "{}"))
    return service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


# ---------------------------------------------------------------------------
# Resources – Cloud Asset Inventory
# ---------------------------------------------------------------------------

_MAX_PREVIEW_LENGTH = 80  # max characters for inline text previews (filter expressions, docs)


def _parse_date(timestamp: str) -> str | None:
    """Return the date portion (YYYY-MM-DD) from an ISO-8601 timestamp string."""
    if not timestamp:
        return None
    try:
        from datetime import datetime  # noqa: PLC0415
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
    except (ValueError, AttributeError):
        return timestamp.split("T")[0] or None


def _extract_config(asset_type: str, resource_data: dict) -> dict:
    """Extract every available configuration field from Cloud Asset Inventory resource data."""
    config: dict = {}

    if asset_type == "compute.googleapis.com/Instance":
        machine_type = resource_data.get("machineType", "")
        config["machine_type"] = machine_type.split("/")[-1] if machine_type else None
        zone = resource_data.get("zone", "")
        config["zone"] = zone.split("/")[-1] if zone else None
        config["cpu_platform"] = resource_data.get("cpuPlatform")
        config["min_cpu_platform"] = resource_data.get("minCpuPlatform")
        config["deletion_protection"] = resource_data.get("deletionProtection")
        config["can_ip_forward"] = resource_data.get("canIpForward")
        config["preemptible"] = resource_data.get("scheduling", {}).get("preemptible")
        # Boot disk details
        disks = resource_data.get("disks", [])
        boot = next((d for d in disks if d.get("boot")), None)
        if boot:
            config["boot_disk_size_gb"] = boot.get("diskSizeGb")
            boot_src = boot.get("source", "")
            config["boot_disk_name"] = boot_src.split("/")[-1] if boot_src else None
            config["boot_disk_type"] = boot.get("diskType", "").split("/")[-1] or None
        config["disk_count"] = len(disks)
        attached = [d.get("source", "").split("/")[-1] for d in disks if d.get("source")]
        config["attached_disks"] = ",".join(attached) if attached else None
        # Network
        nics = resource_data.get("networkInterfaces", [])
        if nics:
            nic = nics[0]
            net = nic.get("network", "")
            config["network"] = net.split("/")[-1] if net else None
            sub = nic.get("subnetwork", "")
            config["subnetwork"] = sub.split("/")[-1] if sub else None
            config["network_ip"] = nic.get("networkIP")
            acs = nic.get("accessConfigs", [])
            config["external_ip"] = acs[0].get("natIP") if acs else None
        # Shielded VM
        shielded = resource_data.get("shieldedInstanceConfig", {})
        config["shielded_secure_boot"] = shielded.get("enableSecureBoot")
        # Service account
        sas = resource_data.get("serviceAccounts", [])
        config["service_account"] = sas[0].get("email") if sas else None

    elif asset_type == "compute.googleapis.com/Disk":
        config["disk_size_gb"] = resource_data.get("sizeGb")
        disk_type = resource_data.get("type", "")
        config["disk_type"] = disk_type.split("/")[-1] if disk_type else None
        zone = resource_data.get("zone", "")
        config["zone"] = zone.split("/")[-1] if zone else None
        src_image = resource_data.get("sourceImage", "")
        config["source_image"] = src_image.split("/")[-1] if src_image else None
        config["snapshot_schedule_count"] = len(resource_data.get("resourcePolicies", []))
        users = resource_data.get("users", [])
        config["in_use_by"] = ",".join(u.split("/")[-1] for u in users) if users else None
        enc = resource_data.get("diskEncryptionKey", {})
        config["encryption"] = "CMEK" if enc.get("kmsKeyName") else "Google-managed"
        config["physical_block_size_bytes"] = resource_data.get("physicalBlockSizeBytes")

    elif asset_type == "storage.googleapis.com/Bucket":
        config["storage_class"] = resource_data.get("storageClass")
        loc_type = resource_data.get("locationType")
        config["location_type"] = loc_type.upper() if loc_type else None
        versioning = resource_data.get("versioning", {})
        config["versioning"] = "Enabled" if versioning.get("enabled") else "Disabled"
        lifecycle = resource_data.get("lifecycle", {})
        rules = lifecycle.get("rule", [])
        config["lifecycle_rules"] = len(rules) if rules else 0
        iam_config = resource_data.get("iamConfiguration", {})
        ubla = iam_config.get("uniformBucketLevelAccess", {})
        config["uniform_bucket_level_access"] = ubla.get("enabled", False)
        config["public_access"] = "Blocked" if iam_config.get("publicAccessPrevention") == "enforced" else "Allowed"
        enc = resource_data.get("encryption", {})
        config["encryption"] = "CMEK" if enc.get("defaultKmsKeyName") else "Google-managed"
        config["logging"] = "Enabled" if resource_data.get("logging") else "Disabled"
        retention = resource_data.get("retentionPolicy", {})
        config["retention_policy_days"] = int(retention.get("retentionPeriod", 0)) // 86400 if retention.get("retentionPeriod") else None
        config["requester_pays"] = resource_data.get("billing", {}).get("requesterPays", False)
        config["cors_rules"] = len(resource_data.get("cors", []))

    elif asset_type == "bigquery.googleapis.com/Dataset":
        config["location"] = resource_data.get("location")
        config["dataset_id"] = resource_data.get("datasetReference", {}).get("datasetId")
        config["default_table_expiration_ms"] = resource_data.get("defaultTableExpirationMs")
        config["default_partition_expiration_ms"] = resource_data.get("defaultPartitionExpirationMs")
        config["description"] = resource_data.get("description") or None
        access = resource_data.get("access", [])
        config["access_entries"] = len(access) if access else None
        config["labels_count"] = len(resource_data.get("labels", {}))
        enc = resource_data.get("defaultEncryptionConfiguration", {})
        config["kms_key"] = enc.get("kmsKeyName", "").split("/")[-2] if enc.get("kmsKeyName") else None

    elif asset_type == "sqladmin.googleapis.com/Instance":
        config["database_version"] = resource_data.get("databaseVersion")
        settings = resource_data.get("settings", {})
        config["tier"] = settings.get("tier")
        config["disk_size_gb"] = settings.get("dataDiskSizeGb")
        config["disk_type"] = settings.get("dataDiskType")
        config["availability_type"] = settings.get("availabilityType")
        backup = settings.get("backupConfiguration", {})
        config["backup_enabled"] = backup.get("enabled")
        config["point_in_time_recovery"] = backup.get("pointInTimeRecoveryEnabled")
        config["connection_name"] = resource_data.get("connectionName")
        ips = resource_data.get("ipAddresses", [])
        for ip in ips:
            if ip.get("type") == "PRIMARY":
                config["ip_address"] = ip.get("ipAddress")
            elif ip.get("type") == "OUTGOING":
                config["public_ip"] = ip.get("ipAddress")
        maint = settings.get("maintenanceWindow", {})
        if maint:
            day_map = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
                       5: "Friday", 6: "Saturday", 7: "Sunday"}
            day = day_map.get(maint.get("day", 0), "")
            hour = maint.get("hour", 0)
            config["maintenance_window"] = f"{day} {hour:02d}:00" if day else None
        config["deletion_protection"] = settings.get("deletionProtectionEnabled")
        flags = settings.get("databaseFlags", [])
        config["database_flags"] = ",".join(f"{f['name']}={f['value']}" for f in flags) if flags else None

    elif asset_type == "container.googleapis.com/Cluster":
        config["current_master_version"] = resource_data.get("currentMasterVersion")
        config["node_count"] = resource_data.get("currentNodeCount")
        node_config = resource_data.get("nodeConfig", {})
        config["node_machine_type"] = node_config.get("machineType")
        config["node_disk_size_gb"] = node_config.get("diskSizeGb")
        config["node_disk_type"] = node_config.get("diskType")
        config["node_image_type"] = node_config.get("imageType")
        network = resource_data.get("network", "")
        config["network"] = network.split("/")[-1] if network else None
        sub = resource_data.get("subnetwork", "")
        config["subnetwork"] = sub.split("/")[-1] if sub else None
        config["node_pool_count"] = len(resource_data.get("nodePools", []))
        autopilot = resource_data.get("autopilot", {})
        config["autopilot"] = autopilot.get("enabled", False)
        private = resource_data.get("privateClusterConfig", {})
        config["private_cluster"] = private.get("enablePrivateNodes", False)
        release = resource_data.get("releaseChannel", {})
        config["release_channel"] = release.get("channel")
        config["services_ipv4_cidr"] = resource_data.get("servicesIpv4Cidr")
        config["cluster_ipv4_cidr"] = resource_data.get("clusterIpv4Cidr")
        config["logging_service"] = resource_data.get("loggingService")
        config["monitoring_service"] = resource_data.get("monitoringService")

    elif asset_type in ("cloudfunctions.googleapis.com/CloudFunction", "cloudfunctions.googleapis.com/Function"):
        config["runtime"] = resource_data.get("runtime")
        config["available_memory_mb"] = resource_data.get("availableMemoryMb")
        config["entry_point"] = resource_data.get("entryPoint")
        config["timeout"] = resource_data.get("timeout")
        config["min_instances"] = resource_data.get("minInstances", 0)
        config["max_instances"] = resource_data.get("maxInstances")
        config["service_account"] = resource_data.get("serviceAccountEmail")
        config["ingress_settings"] = resource_data.get("ingressSettings")
        config["vpc_connector"] = resource_data.get("vpcConnector", "").split("/")[-1] or None
        build_worker = resource_data.get("buildWorkerPool", "")
        config["build_worker_pool"] = build_worker.split("/")[-1] if build_worker else None
        source = resource_data.get("sourceArchiveUrl") or resource_data.get("sourceRepository", {}).get("url")
        config["source_archive"] = source
        if resource_data.get("httpsTrigger"):
            config["trigger_type"] = "HTTP"
        elif resource_data.get("eventTrigger"):
            config["trigger_type"] = resource_data["eventTrigger"].get("eventType", "Event").split("/")[-1]

    elif asset_type == "run.googleapis.com/Service":
        spec = resource_data.get("spec", {})
        template = spec.get("template", {})
        containers = template.get("spec", {}).get("containers", [{}])
        container = containers[0] if containers else {}
        resources_spec = container.get("resources", {})
        limits = resources_spec.get("limits", {})
        config["cpu"] = limits.get("cpu")
        config["memory"] = limits.get("memory")
        annotations = template.get("metadata", {}).get("annotations", {})
        config["max_instances"] = annotations.get("autoscaling.knative.dev/maxScale")
        config["min_instances"] = annotations.get("autoscaling.knative.dev/minScale", "0")
        config["container_image"] = container.get("image")
        config["port"] = container.get("ports", [{}])[0].get("containerPort") if container.get("ports") else None
        svc_spec = spec.get("template", {}).get("spec", {})
        config["concurrency"] = svc_spec.get("containerConcurrency")
        config["timeout"] = svc_spec.get("timeoutSeconds")
        config["service_account"] = svc_spec.get("serviceAccountName")
        env_vars = container.get("env", [])
        config["env_var_count"] = len(env_vars) if env_vars else 0
        svc_annotations = resource_data.get("metadata", {}).get("annotations", {})
        config["ingress"] = svc_annotations.get("run.googleapis.com/ingress")
        vpc = svc_annotations.get("run.googleapis.com/vpc-access-connector", "")
        config["vpc_connector"] = vpc.split("/")[-1] if vpc else None
        status = resource_data.get("status", {})
        config["url"] = status.get("url")

    elif asset_type == "pubsub.googleapis.com/Topic":
        config["message_retention_duration"] = resource_data.get("messageRetentionDuration")
        kms = resource_data.get("kmsKeyName", "")
        config["kms_key"] = kms.split("/")[-2] if kms else None
        config["schema"] = resource_data.get("schemaSettings", {}).get("schema", "").split("/")[-1] or None
        regions = resource_data.get("messageStoragePolicy", {}).get("allowedPersistenceRegions", [])
        config["message_storage_policy"] = ",".join(regions) if regions else None
        config["labels_count"] = len(resource_data.get("labels", {}))

    elif asset_type == "redis.googleapis.com/Instance":
        config["tier"] = resource_data.get("tier")
        config["memory_size_gb"] = resource_data.get("memorySizeGb")
        config["redis_version"] = resource_data.get("redisVersion")
        config["host"] = resource_data.get("host")
        config["port"] = resource_data.get("port")
        net = resource_data.get("authorizedNetwork", "")
        config["network"] = net.split("/")[-1] if net else None
        config["auth_enabled"] = resource_data.get("authEnabled")
        config["transit_encryption_mode"] = resource_data.get("transitEncryptionMode")
        config["connect_mode"] = resource_data.get("connectMode")
        config["read_replicas_mode"] = resource_data.get("readReplicasMode")
        config["replica_count"] = resource_data.get("replicaCount")
        maint = resource_data.get("maintenancePolicy", {}).get("weeklyMaintenanceWindow", [{}])[0]
        if maint:
            config["maintenance_day"] = maint.get("day")
            start = maint.get("startTime", {})
            config["maintenance_hour"] = start.get("hours")

    elif asset_type == "spanner.googleapis.com/Instance":
        config["node_count"] = resource_data.get("nodeCount")
        config["processing_units"] = resource_data.get("processingUnits")
        config_ref = resource_data.get("config", "")
        config["config"] = config_ref.split("/")[-1] if config_ref else None
        config["display_name"] = resource_data.get("displayName")
        config["default_backup_schedule_type"] = resource_data.get("defaultBackupScheduleType")

    elif asset_type == "dataflow.googleapis.com/Job":
        config["job_type"] = resource_data.get("type")
        env = resource_data.get("environment", {})
        config["sdk_version"] = env.get("sdkPipelineOptions", {}).get("options", {}).get("sdkVersion")
        pools = env.get("workerPools", [])
        if pools:
            config["worker_count"] = pools[0].get("numWorkers")
            config["max_workers"] = pools[0].get("maxNumWorkers")
            wmt = pools[0].get("machineType", "")
            config["worker_machine_type"] = wmt or None
        net = env.get("network", "")
        config["network"] = net.split("/")[-1] if net else None
        config["temp_location"] = env.get("tempStoragePrefix")
        config["service_account"] = env.get("serviceAccountEmail")

    elif asset_type == "dataproc.googleapis.com/Cluster":
        config_data = resource_data.get("config", {})
        master = config_data.get("masterConfig", {})
        master_mt = master.get("machineTypeUri", "")
        config["master_machine_type"] = master_mt.split("/")[-1] if master_mt else None
        config["master_disk_gb"] = master.get("diskConfig", {}).get("bootDiskSizeGb")
        worker = config_data.get("workerConfig", {})
        config["num_workers"] = worker.get("numInstances")
        worker_mt = worker.get("machineTypeUri", "")
        config["worker_machine_type"] = worker_mt.split("/")[-1] if worker_mt else None
        config["worker_disk_gb"] = worker.get("diskConfig", {}).get("bootDiskSizeGb")
        preempt = config_data.get("secondaryWorkerConfig", {})
        config["preemptible_workers"] = preempt.get("numInstances", 0)
        software = config_data.get("softwareConfig", {})
        config["software_version"] = software.get("imageVersion")
        gce = config_data.get("gceClusterConfig", {})
        net = gce.get("networkUri", "")
        config["network"] = net.split("/")[-1] if net else None
        config["internal_ip_only"] = gce.get("internalIpOnly")
        endpoint = config_data.get("endpointConfig", {})
        config["component_gateway"] = endpoint.get("enableHttpPortAccess")
        lifecycle = config_data.get("lifecycleConfig", {})
        config["idle_delete_ttl"] = lifecycle.get("idleDeleteTtl")

    elif asset_type == "compute.googleapis.com/Network":
        config["auto_create_subnetworks"] = resource_data.get("autoCreateSubnetworks")
        routing = resource_data.get("routingConfig", {})
        config["routing_mode"] = routing.get("routingMode")
        config["mtu"] = resource_data.get("mtu")
        config["internal_ipv6"] = resource_data.get("enableUlaInternalIpv6", False)
        subnets = resource_data.get("subnetworks", [])
        config["subnet_count"] = len(subnets)
        peers = resource_data.get("peerings", [])
        config["peering_count"] = len(peers)

    elif asset_type == "compute.googleapis.com/ForwardingRule":
        config["load_balancing_scheme"] = resource_data.get("loadBalancingScheme")
        config["protocol"] = resource_data.get("IPProtocol")
        config["ip_address"] = resource_data.get("IPAddress")
        config["port_range"] = resource_data.get("portRange")
        backend = resource_data.get("backendService", "")
        config["backend_service"] = backend.split("/")[-1] if backend else None
        config["network_tier"] = resource_data.get("networkTier")
        ssl_certs = resource_data.get("sslCertificates", [])
        config["ssl_certificates"] = ",".join(c.split("/")[-1] for c in ssl_certs) if ssl_certs else None

    elif asset_type == "compute.googleapis.com/Firewall":
        config["direction"] = resource_data.get("direction")
        config["priority"] = resource_data.get("priority")
        allowed = resource_data.get("allowed", [{}])
        config["protocol"] = allowed[0].get("IPProtocol") if allowed else None
        ports_list = allowed[0].get("ports", []) if allowed else []
        config["ports"] = ",".join(ports_list) if ports_list else None
        src_ranges = resource_data.get("sourceRanges", [])
        config["source_ranges"] = ",".join(src_ranges) if src_ranges else None
        dst_ranges = resource_data.get("destinationRanges", [])
        config["destination_ranges"] = ",".join(dst_ranges) if dst_ranges else None
        target_tags = resource_data.get("targetTags", [])
        config["target_tags"] = ",".join(target_tags) if target_tags else None
        config["disabled"] = resource_data.get("disabled", False)
        log_cfg = resource_data.get("logConfig", {})
        config["log_config"] = log_cfg.get("metadata") if log_cfg.get("enable") else None

    elif asset_type == "compute.googleapis.com/Address":
        config["address_type"] = resource_data.get("addressType")
        config["ip_version"] = resource_data.get("ipVersion", "IPV4")
        config["address"] = resource_data.get("address")
        config["network_tier"] = resource_data.get("networkTier")
        users = resource_data.get("users", [])
        config["in_use_by"] = ",".join(u.split("/")[-1] for u in users) if users else None

    elif asset_type == "artifactregistry.googleapis.com/Repository":
        config["format"] = resource_data.get("format")
        config["size_bytes"] = resource_data.get("sizeBytes")
        kms = resource_data.get("kmsKeyName", "")
        config["kms_key"] = kms.split("/")[-2] if kms else None
        config["immutable_tags"] = resource_data.get("dockerConfig", {}).get("immutableTags", False)
        config["vulnerability_scanning"] = resource_data.get("vulnerabilityScanningConfig", {}).get("enablementConfig")

    elif asset_type == "composer.googleapis.com/Environment":
        env_config = resource_data.get("config", {})
        config["airflow_version"] = env_config.get("softwareConfig", {}).get("imageVersion")
        config["environment_size"] = env_config.get("environmentSize")
        config["python_version"] = env_config.get("softwareConfig", {}).get("pythonVersion")
        gke = env_config.get("gkeCluster", "")
        config["gke_cluster"] = gke.split("/")[-1] if gke else None
        config["dag_gcs_prefix"] = env_config.get("dagGcsPrefix")
        node = env_config.get("nodeConfig", {})
        config["node_count"] = env_config.get("nodeCount")
        config["scheduler_count"] = env_config.get("workloadsConfig", {}).get("scheduler", {}).get("count")
        config["web_server_network_access_control"] = env_config.get("webServerNetworkAccessControl", {}).get("allowedIpRanges", [{}])[0].get("value") if env_config.get("webServerNetworkAccessControl") else None

    elif asset_type == "cloudscheduler.googleapis.com/Job":
        config["schedule"] = resource_data.get("schedule")
        config["timezone"] = resource_data.get("timeZone")
        if resource_data.get("httpTarget"):
            config["target_type"] = "HTTP"
            config["http_method"] = resource_data["httpTarget"].get("httpMethod")
            config["uri"] = resource_data["httpTarget"].get("uri")
        elif resource_data.get("pubsubTarget"):
            config["target_type"] = "PUBSUB"
        retry = resource_data.get("retryConfig", {})
        config["retry_count"] = retry.get("retryCount")
        config["attempt_deadline"] = resource_data.get("attemptDeadline")

    elif asset_type == "cloudtasks.googleapis.com/Queue":
        rate = resource_data.get("rateLimits", {})
        config["max_dispatches_per_second"] = rate.get("maxDispatchesPerSecond")
        config["max_concurrent_dispatches"] = rate.get("maxConcurrentDispatches")
        retry = resource_data.get("retryConfig", {})
        config["max_attempts"] = retry.get("maxAttempts")
        config["max_retry_duration"] = retry.get("maxRetryDuration")
        config["min_backoff"] = retry.get("minBackoff")
        config["max_backoff"] = retry.get("maxBackoff")
        config["max_doublings"] = retry.get("maxDoublings")

    elif asset_type == "file.googleapis.com/Instance":
        config["tier"] = resource_data.get("tier")
        shares = resource_data.get("fileShares", [])
        if shares:
            config["capacity_gb"] = shares[0].get("capacityGb")
            config["share_name"] = shares[0].get("name")
        config["file_shares"] = len(shares)
        nets = resource_data.get("networks", [])
        if nets:
            net = nets[0].get("network", "")
            config["network"] = net.split("/")[-1] if net else None
            config["ip_addresses"] = ",".join(nets[0].get("ipAddresses", []))
            config["modes"] = ",".join(nets[0].get("modes", []))
        kms = resource_data.get("kmsKeyName", "")
        config["kms_key"] = kms.split("/")[-2] if kms else None

    elif asset_type == "bigtable.googleapis.com/Instance":
        clusters = resource_data.get("clusters", {})
        config["cluster_count"] = len(clusters) if isinstance(clusters, dict) else None
        if isinstance(clusters, dict) and clusters:
            first_cluster_id = next(iter(clusters))
            first = clusters[first_cluster_id]
            config["cluster_id"] = first_cluster_id
            config["node_count"] = first.get("serveNodes")
            config["storage_type"] = first.get("defaultStorageType")
        config["deletion_protection"] = resource_data.get("deletionProtection")

    elif asset_type == "iam.googleapis.com/ServiceAccount":
        config["email"] = resource_data.get("email")
        config["description"] = resource_data.get("description") or None
        config["oauth2_client_id"] = resource_data.get("oauth2ClientId")
        config["disabled"] = resource_data.get("disabled", False)

    elif asset_type == "dns.googleapis.com/ManagedZone":
        config["dns_name"] = resource_data.get("dnsName")
        config["visibility"] = resource_data.get("visibility")
        config["record_set_count"] = resource_data.get("recordSetCount")
        name_servers = resource_data.get("nameServers", [])
        config["name_servers"] = name_servers[0] if name_servers else None
        dnssec = resource_data.get("dnssecConfig", {})
        config["dnssec"] = "ON" if dnssec.get("state") == "on" else "OFF"
        config["log_dns_queries"] = resource_data.get("enableLogging", False)

    elif asset_type == "secretmanager.googleapis.com/Secret":
        replication = resource_data.get("replication", {})
        if replication.get("automatic") is not None:
            config["replication"] = "AUTOMATIC"
        elif replication.get("userManaged"):
            config["replication"] = "USER_MANAGED"
        config["expire_time"] = resource_data.get("expireTime")
        topics = resource_data.get("topics", [])
        config["topics"] = ",".join(t.get("name", "").split("/")[-1] for t in topics) if topics else None
        rotation = resource_data.get("rotation", {})
        config["rotation_period"] = rotation.get("rotationPeriod")
        config["etag"] = resource_data.get("etag")

    elif asset_type in ("cloudkms.googleapis.com/CryptoKey", "cloudkms.googleapis.com/KeyRing"):
        config["purpose"] = resource_data.get("purpose")
        version_template = resource_data.get("versionTemplate", {})
        config["algorithm"] = version_template.get("algorithm")
        config["protection_level"] = version_template.get("protectionLevel")
        ring = resource_data.get("name", "").split("/")
        if "keyRings" in ring:
            config["key_ring"] = ring[ring.index("keyRings") + 1]
        config["rotation_period"] = resource_data.get("rotationPeriod")
        config["next_rotation_time"] = _parse_date(resource_data.get("nextRotationTime", ""))
        config["destroy_scheduled_duration"] = resource_data.get("destroyScheduledDuration")

    elif asset_type == "monitoring.googleapis.com/AlertPolicy":
        conditions = resource_data.get("conditions", [])
        config["condition_count"] = len(conditions)
        channels = resource_data.get("notificationChannels", [])
        config["notification_channels"] = len(channels)
        config["combiner"] = resource_data.get("combiner")
        config["severity"] = resource_data.get("severity")
        doc = resource_data.get("documentation", {})
        config["documentation_content"] = doc.get("content", "").split("\n")[0][:_MAX_PREVIEW_LENGTH] if doc.get("content") else None

    elif asset_type == "logging.googleapis.com/LogSink":
        config["destination"] = resource_data.get("destination")
        config["filter"] = resource_data.get("filter", "").replace("\n", " ")[:_MAX_PREVIEW_LENGTH] or None
        dest = resource_data.get("destination", "")
        config["sink_type"] = dest.split(".")[0] if dest else None
        config["include_children"] = resource_data.get("includeChildren", False)
        config["writer_identity"] = resource_data.get("writerIdentity")

    elif asset_type in ("apigateway.googleapis.com/Gateway", "apigateway.googleapis.com/Api"):
        config["default_hostname"] = resource_data.get("defaultHostname")
        config["managed_service"] = resource_data.get("managedService")
        config["config_id"] = resource_data.get("apiConfig", "").split("/")[-1] or None
        config["labels_count"] = len(resource_data.get("labels", {}))

    elif asset_type == "appengine.googleapis.com/Application":
        config["runtime"] = None  # top-level app; runtime is per-service
        config["env"] = resource_data.get("standardEnvironment", {}).get("env", "standard")
        config["serving_status"] = resource_data.get("servingStatus")
        config["instance_class"] = resource_data.get("instanceClass")
        scaling = resource_data.get("automaticScaling", {})
        config["automatic_scaling_min_instances"] = scaling.get("minInstances")
        config["automatic_scaling_max_instances"] = scaling.get("maxInstances")
        inbound = resource_data.get("inboundServices", [])
        config["inbound_services"] = ",".join(inbound) if inbound else None

    elif asset_type in ("aiplatform.googleapis.com/Model", "aiplatform.googleapis.com/Endpoint", "aiplatform.googleapis.com/Dataset"):
        config["display_name"] = resource_data.get("displayName")
        config["artifact_uri"] = resource_data.get("artifactUri")
        schema = resource_data.get("metadataSchemaUri", "")
        config["schema_title"] = schema.split("/")[-1] if schema else None
        containers = resource_data.get("containerSpec", {})
        config["framework"] = containers.get("imageUri", "").split("/")[-1].split(":")[0] if containers.get("imageUri") else None
        config["version_count"] = resource_data.get("versionCount")
        deployments = resource_data.get("deployedModels", [])
        config["deployment_count"] = len(deployments) if deployments else None
        pipeline = resource_data.get("trainingPipeline", "")
        config["training_pipeline"] = pipeline.split("/")[-1] if pipeline else None

    elif asset_type == "cloudbuild.googleapis.com/Build":
        config["machine_type"] = resource_data.get("options", {}).get("machineType")
        config["timeout"] = resource_data.get("timeout")
        config["log_bucket"] = resource_data.get("logsBucket")
        config["service_account"] = resource_data.get("serviceAccount", "").split("/")[-1] or None
        config["worker_pool"] = resource_data.get("options", {}).get("pool", {}).get("name", "").split("/")[-1] or None
        subs = resource_data.get("substitutions", {})
        config["substitution_count"] = len(subs) if subs else 0

    # Remove None values to keep the dict clean
    return {k: v for k, v in config.items() if v is not None}


def get_resources(credentials: dict) -> list[dict]:
    try:
        from googleapiclient import discovery  # type: ignore

        project_id = credentials.get("project_id")
        if not project_id:
            raise RuntimeError(
                "No GCP project selected. Please log out and log in again, "
                "then select a project from the dropdown."
            )

        creds = _build_creds(credentials)
        service = discovery.build("cloudasset", "v1", credentials=creds)

        resources: list[dict] = []
        page_token = None

        while True:
            kwargs: dict = {
                "parent": f"projects/{project_id}",
                "contentType": "RESOURCE",
                "pageSize": 500,
            }
            if page_token:
                kwargs["pageToken"] = page_token

            result = service.assets().list(**kwargs).execute()

            for asset in result.get("assets", []):
                asset_type = asset.get("assetType", "")
                resource_data = asset.get("resource", {}).get("data", {})

                # Full asset name looks like:
                #   //compute.googleapis.com/projects/p/zones/z/instances/name
                full_name = asset.get("name", "")
                display_name = resource_data.get("name", full_name).split("/")[-1]

                friendly_type = _ASSET_TYPE_MAP.get(
                    asset_type,
                    asset_type.split("/")[-1] if "/" in asset_type else asset_type,
                )

                # Location: prefer explicit field, then parse from the asset path
                location = (
                    resource_data.get("location")
                    or resource_data.get("zone", "").split("/")[-1]
                    or resource_data.get("region", "").split("/")[-1]
                    or _location_from_asset_name(full_name)
                    or "global"
                )

                status = (
                    resource_data.get("status")
                    or resource_data.get("state")
                    or "ACTIVE"
                )

                labels = resource_data.get("labels", {})
                tags = ",".join(f"{k}:{v}" for k, v in labels.items())

                config = _extract_config(asset_type, resource_data)

                resources.append({
                    "id": full_name,
                    "name": display_name,
                    "type": friendly_type,
                    "region": str(location),
                    "status": str(status),
                    "tags": tags,
                    **config,
                })

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        if resources:
            return resources
        # Empty but successful — still fall through to mock
        raise RuntimeError("Cloud Asset Inventory returned 0 assets for this project.")

    except Exception as exc:
        _last_resources_error.clear()
        error_msg = str(exc).strip()
        _last_resources_error["error"] = error_msg if error_msg else f"{type(exc).__name__}: could not retrieve GCP resources"
        return mock_service.get_resources("gcp")


# Stores the most recent error from get_resources so the router can surface it.
_last_resources_error: dict[str, str] = {}


def _location_from_asset_name(name: str) -> str:
    """Best-effort location extraction from the asset resource path."""
    parts = name.split("/")
    for key in ("zones", "regions", "locations"):
        if key in parts:
            idx = parts.index(key)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return ""


# ---------------------------------------------------------------------------
# Resource types – derived from the live asset inventory
# ---------------------------------------------------------------------------

def get_resource_types(credentials: dict) -> list[str]:
    """Return all known GCP resource types for the billing filter dropdown.

    Always includes every type from the comprehensive known list so users can
    filter billing data by any service, even ones with no active resources in
    the project.  Any additional types found in the live project are appended.
    """
    known = mock_service.get_resource_types("gcp")
    try:
        resources = get_resources(credentials)
        known_set = set(known)
        extra: list[str] = []
        for r in resources:
            t = r["type"]
            if t not in known_set:
                known_set.add(t)
                extra.append(t)
        return known + extra
    except Exception:
        return known


# ---------------------------------------------------------------------------
# Billing – real billing-account check + mock cost figures
# ---------------------------------------------------------------------------

def _get_billing_account_name(credentials: dict) -> str | None:
    """Return the display name of the billing account linked to the project, or None."""
    try:
        from google.cloud import billing_v1  # type: ignore

        creds = _build_creds(credentials)
        project_id = credentials.get("project_id")
        client = billing_v1.CloudBillingClient(credentials=creds)
        info = client.get_project_billing_info(name=f"projects/{project_id}")
        return info.billing_account_name or None
    except Exception:
        return None


def _billing_note() -> str:
    return (
        "Cost figures are estimated. To see actual GCP costs, enable "
        "Cloud Billing export to BigQuery in the GCP Console."
    )


def _find_bigquery_project(credentials: dict, dataset: str, table: str) -> str | None:
    """Search across accessible GCP projects to find which one contains the given BigQuery dataset and table.

    Uses the ``gcp_projects`` list stored in credentials (populated during OAuth login).
    Falls back to checking only the currently selected ``project_id`` when no project list
    is available (e.g. service-account flow).

    Returns the project ID where the dataset/table was found, or ``None`` if not found.
    """
    try:
        from google.cloud import bigquery  # type: ignore

        creds = _build_creds(credentials)

        # Build the ordered list of projects to search
        projects_to_check: list[str] = []
        current = credentials.get("project_id", "")

        # Start with the currently selected project for faster resolution in the common case
        if current:
            projects_to_check.append(current)

        for proj in credentials.get("gcp_projects", []):
            pid = proj.get("project_id") if isinstance(proj, dict) else str(proj)
            if pid and pid not in projects_to_check:
                projects_to_check.append(pid)

        for project_id in projects_to_check:
            try:
                client = bigquery.Client(credentials=creds, project=project_id)
                client.get_table(f"{project_id}.{dataset}.{table}")
                return project_id
            except Exception:
                continue
    except Exception:
        pass
    return None


def get_bigquery_billing_projects(credentials: dict) -> list[str]:
    """Return the distinct GCP project IDs that appear in the billing export table.

    Queries ``SELECT DISTINCT project.id`` from the configured BigQuery billing
    export table and returns the sorted list of project IDs.  Returns an empty
    list when no dataset/table is configured or the query fails.
    """
    dataset = credentials.get("bigquery_dataset", "").strip()
    table = credentials.get("bigquery_table", "").strip()
    if not dataset or not table:
        return []

    billing_project = _find_bigquery_project(credentials, dataset, table)
    if not billing_project:
        return []

    try:
        from google.cloud import bigquery  # type: ignore

        creds = _build_creds(credentials)
        client = bigquery.Client(credentials=creds, project=billing_project)
        table_ref = f"`{billing_project}.{dataset}.{table}`"
        query = f"SELECT project.id AS project_id FROM {table_ref} WHERE project.id IS NOT NULL GROUP BY project.id ORDER BY project_id"
        rows = list(client.query(query).result())
        return [row["project_id"] for row in rows if row["project_id"]]
    except Exception:
        return []


def _query_bigquery_overall_billing(
    credentials: dict, dataset: str, table: str, start: date, end: date,
    bq_project: str | None = None,
) -> tuple[dict | None, str | None]:
    """Query BigQuery billing export for overall cost data.

    Computes the net cost per service per day by summing both the base cost
    and any credit amounts (discounts, committed-use, etc.) from the credits
    ARRAY column present in the GCP standard billing export.

    Returns (result_dict, None) on success or (None, error_message) on failure.
    """
    try:
        from google.cloud import bigquery  # type: ignore

        creds = _build_creds(credentials)
        project_id = credentials.get("project_id")
        client = bigquery.Client(credentials=creds, project=project_id)

        table_ref = f"`{project_id}.{dataset}.{table}`"
        # Net cost = gross cost + credits (credits.amount values are negative for discounts).
        # UNNEST the credits array and add each credit amount to arrive at the true net charge.
        # Use alias names in GROUP BY (same as the user-confirmed working query in BigQuery UI).
        project_filter = "AND project.id = @bq_project" if bq_project else ""
        query = f"""
            SELECT
                service.description AS service,
                DATE(usage_start_time) AS usage_date,
                SUM(cost + IFNULL(
                    (SELECT SUM(c.amount) FROM UNNEST(credits) AS c),
                    0
                )) AS daily_cost,
                MAX(currency) AS currency
            FROM {table_ref}
            WHERE DATE(usage_start_time) BETWEEN @start_date AND @end_date
              AND service.description IS NOT NULL
              {project_filter}
            GROUP BY service, usage_date
            HAVING daily_cost != 0
            ORDER BY usage_date, daily_cost DESC
        """
        query_params = [
            bigquery.ScalarQueryParameter("start_date", "DATE", start.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end.isoformat()),
        ]
        if bq_project:
            query_params.append(bigquery.ScalarQueryParameter("bq_project", "STRING", bq_project))
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        rows = list(client.query(query, job_config=job_config).result())
        if not rows:
            return {
                "total": 0.0,
                "currency": "USD",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily_costs": [],
                "breakdown": [],
                "service_daily": {},
                "source": "bigquery",
            }, None

        # Aggregate daily totals, service breakdown, AND per-service-per-day costs
        daily_map: dict[str, float] = {}
        service_map: dict[str, float] = {}
        # service_daily: {date -> {service -> cost}} — used for accurate stacked chart
        service_daily: dict[str, dict[str, float]] = {}
        currency = "USD"
        for row in rows:
            d = row["usage_date"].isoformat()
            cost = float(row["daily_cost"] or 0.0)
            svc = row["service"] or "Other"
            daily_map[d] = daily_map.get(d, 0.0) + cost
            service_map[svc] = service_map.get(svc, 0.0) + cost
            if d not in service_daily:
                service_daily[d] = {}
            service_daily[d][svc] = service_daily[d].get(svc, 0.0) + cost
            if row["currency"]:
                currency = row["currency"]

        daily_costs = [
            {"date": d, "cost": round(c, 2)}
            for d, c in sorted(daily_map.items())
        ]
        total = round(sum(daily_map.values()), 2)
        breakdown = sorted(
            [{"service": s, "cost": round(c, 2)} for s, c in service_map.items()],
            key=lambda x: x["cost"],
            reverse=True,
        )
        return {
            "total": total,
            "currency": currency,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily_costs": daily_costs,
            "breakdown": breakdown,
            "service_daily": service_daily,
            "source": "bigquery",
        }, None
    except Exception as exc:
        return None, str(exc)


def _query_bigquery_billing_by_service(
    credentials: dict, dataset: str, table: str,
    resource_type: str, start: date, end: date,
    bq_project: str | None = None,
) -> tuple[dict | None, str | None]:
    """Query BigQuery billing export for a specific service's cost data.

    Computes the net cost (gross cost + credits) per day for the given service.
    Returns (result_dict, None) on success or (None, error_message) on failure.
    """
    try:
        from google.cloud import bigquery  # type: ignore

        creds = _build_creds(credentials)
        project_id = credentials.get("project_id")
        client = bigquery.Client(credentials=creds, project=project_id)

        table_ref = f"`{project_id}.{dataset}.{table}`"
        project_filter = "AND project.id = @bq_project" if bq_project else ""
        query = f"""
            SELECT
                DATE(usage_start_time) AS usage_date,
                SUM(cost + IFNULL(
                    (SELECT SUM(c.amount) FROM UNNEST(credits) AS c),
                    0
                )) AS daily_cost,
                MAX(currency) AS currency
            FROM {table_ref}
            WHERE DATE(usage_start_time) BETWEEN @start_date AND @end_date
              AND service.description = @resource_type
              {project_filter}
            GROUP BY usage_date
            HAVING daily_cost != 0
            ORDER BY usage_date
        """
        query_params = [
            bigquery.ScalarQueryParameter("start_date", "DATE", start.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end.isoformat()),
            bigquery.ScalarQueryParameter("resource_type", "STRING", resource_type),
        ]
        if bq_project:
            query_params.append(bigquery.ScalarQueryParameter("bq_project", "STRING", bq_project))
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        rows = list(client.query(query, job_config=job_config).result())
        if not rows:
            days = (end - start).days + 1
            return {
                "resource_type": resource_type,
                "total": 0.0,
                "currency": "USD",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily_costs": [],
                "average_daily": 0.0,
                "source": "bigquery",
            }, None

        currency = "USD"
        daily_costs = []
        for row in rows:
            daily_costs.append({"date": row["usage_date"].isoformat(), "cost": round(float(row["daily_cost"]), 2)})
            if row["currency"]:
                currency = row["currency"]

        total = round(sum(r["cost"] for r in daily_costs), 2)
        days = (end - start).days + 1
        return {
            "resource_type": resource_type,
            "total": total,
            "currency": currency,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily_costs": daily_costs,
            "average_daily": round(total / max(days, 1), 2),
            "source": "bigquery",
        }, None
    except Exception as exc:
        return None, str(exc)


def _build_gcp_billing_base(credentials: dict) -> dict[str, float]:
    """Return a billing base dict keyed by billable GCP service categories
    present in the account.

    Includes every live resource type that carries a cost:
    - Known types use their entry from GCP_BILLING_BASE.
    - Unknown billable types fall back to a small default cost so they still
      appear in the breakdown.
    - Types in _FREE_RESOURCE_TYPES are excluded (they carry no direct charge).
    Falls back to the full static GCP_BILLING_BASE when the live call fails.
    """
    from services.mock_service import GCP_BILLING_BASE  # noqa: PLC0415

    _DEFAULT_COST = 10.0  # fallback monthly estimate for unrecognized types

    try:
        resources = get_resources(credentials)
        if not resources:
            return GCP_BILLING_BASE

        seen: set[str] = set()
        live_types: list[str] = []
        for r in resources:
            t = r["type"]
            if t not in seen:
                seen.add(t)
                live_types.append(t)

        if not live_types:
            return GCP_BILLING_BASE

        base: dict[str, float] = {}
        for t in live_types:
            if t in _FREE_RESOURCE_TYPES:
                continue
            base[t] = GCP_BILLING_BASE.get(t, _DEFAULT_COST)

        return base if base else GCP_BILLING_BASE
    except Exception:
        return GCP_BILLING_BASE


def get_overall_billing(credentials: dict, start: date, end: date, bq_project: str | None = None) -> dict:
    from services.mock_service import _make_seed, _daily_costs  # noqa: PLC0415

    _last_billing_error.clear()

    dataset = credentials.get("bigquery_dataset", "").strip()
    table = credentials.get("bigquery_table", "").strip()

    if dataset and table:
        billing_project = _find_bigquery_project(credentials, dataset, table)
        if billing_project:
            bq_creds = {**credentials, "project_id": billing_project}
            bq_result, bq_error = _query_bigquery_overall_billing(
                bq_creds, dataset, table, start, end, bq_project=bq_project
            )
            if bq_result is not None:
                bq_result["bigquery_project"] = billing_project
                return bq_result
            # bq_error is set when the query itself failed
            _last_billing_error["error"] = (
                f"BigQuery query failed in project '{billing_project}': {bq_error}. "
                "Showing estimated data based on your project's resource types."
            )
        else:
            _last_billing_error["error"] = (
                f"BigQuery dataset '{dataset}' / table '{table}' was not found in any "
                "accessible GCP project. Please verify the dataset and table names."
            )
    else:
        # No BigQuery export configured — all data is estimated
        _last_billing_error["error"] = (
            "Actual billing data requires Cloud Billing export to BigQuery. "
            "Enable it in the GCP Console under Billing → Billing export."
        )

    billing_base = _build_gcp_billing_base(credentials)
    total_base = sum(billing_base.values())
    seed = _make_seed("gcp", start.isoformat(), end.isoformat())
    daily = _daily_costs(total_base, start, end, seed)
    total = round(sum(d["cost"] for d in daily), 2)

    breakdown = [
        {"service": svc, "cost": round(total * cost / total_base, 2)}
        for svc, cost in billing_base.items()
    ]
    breakdown.sort(key=lambda x: x["cost"], reverse=True)

    result = {
        "total": total,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": daily,
        "breakdown": breakdown,
        "estimated": True,
        "note": _last_billing_error.get("error") or _billing_note(),
    }

    billing_account = _get_billing_account_name(credentials)
    if billing_account:
        result["billing_account"] = billing_account

    return result


def get_billing_by_resource_type(
    credentials: dict, resource_type: str, start: date, end: date,
    bq_project: str | None = None,
) -> dict:
    from services.mock_service import GCP_BILLING_BASE, _make_seed, _daily_costs  # noqa: PLC0415

    _last_billing_error.clear()

    dataset = credentials.get("bigquery_dataset", "").strip()
    table = credentials.get("bigquery_table", "").strip()

    if dataset and table:
        billing_project = _find_bigquery_project(credentials, dataset, table)
        if billing_project:
            bq_creds = {**credentials, "project_id": billing_project}
            bq_result, bq_error = _query_bigquery_billing_by_service(
                bq_creds, dataset, table, resource_type, start, end, bq_project=bq_project
            )
            if bq_result is not None:
                bq_result["bigquery_project"] = billing_project
                return bq_result
            _last_billing_error["error"] = (
                f"BigQuery query failed in project '{billing_project}': {bq_error}. "
                "Showing estimated data based on your project's resource types."
            )
        else:
            _last_billing_error["error"] = (
                f"BigQuery dataset '{dataset}' / table '{table}' was not found in any "
                "accessible GCP project. Please verify the dataset and table names."
            )
    else:
        _last_billing_error["error"] = (
            "Actual billing data requires Cloud Billing export to BigQuery. "
            "Enable it in the GCP Console under Billing → Billing export."
        )

    base = GCP_BILLING_BASE.get(resource_type, 50.0)
    seed = _make_seed("gcp", resource_type, start.isoformat(), end.isoformat())
    daily = _daily_costs(base, start, end, seed)
    days = (end - start).days + 1
    total = round(sum(d["cost"] for d in daily), 2)

    result = {
        "resource_type": resource_type,
        "total": total,
        "currency": "USD",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily_costs": daily,
        "average_daily": round(total / max(days, 1), 2),
        "estimated": True,
        "note": _last_billing_error.get("error") or _billing_note(),
    }

    billing_account = _get_billing_account_name(credentials)
    if billing_account:
        result["billing_account"] = billing_account

    return result


# Stores the most recent billing error so the router can surface it.
_last_billing_error: dict[str, str] = {}


# ---------------------------------------------------------------------------
# IAM – fetch authenticated user's roles and the project IAM policy
# ---------------------------------------------------------------------------

def get_iam_roles(credentials: dict) -> dict:
    """Return IAM bindings for the project and – for OAuth sessions – the
    roles held by the logged-in user.

    Returns a dict with:
      - ``email``       : the authenticated user's email (OAuth only, else None)
      - ``project_id``  : the GCP project ID
      - ``user_roles``  : list of role IDs assigned to this user
      - ``all_bindings``: full IAM policy bindings for the project
      - ``error``       : error message if the call failed (instead of the above)
    """
    try:
        from googleapiclient import discovery  # type: ignore

        creds = _build_creds(credentials)
        project_id = credentials.get("project_id", "")

        # Resolve the authenticated user's email for OAuth sessions
        user_email: str | None = None
        if credentials.get("auth_type") == "oauth":
            try:
                import requests as _req  # type: ignore

                resp = _req.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    headers={"Authorization": f"Bearer {credentials.get('token', '')}"},
                    timeout=5,
                )
                if resp.status_code == 200:
                    user_email = resp.json().get("email")
            except Exception:
                pass

        # Fetch the project's IAM policy
        crm = discovery.build(
            "cloudresourcemanager", "v1", credentials=creds, cache_discovery=False
        )
        policy = crm.projects().getIamPolicy(resource=project_id, body={}).execute()
        all_bindings = policy.get("bindings", [])

        # Filter bindings to find the roles held by this user
        user_roles: list[str] = []
        if user_email:
            prefixes = {f"user:{user_email}", f"serviceAccount:{user_email}"}
            for binding in all_bindings:
                members = set(binding.get("members", []))
                if members & prefixes:
                    user_roles.append(binding.get("role", ""))

        return {
            "email": user_email,
            "project_id": project_id,
            "user_roles": user_roles,
            "all_bindings": all_bindings,
        }
    except Exception as exc:
        return {"error": str(exc)[:500]}


# ---------------------------------------------------------------------------
# Suggestions – analyse resources, billing, and IAM to surface actionable items
# ---------------------------------------------------------------------------

# Machine types ordered roughly by size (vCPU count) for over-provisioning checks.
_LARGE_MACHINE_TYPES: frozenset[str] = frozenset({
    "n1-standard-16", "n1-standard-32", "n1-standard-64", "n1-standard-96",
    "n1-highmem-16", "n1-highmem-32", "n1-highmem-64", "n1-highmem-96",
    "n2-standard-16", "n2-standard-32", "n2-standard-48", "n2-standard-64", "n2-standard-96",
    "n2-highmem-16", "n2-highmem-32", "n2-highmem-48", "n2-highmem-64",
    "n2d-standard-16", "n2d-standard-32", "n2d-standard-48", "n2d-standard-64",
    "e2-standard-16", "e2-standard-32",
    "c2-standard-16", "c2-standard-30", "c2-standard-60",
    "m1-megamem-96", "m1-ultramem-40", "m1-ultramem-80", "m1-ultramem-160",
    "m2-megamem-416", "m2-ultramem-208", "m2-ultramem-416",
})

# IAM roles that grant very broad access – flag when assigned at project level.
_PRIMITIVE_ROLES: frozenset[str] = frozenset({
    "roles/owner", "roles/editor", "roles/viewer",
})
_HIGH_RISK_ROLES: frozenset[str] = frozenset({
    "roles/owner", "roles/editor",
})

# Persistent disk types considered high-performance (and therefore higher cost).
_HIGH_PERF_DISK_TYPES: frozenset[str] = frozenset({
    "pd-ssd", "hyperdisk-balanced",
})


def _suggestion(
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
) -> dict:
    return {
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


def _suggestions_from_resources(resources: list[dict]) -> list[dict]:
    """Analyse resource configurations and return a list of suggestions."""
    suggestions: list[dict] = []

    # Track orphaned disks (not attached to any instance)
    attached_disks: set[str] = set()
    for r in resources:
        if r.get("type") == "Compute Engine":
            for disk_name in (r.get("attached_disks") or "").split(","):
                name = disk_name.strip()
                if name:
                    attached_disks.add(name)

    for r in resources:
        name = r.get("name", "unknown")
        rtype = r.get("type", "")

        # ── Compute Engine Instances ─────────────────────────────────────────
        if rtype == "Compute Engine":
            machine_type = r.get("machine_type") or ""

            # Over-provisioned: large machine type
            if machine_type.lower() in _LARGE_MACHINE_TYPES:
                suggestions.append(_suggestion(
                    sid=f"res-ce-large-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Large machine type may be over-provisioned",
                    description=(
                        f"Instance '{name}' uses machine type '{machine_type}', which has a high "
                        "vCPU/memory footprint. If CPU and memory utilisation are consistently low, "
                        "consider right-sizing to a smaller type."
                    ),
                    current_value=machine_type,
                    recommendation=(
                        "Review Cloud Monitoring CPU/memory metrics. Downsize to a smaller machine "
                        "type (e.g. n2-standard-4) or enable Recommender API for automated suggestions."
                    ),
                ))

            # Underused: preemptible not enabled (missed cost-saving opportunity)
            if r.get("preemptible") is False:
                suggestions.append(_suggestion(
                    sid=f"res-ce-preemptible-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Preemptible/Spot VM not used",
                    description=(
                        f"Instance '{name}' is not configured as a preemptible or Spot VM. "
                        "For fault-tolerant batch workloads, Spot VMs can save up to 90% of compute cost."
                    ),
                    current_value="preemptible: false",
                    recommendation=(
                        "Enable Spot VMs for non-critical or batch workloads. "
                        "Not recommended for stateful or long-running services."
                    ),
                ))

            # Security: external/public IP exposed
            if r.get("external_ip"):
                suggestions.append(_suggestion(
                    sid=f"res-ce-extip-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Instance has a public external IP",
                    description=(
                        f"Instance '{name}' has external IP '{r.get('external_ip')}' attached. "
                        "Exposing instances directly to the internet increases the attack surface."
                    ),
                    current_value=f"external_ip: {r.get('external_ip')}",
                    recommendation=(
                        "Use Cloud NAT or an internal load balancer. Remove the external IP unless "
                        "the instance must be directly reachable from the internet."
                    ),
                ))

            # Over-provisioned: very large boot disk
            try:
                disk_gb = int(r.get("boot_disk_size_gb") or 0)
            except (TypeError, ValueError):
                disk_gb = 0
            if disk_gb > 500:
                suggestions.append(_suggestion(
                    sid=f"res-ce-disk-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Oversized boot disk",
                    description=(
                        f"Instance '{name}' has a boot disk of {disk_gb} GB. "
                        "Oversized disks incur unnecessary persistent-disk costs."
                    ),
                    current_value=f"boot_disk_size_gb: {disk_gb}",
                    recommendation=(
                        "Resize the boot disk to the minimum required for the OS and application, "
                        "or migrate data to a cheaper Cloud Storage bucket."
                    ),
                ))

            # Security: Shielded VM secure boot not enabled
            if r.get("shielded_secure_boot") is False:
                suggestions.append(_suggestion(
                    sid=f"res-ce-shielded-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Shielded VM Secure Boot is disabled",
                    description=(
                        f"Instance '{name}' does not have Shielded VM Secure Boot enabled. "
                        "Secure Boot helps protect the VM against boot-level malware."
                    ),
                    current_value="shielded_secure_boot: false",
                    recommendation=(
                        "Enable Secure Boot in the instance's Shielded VM configuration "
                        "to protect against rootkits and bootloader tampering."
                    ),
                ))

        # ── Persistent Disks ─────────────────────────────────────────────────
        elif rtype == "Persistent Disk":
            # Underused: orphaned disk not attached to any instance
            in_use_by = (r.get("in_use_by") or "").strip()
            if not in_use_by and name not in attached_disks:
                suggestions.append(_suggestion(
                    sid=f"res-pd-orphan-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Orphaned persistent disk (not attached to any instance)",
                    description=(
                        f"Disk '{name}' is not attached to any Compute Engine instance. "
                        "Unattached disks still incur storage costs."
                    ),
                    current_value="in_use_by: (none)",
                    recommendation=(
                        "Verify whether the disk is still needed. If not, create a snapshot "
                        "for backup and then delete the disk to stop incurring charges."
                    ),
                ))

            # Over-provisioned: SSD disk when standard may suffice
            if (r.get("disk_type") or "").lower() in _HIGH_PERF_DISK_TYPES:
                suggestions.append(_suggestion(
                    sid=f"res-pd-ssd-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="SSD persistent disk – verify IOPS requirements",
                    description=(
                        f"Disk '{name}' uses type '{r.get('disk_type')}'. SSDs cost significantly "
                        "more than standard HDDs. If the workload does not require high IOPS, "
                        "a standard persistent disk may be sufficient."
                    ),
                    current_value=f"disk_type: {r.get('disk_type')}",
                    recommendation=(
                        "Review Cloud Monitoring disk IOPS metrics. "
                        "If utilisation is low, migrate to pd-standard or pd-balanced."
                    ),
                ))

        # ── Cloud Storage Buckets ─────────────────────────────────────────────
        elif rtype == "Cloud Storage":
            storage_class = r.get("storage_class") or ""
            lifecycle_rules = r.get("lifecycle_rules") or 0
            versioning = r.get("versioning") or ""
            public_access = r.get("public_access") or ""

            # Underused storage-class optimisation
            if storage_class.upper() == "STANDARD" and lifecycle_rules == 0:
                suggestions.append(_suggestion(
                    sid=f"res-gcs-lifecycle-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="No lifecycle policy on STANDARD storage bucket",
                    description=(
                        f"Bucket '{name}' uses STANDARD storage class with no lifecycle rules. "
                        "Infrequently accessed objects could be moved to NEARLINE or COLDLINE "
                        "to reduce storage costs."
                    ),
                    current_value=f"storage_class: {storage_class}, lifecycle_rules: 0",
                    recommendation=(
                        "Add a lifecycle rule to transition objects to NEARLINE (30 days) "
                        "or COLDLINE (90 days) after a period of inactivity."
                    ),
                ))

            # Over-provisioned: versioning enabled without lifecycle (versions accumulate)
            if versioning == "Enabled" and lifecycle_rules == 0:
                suggestions.append(_suggestion(
                    sid=f"res-gcs-versioning-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Object versioning enabled with no lifecycle rule to expire old versions",
                    description=(
                        f"Bucket '{name}' has versioning enabled but no lifecycle rules. "
                        "Non-current object versions accumulate indefinitely, consuming storage "
                        "and increasing costs."
                    ),
                    current_value="versioning: Enabled, lifecycle_rules: 0",
                    recommendation=(
                        "Add a lifecycle rule to delete non-current object versions after a "
                        "reasonable retention period (e.g. 30 days)."
                    ),
                ))

            # Security: public access allowed
            if public_access == "Allowed":
                suggestions.append(_suggestion(
                    sid=f"res-gcs-public-{name}",
                    category="resources",
                    severity="critical",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Bucket public access is not blocked",
                    description=(
                        f"Bucket '{name}' does not enforce public access prevention. "
                        "Objects may be inadvertently exposed to the internet."
                    ),
                    current_value="public_access: Allowed",
                    recommendation=(
                        "Set publicAccessPrevention to 'enforced' on the bucket unless "
                        "public access is intentionally required for a website or CDN."
                    ),
                ))

        # ── Cloud SQL ────────────────────────────────────────────────────────
        elif rtype == "Cloud SQL":
            # Critical: backups disabled
            if r.get("backup_enabled") is False:
                suggestions.append(_suggestion(
                    sid=f"res-sql-backup-{name}",
                    category="resources",
                    severity="critical",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Automated backups are disabled",
                    description=(
                        f"Cloud SQL instance '{name}' has automated backups disabled. "
                        "A data-loss event (accidental deletion, corruption) would be unrecoverable."
                    ),
                    current_value="backup_enabled: false",
                    recommendation=(
                        "Enable automated backups and Point-in-Time Recovery (PITR) in the "
                        "instance settings immediately."
                    ),
                ))

            # Underused: single-zone availability (no HA)
            availability = (r.get("availability_type") or "").upper()
            if availability == "ZONAL":
                suggestions.append(_suggestion(
                    sid=f"res-sql-ha-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Cloud SQL instance is not configured for high availability",
                    description=(
                        f"Cloud SQL instance '{name}' uses ZONAL availability (single zone). "
                        "A zone outage will take the database offline."
                    ),
                    current_value="availability_type: ZONAL",
                    recommendation=(
                        "Switch to REGIONAL availability to enable automatic failover to a "
                        "standby replica in a different zone."
                    ),
                ))

            # Security: deletion protection disabled
            if r.get("deletion_protection") is False:
                suggestions.append(_suggestion(
                    sid=f"res-sql-delprotect-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Deletion protection is not enabled",
                    description=(
                        f"Cloud SQL instance '{name}' does not have deletion protection enabled. "
                        "The instance can be accidentally deleted."
                    ),
                    current_value="deletion_protection: false",
                    recommendation=(
                        "Enable deletion protection in the instance settings to prevent "
                        "accidental deletion of the database."
                    ),
                ))

        # ── GKE Clusters ─────────────────────────────────────────────────────
        elif rtype == "GKE":
            # Underused: autopilot not enabled
            if r.get("autopilot") is False:
                suggestions.append(_suggestion(
                    sid=f"res-gke-autopilot-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="underused",
                    resource_name=name,
                    resource_type=rtype,
                    title="GKE Autopilot mode not enabled",
                    description=(
                        f"GKE cluster '{name}' uses standard mode. Autopilot manages node "
                        "provisioning automatically, optimising resource usage and reducing "
                        "operational overhead."
                    ),
                    current_value="autopilot: false",
                    recommendation=(
                        "Consider migrating to GKE Autopilot for fully managed node management "
                        "and per-pod billing that eliminates idle node costs."
                    ),
                ))

            # Security: cluster is not private
            if r.get("private_cluster") is False:
                suggestions.append(_suggestion(
                    sid=f"res-gke-private-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="GKE cluster does not use private nodes",
                    description=(
                        f"GKE cluster '{name}' has public nodes (private nodes not enabled). "
                        "Worker nodes with public IP addresses are directly reachable from the internet."
                    ),
                    current_value="private_cluster: false",
                    recommendation=(
                        "Enable private nodes so worker nodes only have internal IP addresses. "
                        "Use Cloud NAT for outbound internet access."
                    ),
                ))

            # Over-provisioned: high node count
            try:
                node_count = int(r.get("node_count") or 0)
            except (TypeError, ValueError):
                node_count = 0
            if node_count > 20:
                suggestions.append(_suggestion(
                    sid=f"res-gke-nodes-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="High node count – verify cluster utilisation",
                    description=(
                        f"GKE cluster '{name}' has {node_count} nodes. "
                        "A large number of nodes may indicate over-provisioning if workloads "
                        "do not fully utilise available CPU and memory."
                    ),
                    current_value=f"node_count: {node_count}",
                    recommendation=(
                        "Review cluster CPU/memory utilisation in Cloud Monitoring. "
                        "Enable cluster autoscaler to scale nodes down when demand is low."
                    ),
                ))

        # ── Cloud Functions ───────────────────────────────────────────────────
        elif rtype == "Cloud Functions":
            # Over-provisioned: very high memory allocation
            try:
                mem_mb = int(r.get("available_memory_mb") or 0)
            except (TypeError, ValueError):
                mem_mb = 0
            if mem_mb > 1024:
                suggestions.append(_suggestion(
                    sid=f"res-cf-memory-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Cloud Function allocated memory may be over-provisioned",
                    description=(
                        f"Cloud Function '{name}' is allocated {mem_mb} MB of memory. "
                        "If the function's actual peak memory is much lower, this is wasted spend."
                    ),
                    current_value=f"available_memory_mb: {mem_mb}",
                    recommendation=(
                        "Monitor the function's memory usage in Cloud Monitoring and reduce "
                        "the allocation to the observed peak plus a 20% headroom."
                    ),
                ))

            # Over-provisioned: always-on min instances
            try:
                min_inst = int(r.get("min_instances") or 0)
            except (TypeError, ValueError):
                min_inst = 0
            if min_inst > 0:
                suggestions.append(_suggestion(
                    sid=f"res-cf-mininst-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Cloud Function has minimum instances configured (always-on cost)",
                    description=(
                        f"Cloud Function '{name}' has min_instances={min_inst}. "
                        "Keeping instances warm prevents cold starts but incurs continuous cost "
                        "even when there is no traffic."
                    ),
                    current_value=f"min_instances: {min_inst}",
                    recommendation=(
                        "Set min_instances=0 unless cold-start latency is a hard requirement. "
                        "For latency-sensitive functions consider Cloud Run with min-instances instead."
                    ),
                ))

            # Security: unrestricted ingress
            if (r.get("ingress_settings") or "").upper() == "ALLOW_ALL":
                suggestions.append(_suggestion(
                    sid=f"res-cf-ingress-{name}",
                    category="resources",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=name,
                    resource_type=rtype,
                    title="Cloud Function allows all ingress traffic",
                    description=(
                        f"Cloud Function '{name}' has ingress_settings=ALLOW_ALL. "
                        "This allows calls from the public internet without restriction."
                    ),
                    current_value="ingress_settings: ALLOW_ALL",
                    recommendation=(
                        "Restrict ingress to ALLOW_INTERNAL_ONLY or ALLOW_INTERNAL_AND_GCLB "
                        "unless the function is intentionally a public HTTP endpoint."
                    ),
                ))

        # ── Cloud Run Services ───────────────────────────────────────────────
        elif rtype == "Cloud Run":
            # Underused: no minimum instances + no max concurrency cap
            try:
                max_scale = int(r.get("max_scale") or 0)
            except (TypeError, ValueError):
                max_scale = 0
            if max_scale == 0:
                suggestions.append(_suggestion(
                    sid=f"res-cr-maxscale-{name}",
                    category="resources",
                    severity="info",
                    suggestion_type="overused",
                    resource_name=name,
                    resource_type=rtype,
                    title="Cloud Run service has no maximum instance limit",
                    description=(
                        f"Cloud Run service '{name}' has no maximum scaling limit configured. "
                        "An unexpected traffic spike can create thousands of instances, "
                        "leading to unexpectedly high costs."
                    ),
                    current_value="max_scale: unlimited",
                    recommendation=(
                        "Set a maximum instance limit appropriate for the expected traffic "
                        "and budget to prevent runaway scaling costs."
                    ),
                ))

    return suggestions


def _suggestions_from_billing(billing_data: dict) -> list[dict]:
    """Analyse overall billing data and return cost-optimisation suggestions."""
    suggestions: list[dict] = []

    breakdown: list[dict] = billing_data.get("breakdown", [])
    total: float = billing_data.get("total", 0.0)
    if not breakdown or total <= 0:
        return suggestions

    # Detect top spender (service consuming > 50 % of total)
    for item in breakdown:
        svc = item.get("service", "Unknown")
        cost = item.get("cost", 0.0)
        pct = round(cost / total * 100, 1) if total > 0 else 0
        if pct > 50:
            suggestions.append(_suggestion(
                sid=f"bill-top-{svc.replace(' ', '_').lower()[:40]}",
                category="billing",
                severity="warning",
                suggestion_type="overused",
                resource_name=svc,
                resource_type="Billing",
                title=f"'{svc}' accounts for {pct}% of total spend",
                description=(
                    f"The service '{svc}' is responsible for {pct}% (${cost:.2f}) of the "
                    f"${total:.2f} total spend in the selected period. "
                    "A high concentration of spend in one service can indicate over-provisioning "
                    "or unoptimised usage."
                ),
                current_value=f"${cost:.2f} / ${total:.2f} total ({pct}%)",
                recommendation=(
                    "Review resource usage for this service in Cloud Monitoring. "
                    "Enable committed-use discounts or sustained-use discount analysis in "
                    "the GCP Cost Management console."
                ),
            ))

        # Near-zero spend (possibly unused service still incurring cost)
        if 0 < cost < 1.0:
            suggestions.append(_suggestion(
                sid=f"bill-low-{svc.replace(' ', '_').lower()[:40]}",
                category="billing",
                severity="info",
                suggestion_type="underused",
                resource_name=svc,
                resource_type="Billing",
                title=f"'{svc}' has very low spend – may be an unused service",
                description=(
                    f"Service '{svc}' shows a cost of ${cost:.2f} in the selected period. "
                    "A very small charge often indicates a lingering resource (e.g. static IP, "
                    "idle instance, unused API enablement) that can be safely removed."
                ),
                current_value=f"${cost:.2f}",
                recommendation=(
                    f"Investigate active resources under '{svc}'. "
                    "Delete or disable resources that are no longer in use to eliminate the charge."
                ),
            ))

    # Detect cost growth: compare first-half vs second-half of the period
    daily_costs: list[dict] = billing_data.get("daily_costs", [])
    if len(daily_costs) >= 4:
        mid = len(daily_costs) // 2
        first_avg = sum(d.get("cost", 0) for d in daily_costs[:mid]) / mid
        second_avg = sum(d.get("cost", 0) for d in daily_costs[mid:]) / (len(daily_costs) - mid)
        if first_avg > 0 and second_avg > first_avg * 1.5:
            growth_pct = round((second_avg - first_avg) / first_avg * 100, 1)
            suggestions.append(_suggestion(
                sid="bill-cost-growth",
                category="billing",
                severity="warning",
                suggestion_type="overused",
                resource_name="Overall",
                resource_type="Billing",
                title=f"Daily spend growing rapidly (+{growth_pct}% in second half of period)",
                description=(
                    f"Average daily spend increased by {growth_pct}% in the second half of the "
                    "selected billing period compared to the first half. "
                    "This may signal new workloads, misconfiguration, or runaway autoscaling."
                ),
                current_value=f"avg daily: ${first_avg:.2f} → ${second_avg:.2f}",
                recommendation=(
                    "Review Cloud Monitoring cost anomaly alerts and inspect recently "
                    "created or scaled resources. Enable budget alerts in GCP Billing."
                ),
            ))

    return suggestions


def _suggestions_from_iam(iam_data: dict) -> list[dict]:
    """Analyse IAM policy bindings and return security suggestions."""
    suggestions: list[dict] = []
    all_bindings: list[dict] = iam_data.get("all_bindings", [])
    if not all_bindings:
        return suggestions

    # Count owners
    owner_members: list[str] = []
    for binding in all_bindings:
        role = binding.get("role", "")
        members = binding.get("members", [])
        if role == "roles/owner":
            owner_members.extend(members)

    if len(owner_members) > 3:
        suggestions.append(_suggestion(
            sid="iam-many-owners",
            category="iam",
            severity="warning",
            suggestion_type="security",
            resource_name="Project",
            resource_type="IAM",
            title=f"Too many project owners ({len(owner_members)})",
            description=(
                f"The project has {len(owner_members)} members with roles/owner. "
                "Owner is the most privileged role; having many owners increases the risk "
                "of accidental or malicious changes."
            ),
            current_value=f"{len(owner_members)} owners: {', '.join(owner_members[:5])}{'...' if len(owner_members) > 5 else ''}",
            recommendation=(
                "Reduce the number of owners to 1–2 break-glass accounts. "
                "Use roles/editor or custom roles with least-privilege principles for regular work."
            ),
        ))

    # Flag service accounts with primitive roles
    for binding in all_bindings:
        role = binding.get("role", "")
        if role not in _HIGH_RISK_ROLES:
            continue
        for member in binding.get("members", []):
            if member.startswith("serviceAccount:"):
                sa_name = member[len("serviceAccount:"):]
                suggestions.append(_suggestion(
                    sid=f"iam-sa-{role.replace('/', '-')}-{sa_name[:30]}",
                    category="iam",
                    severity="critical" if role == "roles/owner" else "warning",
                    suggestion_type="security",
                    resource_name=sa_name,
                    resource_type="IAM",
                    title=f"Service account has broad '{role}' role",
                    description=(
                        f"Service account '{sa_name}' has been granted '{role}', a primitive "
                        "role that grants very broad permissions. This violates the principle "
                        "of least privilege."
                    ),
                    current_value=f"{member}: {role}",
                    recommendation=(
                        "Replace the primitive role with a predefined or custom role that "
                        "grants only the specific permissions required by this service account."
                    ),
                ))

    # Flag users/groups with roles/owner (not just service accounts)
    for binding in all_bindings:
        role = binding.get("role", "")
        if role != "roles/owner":
            continue
        for member in binding.get("members", []):
            if member.startswith("user:") or member.startswith("group:"):
                display = member.split(":", 1)[1] if ":" in member else member
                suggestions.append(_suggestion(
                    sid=f"iam-owner-{display[:40]}",
                    category="iam",
                    severity="warning",
                    suggestion_type="security",
                    resource_name=display,
                    resource_type="IAM",
                    title=f"'{display}' has project Owner role",
                    description=(
                        f"'{member}' holds the roles/owner role on the project. "
                        "This grants full control including billing and IAM management."
                    ),
                    current_value=f"{member}: roles/owner",
                    recommendation=(
                        "Reduce to roles/editor or a custom role with required permissions. "
                        "Keep roles/owner only for break-glass emergency accounts."
                    ),
                ))

    # Detect allUsers / allAuthenticatedUsers in any binding
    for binding in all_bindings:
        role = binding.get("role", "")
        for member in binding.get("members", []):
            if member in ("allUsers", "allAuthenticatedUsers"):
                suggestions.append(_suggestion(
                    sid=f"iam-public-{role.replace('/', '-')}",
                    category="iam",
                    severity="critical",
                    suggestion_type="security",
                    resource_name="Project",
                    resource_type="IAM",
                    title=f"Public identity '{member}' has role '{role}'",
                    description=(
                        f"The IAM binding grants '{role}' to '{member}', meaning anyone on "
                        "the internet (allUsers) or any authenticated Google account "
                        "(allAuthenticatedUsers) can exercise this role on the project."
                    ),
                    current_value=f"{member}: {role}",
                    recommendation=(
                        "Remove this binding immediately unless intentionally exposing a "
                        "public API. Use specific user/group/service-account identities instead."
                    ),
                ))

    return suggestions


def get_suggestions(credentials: dict) -> dict:
    """Analyse GCP resources, billing, and IAM to produce actionable suggestions.

    Each suggestion describes either an *over-used* configuration (resource is
    provisioned beyond what its workload needs) or an *under-used* one (a
    cost-saving or security feature is available but not enabled).

    Returns a dict with keys:
      - ``suggestions``  : list of suggestion dicts (see ``_suggestion`` helper)
      - ``summary``      : counts per category and severity
      - ``resources_error``: error string if resource fetch failed (or None)
      - ``billing_error``:  error string if billing fetch failed (or None)
      - ``iam_error``    :  error string if IAM fetch failed (or None)
    """
    from datetime import date, timedelta  # noqa: PLC0415

    end = date.today()
    start = end - timedelta(days=89)

    all_suggestions: list[dict] = []
    resources_data: list[dict] = []
    billing_data: dict = {}
    iam_data: dict = {}
    resources_error: str | None = None
    billing_error: str | None = None
    iam_error: str | None = None

    # ── Resources ────────────────────────────────────────────────────────────
    try:
        resources_data = get_resources(credentials)
        # get_resources never raises – it falls back to mock on error
        if _last_resources_error.get("error"):
            resources_error = _last_resources_error["error"]
        all_suggestions.extend(_suggestions_from_resources(resources_data))
    except Exception as exc:
        resources_error = str(exc)[:300]

    # ── Billing ───────────────────────────────────────────────────────────────
    try:
        billing_data = get_overall_billing(credentials, start, end)
        if _last_billing_error.get("error"):
            billing_error = _last_billing_error["error"]
        all_suggestions.extend(_suggestions_from_billing(billing_data))
    except Exception as exc:
        billing_error = str(exc)[:300]

    # ── IAM ───────────────────────────────────────────────────────────────────
    try:
        iam_data = get_iam_roles(credentials)
        if "error" in iam_data:
            iam_error = iam_data["error"]
        else:
            all_suggestions.extend(_suggestions_from_iam(iam_data))
    except Exception as exc:
        iam_error = str(exc)[:300]

    vertex_suggestions, vertex_error = generate_vertexai_suggestions(
        provider="gcp",
        resources_data=resources_data,
        billing_data=billing_data,
        iam_data=iam_data,
        heuristic_suggestions=all_suggestions,
        billing_start=start,
        billing_end=end,
    )
    all_suggestions = vertex_suggestions + all_suggestions
    if vertex_error and not billing_error:
        billing_error = f"Vertex AI fallback: {vertex_error}"

    # ── Deduplicate by id (keep first occurrence) ─────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for s in all_suggestions:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)

    # ── Summary counts ────────────────────────────────────────────────────────
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
