import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { InputText } from 'primereact/inputtext';
import { Tag } from 'primereact/tag';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { MultiSelect } from 'primereact/multiselect';
import { Dropdown } from 'primereact/dropdown';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Badge } from 'primereact/badge';
import { Toast } from 'primereact/toast';
import { getResources, getResourceTypes, getResourceSummary } from '../api/cloudApi';

const STATUS_SEVERITY = {
  running: 'success', active: 'success', available: 'success',
  completed: 'success', 'in-use': 'success',
  RUNNING: 'success', ACTIVE: 'success', RUNNABLE: 'success', Online: 'success', Available: 'success',
  stopped: 'warning', STOPPED: 'warning', Stopped: 'warning', TERMINATED: 'warning',
  unassociated: 'warning', pending: 'warning',
  error: 'danger', ERROR: 'danger', failed: 'danger',
};

// EC2 console-style sub-category navigation structure
const EC2_CATEGORIES = [
  {
    name: 'Instances',
    icon: 'pi-server',
    color: '#667eea',
    items: [
      { label: 'Instances', resourceType: 'EC2', description: 'Running and stopped EC2 instances' },
    ],
  },
  {
    name: 'Images',
    icon: 'pi-copy',
    color: '#4facfe',
    items: [
      { label: 'AMIs', resourceType: 'AMI', description: 'Amazon Machine Images owned by you' },
    ],
  },
  {
    name: 'Elastic Block Store',
    icon: 'pi-database',
    color: '#f093fb',
    items: [
      { label: 'Volumes', resourceType: 'EBS Volume', description: 'EBS block storage volumes' },
      { label: 'Snapshots', resourceType: 'EBS Snapshot', description: 'Point-in-time volume snapshots' },
    ],
  },
  {
    name: 'Network & Security',
    icon: 'pi-shield',
    color: '#43e97b',
    items: [
      { label: 'Security Groups', resourceType: 'Security Group', description: 'Virtual firewalls for instances' },
      { label: 'Elastic IPs', resourceType: 'Elastic IP', description: 'Static public IPv4 addresses' },
      { label: 'Placement Groups', resourceType: 'Placement Group', description: 'Logical groupings for instances' },
      { label: 'Key Pairs', resourceType: 'Key Pair', description: 'SSH key pairs for EC2 access' },
      { label: 'Network Interfaces', resourceType: 'Network Interface', description: 'Virtual network cards (ENIs)' },
    ],
  },
  {
    name: 'Load Balancing',
    icon: 'pi-sliders-h',
    color: '#fa709a',
    items: [
      { label: 'Load Balancers', resourceType: 'ELB', description: 'Application, Network, and Classic LBs' },
      { label: 'Target Groups', resourceType: 'Target Group', description: 'Routing targets for load balancers' },
    ],
  },
  {
    name: 'Auto Scaling',
    icon: 'pi-sort-alt',
    color: '#fda085',
    items: [
      { label: 'Auto Scaling Groups', resourceType: 'Auto Scaling Group', description: 'Automatically manage EC2 capacity' },
    ],
  },
];

// VPC console-style sub-category navigation structure
const VPC_CATEGORIES = [
  {
    name: 'Virtual Private Cloud',
    icon: 'pi-sitemap',
    color: '#667eea',
    items: [
      { label: 'Your VPCs', resourceType: 'VPC', description: 'Your virtual private clouds' },
      { label: 'Subnets', resourceType: 'Subnet', description: 'Subnets within your VPCs' },
      { label: 'Route Tables', resourceType: 'Route Table', description: 'Route tables controlling traffic' },
      { label: 'Internet Gateways', resourceType: 'Internet Gateway', description: 'Connect VPCs to the internet' },
      { label: 'Egress-only Internet Gateways', resourceType: 'Egress-only Internet Gateway', description: 'IPv6 egress-only internet access' },
      { label: 'DHCP Option Sets', resourceType: 'DHCP Option Set', description: 'DHCP configuration for VPCs' },
      { label: 'Elastic IPs', resourceType: 'Elastic IP', description: 'Static public IPv4 addresses' },
      { label: 'Managed Prefix Lists', resourceType: 'Managed Prefix List', description: 'Sets of IP address ranges' },
      { label: 'Endpoints', resourceType: 'VPC Endpoint', description: 'Private connections to AWS services' },
      { label: 'Endpoint Services', resourceType: 'VPC Endpoint Service', description: 'Your PrivateLink endpoint services' },
      { label: 'NAT Gateways', resourceType: 'NAT Gateway', description: 'Enable outbound internet for private subnets' },
      { label: 'Peering Connections', resourceType: 'VPC Peering Connection', description: 'VPC-to-VPC routing connections' },
    ],
  },
  {
    name: 'Security',
    icon: 'pi-shield',
    color: '#43e97b',
    items: [
      { label: 'Network ACLs', resourceType: 'Network ACL', description: 'Stateless subnet-level firewall rules' },
      { label: 'Security Groups', resourceType: 'Security Group', description: 'Stateful instance-level firewall rules' },
    ],
  },
  {
    name: 'DNS Firewall',
    icon: 'pi-ban',
    color: '#f093fb',
    items: [
      { label: 'Rule Groups', resourceType: 'DNS Firewall Rule Group', description: 'DNS query filtering rule groups' },
      { label: 'Domain Lists', resourceType: 'DNS Firewall Domain List', description: 'Lists of domains for DNS filtering' },
    ],
  },
  {
    name: 'Network Firewall',
    icon: 'pi-lock',
    color: '#fa709a',
    items: [
      { label: 'Firewalls', resourceType: 'Network Firewall', description: 'Stateful network traffic inspection' },
      { label: 'Firewall Policies', resourceType: 'Firewall Policy', description: 'Rules and settings for firewalls' },
      { label: 'Rule Groups', resourceType: 'Network Firewall Rule Group', description: 'Reusable sets of firewall rules' },
      { label: 'TLS Inspection Configurations', resourceType: 'TLS Inspection Configuration', description: 'TLS traffic decryption configurations' },
    ],
  },
  {
    name: 'Virtual Private Network (VPN)',
    icon: 'pi-key',
    color: '#4facfe',
    items: [
      { label: 'Customer Gateways', resourceType: 'Customer Gateway', description: 'Your on-premises VPN devices' },
      { label: 'Virtual Private Gateways', resourceType: 'Virtual Private Gateway', description: 'AWS side of Site-to-Site VPN' },
      { label: 'Site-to-Site VPN Connections', resourceType: 'VPN Connection', description: 'Encrypted tunnels to on-premises' },
    ],
  },
  {
    name: 'Transit Gateways',
    icon: 'pi-share-alt',
    color: '#fda085',
    items: [
      { label: 'Transit Gateways', resourceType: 'Transit Gateway', description: 'Central hub for VPC and on-premises routing' },
      { label: 'Transit Gateway Attachments', resourceType: 'Transit Gateway Attachment', description: 'VPCs and VPNs attached to transit gateways' },
      { label: 'Transit Gateway Route Tables', resourceType: 'Transit Gateway Route Table', description: 'Routing tables for transit gateways' },
    ],
  },
  {
    name: 'Traffic Mirroring',
    icon: 'pi-eye',
    color: '#a18cd1',
    items: [
      { label: 'Mirror Sessions', resourceType: 'Mirror Session', description: 'Sessions that capture and mirror traffic' },
      { label: 'Mirror Targets', resourceType: 'Mirror Target', description: 'Destinations for mirrored traffic' },
      { label: 'Mirror Filters', resourceType: 'Mirror Filter', description: 'Filters controlling mirrored traffic' },
    ],
  },
];

const TYPE_ICON = {
  EC2: 'pi-server', S3: 'pi-database', RDS: 'pi-database', Lambda: 'pi-bolt',
  ElastiCache: 'pi-refresh', OpenSearch: 'pi-search', SQS: 'pi-send',
  SNS: 'pi-bell', DynamoDB: 'pi-table', ECS: 'pi-server', EKS: 'pi-sitemap',
  ELB: 'pi-sliders-h', VPC: 'pi-sitemap', CloudWatch: 'pi-chart-line',
  MSK: 'pi-share-alt', Glue: 'pi-directions', Athena: 'pi-search',
  'API Gateway': 'pi-link', 'Route 53': 'pi-globe',
  CloudFormation: 'pi-clone', CloudTrail: 'pi-history',
  KMS: 'pi-key', 'Secrets Manager': 'pi-lock', Cognito: 'pi-users',
  ECR: 'pi-box', 'ECR Public': 'pi-globe', 'Step Functions': 'pi-directions',
  EFS: 'pi-folder', SES: 'pi-envelope', WAF: 'pi-shield',
  CodeBuild: 'pi-cog', CodePipeline: 'pi-sort-alt',
  QuickSight: 'pi-chart-bar', Inspector: 'pi-eye', 'X-Ray': 'pi-sitemap',
  'Transfer Family': 'pi-upload', EventBridge: 'pi-calendar',
  'Location Service': 'pi-map-marker',
  // EC2 sub-resources
  AMI: 'pi-copy', 'EBS Volume': 'pi-database', 'EBS Snapshot': 'pi-camera',
  'Security Group': 'pi-shield', 'Elastic IP': 'pi-map-marker',
  'Key Pair': 'pi-key', 'Network Interface': 'pi-sitemap',
  'Placement Group': 'pi-th-large', 'Target Group': 'pi-list',
  'Auto Scaling Group': 'pi-sort-alt',
  // VPC sub-resources
  Subnet: 'pi-sitemap', 'Route Table': 'pi-directions',
  'Internet Gateway': 'pi-globe', 'Egress-only Internet Gateway': 'pi-arrow-up',
  'DHCP Option Set': 'pi-cog', 'Managed Prefix List': 'pi-list',
  'VPC Endpoint': 'pi-link', 'VPC Endpoint Service': 'pi-link',
  'NAT Gateway': 'pi-arrow-right-arrow-left', 'VPC Peering Connection': 'pi-share-alt',
  'Network ACL': 'pi-shield',
  'DNS Firewall Rule Group': 'pi-ban', 'DNS Firewall Domain List': 'pi-globe',
  'Network Firewall': 'pi-lock', 'Firewall Policy': 'pi-file',
  'Network Firewall Rule Group': 'pi-list', 'TLS Inspection Configuration': 'pi-lock',
  'Customer Gateway': 'pi-server', 'Virtual Private Gateway': 'pi-cloud',
  'VPN Connection': 'pi-key',
  'Transit Gateway': 'pi-share-alt', 'Transit Gateway Attachment': 'pi-sitemap',
  'Transit Gateway Route Table': 'pi-directions',
  'Mirror Session': 'pi-eye', 'Mirror Target': 'pi-bullseye', 'Mirror Filter': 'pi-filter',
  // GCP / Azure
  'Compute Engine': 'pi-server', 'Cloud Storage': 'pi-database',
  BigQuery: 'pi-chart-bar', 'Cloud SQL': 'pi-database', GKE: 'pi-sitemap',
  'Cloud Functions': 'pi-bolt', 'Pub/Sub': 'pi-send', 'Cloud CDN': 'pi-globe',
  'Virtual Machines': 'pi-server', 'Storage Accounts': 'pi-database',
  'SQL Database': 'pi-database', 'Azure Functions': 'pi-bolt',
  AKS: 'pi-sitemap', 'Cosmos DB': 'pi-database',
  'Azure Cache for Redis': 'pi-refresh', 'Service Bus': 'pi-send',
  'Application Insights': 'pi-chart-line',
};

const TYPE_COLORS = [
  '#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a',
  '#a18cd1', '#fda085', '#30cfd0', '#a1c4fd', '#c4b5fd',
];

function statusTemplate(rowData) {
  const sev = STATUS_SEVERITY[rowData.status] || 'info';
  return <Tag value={rowData.status} severity={sev} rounded />;
}

function typeTemplate(rowData) {
  const icon = TYPE_ICON[rowData.type] || 'pi-box';
  return (
    <span className="flex align-items-center gap-2">
      <i className={`pi ${icon}`} style={{ color: '#818cf8' }} />
      <span className="font-medium">{rowData.type}</span>
    </span>
  );
}

function tagsTemplate(rowData) {
  if (!rowData.tags) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {rowData.tags.split(',').filter(Boolean).map((t) => (
        <span key={t} className="text-xs px-2 py-1"
          style={{ background: '#1e3a5f', borderRadius: '12px', color: '#93c5fd', fontFamily: 'monospace' }}>
          {t.trim()}
        </span>
      ))}
    </div>
  );
}

function detailsTemplate(rowData) {
  const fields = getDetailFields(rowData);
  if (!fields || fields.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {fields.map(({ label, value }) =>
        value !== null && value !== undefined && value !== '' ? (
          <span key={label} style={{
            background: '#0f2e4a', borderRadius: '8px', padding: '2px 8px',
            fontSize: '0.76rem', color: '#93c5fd', whiteSpace: 'nowrap',
          }}>
            <span style={{ color: '#64748b' }}>{label}:</span>{' '}
            <span style={{ color: '#e2e8f0' }}>{String(value)}</span>
          </span>
        ) : null
      )}
    </div>
  );
}

function getDetailFields(rowData) {
  switch (rowData.type) {
    case 'EC2':
      return [
        { label: 'Instance Type', value: rowData.instance_type || rowData.size },
        { label: 'AMI', value: rowData.ami_id },
        { label: 'Platform', value: rowData.platform },
        { label: 'Architecture', value: rowData.architecture },
        { label: 'AZ', value: rowData.availability_zone },
        { label: 'VPC', value: rowData.vpc_id },
        { label: 'Subnet', value: rowData.subnet_id },
        { label: 'Private IP', value: rowData.private_ip },
        { label: 'Public IP', value: rowData.public_ip },
        { label: 'Key Pair', value: rowData.key_name },
        { label: 'IAM Role', value: rowData.iam_role },
        { label: 'Monitoring', value: rowData.monitoring_state },
      ];
    case 'VPC':
      return [
        { label: 'VPC ID', value: rowData.id },
        { label: 'CIDR', value: rowData.cidr_block || rowData.size },
        { label: 'Default', value: rowData.is_default ? 'Yes' : null },
        { label: 'Subnets', value: rowData.subnet_count != null ? rowData.subnet_count : null },
        { label: 'NAT GWs', value: rowData.nat_gateway_count != null ? rowData.nat_gateway_count : null },
        { label: 'IGWs', value: rowData.igw_count != null ? rowData.igw_count : null },
        { label: 'EC2 Instances', value: rowData.ec2_instance_count != null ? rowData.ec2_instance_count : null },
      ];
    case 'S3':
      return [
        { label: 'Storage', value: rowData.storage_size || rowData.size },
      ];
    case 'RDS':
      return [
        { label: 'Class', value: rowData.instance_class },
        { label: 'Engine', value: rowData.engine },
        { label: 'Version', value: rowData.engine_version },
        { label: 'Multi-AZ', value: rowData.multi_az ? 'Yes' : rowData.multi_az === false ? 'No' : null },
        { label: 'Storage', value: rowData.size },
      ];
    case 'Lambda':
      return [
        { label: 'Runtime', value: rowData.runtime },
        { label: 'Memory', value: rowData.size },
        { label: 'Timeout', value: rowData.timeout ? `${rowData.timeout}s` : null },
      ];
    case 'ElastiCache':
      return [
        { label: 'Node Type', value: rowData.size },
        { label: 'Engine', value: rowData.engine },
        { label: 'Version', value: rowData.engine_version },
        { label: 'Nodes', value: rowData.num_nodes },
      ];
    case 'OpenSearch':
      return [
        { label: 'Instance Type', value: rowData.instance_type },
        { label: 'Instances', value: rowData.instance_count },
        { label: 'Engine', value: rowData.engine_version },
      ];
    case 'DynamoDB':
      return [
        { label: 'Size', value: rowData.size },
        { label: 'Item Count', value: rowData.item_count != null ? rowData.item_count.toLocaleString() : null },
        { label: 'Billing', value: rowData.billing_mode },
      ];
    case 'ECS':
      return [
        { label: 'Running Tasks', value: rowData.running_tasks_count },
        { label: 'Active Services', value: rowData.active_services_count },
      ];
    case 'EKS':
      return [
        { label: 'K8s Version', value: rowData.kubernetes_version },
        { label: 'Nodes', value: rowData.node_count },
        { label: 'Node Groups', value: rowData.node_groups },
      ];
    case 'ELB':
      return [
        { label: 'Type', value: rowData.lb_type },
        { label: 'Scheme', value: rowData.scheme },
      ];
    case 'MSK':
      return [
        { label: 'Brokers', value: rowData.broker_count },
        { label: 'Instance Type', value: rowData.broker_instance_type },
        { label: 'Kafka Version', value: rowData.kafka_version },
      ];
    case 'Glue':
      return [
        { label: 'Worker Type', value: rowData.worker_type },
        { label: 'Max Workers', value: rowData.max_workers },
      ];
    case 'ECR':
      return [
        { label: 'Images', value: rowData.image_count },
        { label: 'URI', value: rowData.repository_uri },
      ];
    case 'EFS':
      return [
        { label: 'Size', value: rowData.size },
      ];
    // GCP resource types
    case 'Compute Engine':
      return [
        { label: 'Machine Type', value: rowData.machine_type },
        { label: 'Zone', value: rowData.zone },
        { label: 'CPU Platform', value: rowData.cpu_platform },
        { label: 'Min CPU Platform', value: rowData.min_cpu_platform },
        { label: 'Boot Disk', value: rowData.boot_disk_name },
        { label: 'Boot Disk Size (GB)', value: rowData.boot_disk_size_gb },
        { label: 'Boot Disk Type', value: rowData.boot_disk_type },
        { label: 'Disk Count', value: rowData.disk_count },
        { label: 'Attached Disks', value: rowData.attached_disks },
        { label: 'Network', value: rowData.network },
        { label: 'Subnet', value: rowData.subnetwork },
        { label: 'Internal IP', value: rowData.network_ip },
        { label: 'External IP', value: rowData.external_ip },
        { label: 'Preemptible', value: rowData.preemptible != null ? (rowData.preemptible ? 'Yes' : 'No') : null },
        { label: 'Deletion Protection', value: rowData.deletion_protection != null ? (rowData.deletion_protection ? 'Yes' : 'No') : null },
        { label: 'Can IP Forward', value: rowData.can_ip_forward != null ? (rowData.can_ip_forward ? 'Yes' : 'No') : null },
        { label: 'Shielded Secure Boot', value: rowData.shielded_secure_boot != null ? (rowData.shielded_secure_boot ? 'Yes' : 'No') : null },
        { label: 'Service Account', value: rowData.service_account },
      ];
    case 'Persistent Disk':
      return [
        { label: 'Size (GB)', value: rowData.disk_size_gb },
        { label: 'Type', value: rowData.disk_type },
        { label: 'Zone', value: rowData.zone },
        { label: 'Source Image', value: rowData.source_image },
        { label: 'In Use By', value: rowData.in_use_by },
        { label: 'Snapshot Schedules', value: rowData.snapshot_schedule_count },
        { label: 'Encryption', value: rowData.encryption },
        { label: 'Block Size (B)', value: rowData.physical_block_size_bytes },
      ];
    case 'Cloud Storage':
      return [
        { label: 'Storage Class', value: rowData.storage_class },
        { label: 'Location Type', value: rowData.location_type },
        { label: 'Versioning', value: rowData.versioning },
        { label: 'Lifecycle Rules', value: rowData.lifecycle_rules },
        { label: 'Public Access', value: rowData.public_access },
        { label: 'Uniform Access', value: rowData.uniform_bucket_level_access != null ? (rowData.uniform_bucket_level_access ? 'Yes' : 'No') : null },
        { label: 'Encryption', value: rowData.encryption },
        { label: 'Logging', value: rowData.logging },
        { label: 'Retention (days)', value: rowData.retention_policy_days },
        { label: 'Requester Pays', value: rowData.requester_pays != null ? (rowData.requester_pays ? 'Yes' : 'No') : null },
        { label: 'CORS Rules', value: rowData.cors_rules },
      ];
    case 'BigQuery':
      return [
        { label: 'Dataset ID', value: rowData.dataset_id },
        { label: 'Location', value: rowData.location },
        { label: 'Tables', value: rowData.table_count },
        { label: 'Table Expiration', value: rowData.default_table_expiration_ms != null ? `${Math.round(rowData.default_table_expiration_ms / 86_400_000)}d` : null },
        { label: 'Partition Expiration', value: rowData.default_partition_expiration_ms != null ? `${Math.round(rowData.default_partition_expiration_ms / 86_400_000)}d` : null },
        { label: 'Description', value: rowData.description },
        { label: 'Access Entries', value: rowData.access_entries },
        { label: 'Labels', value: rowData.labels_count },
        { label: 'KMS Key', value: rowData.kms_key },
      ];
    case 'Cloud SQL':
      return [
        { label: 'Version', value: rowData.database_version },
        { label: 'Tier', value: rowData.tier },
        { label: 'Disk (GB)', value: rowData.disk_size_gb },
        { label: 'Disk Type', value: rowData.disk_type },
        { label: 'Availability', value: rowData.availability_type },
        { label: 'Backups', value: rowData.backup_enabled != null ? (rowData.backup_enabled ? 'Enabled' : 'Disabled') : null },
        { label: 'PITR', value: rowData.point_in_time_recovery != null ? (rowData.point_in_time_recovery ? 'Enabled' : 'Disabled') : null },
        { label: 'Connection Name', value: rowData.connection_name },
        { label: 'Private IP', value: rowData.ip_address },
        { label: 'Public IP', value: rowData.public_ip },
        { label: 'Maintenance', value: rowData.maintenance_window },
        { label: 'Deletion Protection', value: rowData.deletion_protection != null ? (rowData.deletion_protection ? 'Yes' : 'No') : null },
        { label: 'DB Flags', value: rowData.database_flags },
      ];
    case 'GKE':
      return [
        { label: 'K8s Version', value: rowData.current_master_version },
        { label: 'Nodes', value: rowData.node_count },
        { label: 'Node Type', value: rowData.node_machine_type },
        { label: 'Node Disk (GB)', value: rowData.node_disk_size_gb },
        { label: 'Node Disk Type', value: rowData.node_disk_type },
        { label: 'Node Image', value: rowData.node_image_type },
        { label: 'Node Pools', value: rowData.node_pool_count },
        { label: 'Network', value: rowData.network },
        { label: 'Subnet', value: rowData.subnetwork },
        { label: 'Autopilot', value: rowData.autopilot != null ? (rowData.autopilot ? 'Yes' : 'No') : null },
        { label: 'Private Cluster', value: rowData.private_cluster != null ? (rowData.private_cluster ? 'Yes' : 'No') : null },
        { label: 'Release Channel', value: rowData.release_channel },
        { label: 'Services CIDR', value: rowData.services_ipv4_cidr },
        { label: 'Cluster CIDR', value: rowData.cluster_ipv4_cidr },
        { label: 'Logging', value: rowData.logging_service },
        { label: 'Monitoring', value: rowData.monitoring_service },
      ];
    case 'Cloud Functions':
      return [
        { label: 'Runtime', value: rowData.runtime },
        { label: 'Memory (MB)', value: rowData.available_memory_mb },
        { label: 'Entry Point', value: rowData.entry_point },
        { label: 'Trigger', value: rowData.trigger_type },
        { label: 'Timeout', value: rowData.timeout },
        { label: 'Min Instances', value: rowData.min_instances },
        { label: 'Max Instances', value: rowData.max_instances },
        { label: 'Service Account', value: rowData.service_account },
        { label: 'Ingress', value: rowData.ingress_settings },
        { label: 'VPC Connector', value: rowData.vpc_connector },
        { label: 'Build Pool', value: rowData.build_worker_pool },
        { label: 'Source', value: rowData.source_archive },
      ];
    case 'Cloud Run':
      return [
        { label: 'Image', value: rowData.container_image },
        { label: 'CPU', value: rowData.cpu },
        { label: 'Memory', value: rowData.memory },
        { label: 'Min Instances', value: rowData.min_instances },
        { label: 'Max Instances', value: rowData.max_instances },
        { label: 'Port', value: rowData.port },
        { label: 'Concurrency', value: rowData.concurrency },
        { label: 'Timeout', value: rowData.timeout },
        { label: 'Service Account', value: rowData.service_account },
        { label: 'Ingress', value: rowData.ingress },
        { label: 'VPC Connector', value: rowData.vpc_connector },
        { label: 'Env Vars', value: rowData.env_var_count },
        { label: 'URL', value: rowData.url },
      ];
    case 'Pub/Sub':
      return [
        { label: 'Retention', value: rowData.message_retention_duration },
        { label: 'Subscriptions', value: rowData.subscription_count },
        { label: 'KMS Key', value: rowData.kms_key },
        { label: 'Schema', value: rowData.schema },
        { label: 'Storage Policy', value: rowData.message_storage_policy },
        { label: 'Labels', value: rowData.labels_count },
      ];
    case 'Cloud Memorystore':
      return [
        { label: 'Tier', value: rowData.tier },
        { label: 'Memory (GB)', value: rowData.memory_size_gb },
        { label: 'Redis Version', value: rowData.redis_version },
        { label: 'Host', value: rowData.host },
        { label: 'Port', value: rowData.port },
        { label: 'Network', value: rowData.network },
        { label: 'Auth', value: rowData.auth_enabled != null ? (rowData.auth_enabled ? 'Enabled' : 'Disabled') : null },
        { label: 'TLS', value: rowData.transit_encryption_mode },
        { label: 'Connect Mode', value: rowData.connect_mode },
        { label: 'Read Replicas', value: rowData.read_replicas_mode },
        { label: 'Replica Count', value: rowData.replica_count },
        { label: 'Maintenance Day', value: rowData.maintenance_day },
        { label: 'Maintenance Hour', value: rowData.maintenance_hour != null ? `${rowData.maintenance_hour}:00` : null },
      ];
    case 'Cloud Spanner':
      return [
        { label: 'Display Name', value: rowData.display_name },
        { label: 'Config', value: rowData.config },
        { label: 'Nodes', value: rowData.node_count },
        { label: 'Processing Units', value: rowData.processing_units },
        { label: 'Databases', value: rowData.database_count },
        { label: 'Backups', value: rowData.backup_count },
        { label: 'Backup Schedule', value: rowData.default_backup_schedule_type },
      ];
    case 'Firestore':
      return [
        { label: 'Type', value: rowData.type_detail },
        { label: 'Location', value: rowData.location_id },
        { label: 'Concurrency', value: rowData.concurrency_mode },
        { label: 'App Engine Integration', value: rowData.app_engine_integration },
        { label: 'PITR', value: rowData.point_in_time_recovery },
        { label: 'Delete Protection', value: rowData.delete_protection },
      ];
    case 'Dataflow':
      return [
        { label: 'Job Type', value: rowData.job_type },
        { label: 'SDK Version', value: rowData.sdk_version },
        { label: 'Workers', value: rowData.worker_count },
        { label: 'Max Workers', value: rowData.max_workers },
        { label: 'Worker Type', value: rowData.worker_machine_type },
        { label: 'Network', value: rowData.network },
        { label: 'Subnet', value: rowData.subnetwork },
        { label: 'Temp Bucket', value: rowData.temp_location },
        { label: 'Service Account', value: rowData.service_account },
      ];
    case 'Dataproc':
      return [
        { label: 'Version', value: rowData.software_version },
        { label: 'Master Type', value: rowData.master_machine_type },
        { label: 'Master Disk (GB)', value: rowData.master_disk_gb },
        { label: 'Workers', value: rowData.num_workers },
        { label: 'Worker Type', value: rowData.worker_machine_type },
        { label: 'Worker Disk (GB)', value: rowData.worker_disk_gb },
        { label: 'Preemptible Workers', value: rowData.preemptible_workers },
        { label: 'Network', value: rowData.network },
        { label: 'Internal IP Only', value: rowData.internal_ip_only != null ? (rowData.internal_ip_only ? 'Yes' : 'No') : null },
        { label: 'Component Gateway', value: rowData.component_gateway != null ? (rowData.component_gateway ? 'Yes' : 'No') : null },
        { label: 'Idle Delete TTL', value: rowData.idle_delete_ttl },
      ];
    case 'VPC Network':
      return [
        { label: 'Auto Subnets', value: rowData.auto_create_subnetworks == null ? null : rowData.auto_create_subnetworks ? 'Yes' : 'No' },
        { label: 'Routing Mode', value: rowData.routing_mode },
        { label: 'MTU', value: rowData.mtu },
        { label: 'Subnets', value: rowData.subnet_count },
        { label: 'Peerings', value: rowData.peering_count },
        { label: 'Firewall Rules', value: rowData.firewall_rule_count },
        { label: 'Routes', value: rowData.route_count },
        { label: 'Internal IPv6', value: rowData.internal_ipv6 != null ? (rowData.internal_ipv6 ? 'Yes' : 'No') : null },
      ];
    case 'Firewall Rule':
      return [
        { label: 'Direction', value: rowData.direction },
        { label: 'Priority', value: rowData.priority },
        { label: 'Protocol', value: rowData.protocol },
        { label: 'Ports', value: rowData.ports },
        { label: 'Source Ranges', value: rowData.source_ranges },
        { label: 'Dest Ranges', value: rowData.destination_ranges },
        { label: 'Target Tags', value: rowData.target_tags },
        { label: 'Disabled', value: rowData.disabled != null ? (rowData.disabled ? 'Yes' : 'No') : null },
        { label: 'Log Config', value: rowData.log_config },
      ];
    case 'Load Balancer':
      return [
        { label: 'Scheme', value: rowData.load_balancing_scheme },
        { label: 'Protocol', value: rowData.protocol },
        { label: 'IP Address', value: rowData.ip_address },
        { label: 'Port Range', value: rowData.port_range },
        { label: 'Backend Service', value: rowData.backend_service },
        { label: 'SSL Certificates', value: rowData.ssl_certificates },
        { label: 'Network Tier', value: rowData.network_tier },
      ];
    case 'Artifact Registry':
      return [
        { label: 'Format', value: rowData.format },
        { label: 'Images', value: rowData.image_count },
        { label: 'Size', value: rowData.size_bytes != null ? `${(rowData.size_bytes / 1_073_741_824).toFixed(1)} GB` : null },
        { label: 'KMS Key', value: rowData.kms_key },
        { label: 'Immutable Tags', value: rowData.immutable_tags != null ? (rowData.immutable_tags ? 'Yes' : 'No') : null },
        { label: 'Vuln Scanning', value: rowData.vulnerability_scanning },
        { label: 'Cleanup Policies', value: rowData.cleanup_policy_count },
      ];
    case 'Cloud Composer':
      return [
        { label: 'Airflow Version', value: rowData.airflow_version },
        { label: 'Size', value: rowData.environment_size },
        { label: 'Python Version', value: rowData.python_version },
        { label: 'GKE Cluster', value: rowData.gke_cluster },
        { label: 'DAG Bucket', value: rowData.dag_gcs_prefix },
        { label: 'Nodes', value: rowData.node_count },
        { label: 'Schedulers', value: rowData.scheduler_count },
        { label: 'Web Access', value: rowData.web_server_network_access_control },
      ];
    case 'Cloud Scheduler':
      return [
        { label: 'Schedule', value: rowData.schedule },
        { label: 'Timezone', value: rowData.timezone },
        { label: 'Target Type', value: rowData.target_type },
        { label: 'HTTP Method', value: rowData.http_method },
        { label: 'URI', value: rowData.uri },
        { label: 'Retry Count', value: rowData.retry_count },
        { label: 'Attempt Deadline', value: rowData.attempt_deadline },
      ];
    case 'Cloud Tasks':
      return [
        { label: 'Max Dispatches/s', value: rowData.max_dispatches_per_second },
        { label: 'Max Concurrent', value: rowData.max_concurrent_dispatches },
        { label: 'Max Attempts', value: rowData.max_attempts },
        { label: 'Max Retry Duration', value: rowData.max_retry_duration },
        { label: 'Min Backoff', value: rowData.min_backoff },
        { label: 'Max Backoff', value: rowData.max_backoff },
        { label: 'Max Doublings', value: rowData.max_doublings },
        { label: 'Tasks', value: rowData.task_count },
      ];
    case 'Filestore':
      return [
        { label: 'Tier', value: rowData.tier },
        { label: 'Capacity (GB)', value: rowData.capacity_gb },
        { label: 'Share Name', value: rowData.share_name },
        { label: 'File Shares', value: rowData.file_shares },
        { label: 'Network', value: rowData.network },
        { label: 'IP Addresses', value: rowData.ip_addresses },
        { label: 'Modes', value: rowData.modes },
        { label: 'Snapshots', value: rowData.snapshot_count },
        { label: 'KMS Key', value: rowData.kms_key },
      ];
    case 'Cloud Bigtable':
      return [
        { label: 'Clusters', value: rowData.cluster_count },
        { label: 'Cluster ID', value: rowData.cluster_id },
        { label: 'Nodes', value: rowData.node_count },
        { label: 'Storage Type', value: rowData.storage_type },
        { label: 'Tables', value: rowData.table_count },
        { label: 'Backups', value: rowData.backup_count },
        { label: 'Deletion Protection', value: rowData.deletion_protection != null ? (rowData.deletion_protection ? 'Yes' : 'No') : null },
        { label: 'KMS Key', value: rowData.kms_key },
      ];
    case 'Service Account':
      return [
        { label: 'Email', value: rowData.email },
        { label: 'Description', value: rowData.description },
        { label: 'OAuth2 Client ID', value: rowData.oauth2_client_id },
        { label: 'Keys', value: rowData.key_count },
        { label: 'Disabled', value: rowData.disabled != null ? (rowData.disabled ? 'Yes' : 'No') : null },
      ];
    case 'Cloud DNS':
      return [
        { label: 'DNS Name', value: rowData.dns_name },
        { label: 'Visibility', value: rowData.visibility },
        { label: 'Record Sets', value: rowData.record_set_count },
        { label: 'Name Servers', value: rowData.name_servers },
        { label: 'DNSSEC', value: rowData.dnssec },
        { label: 'Query Logging', value: rowData.log_dns_queries != null ? (rowData.log_dns_queries ? 'Enabled' : 'Disabled') : null },
      ];
    case 'Secret Manager':
      return [
        { label: 'Replication', value: rowData.replication },
        { label: 'Versions', value: rowData.version_count },
        { label: 'Rotation Period', value: rowData.rotation_period },
        { label: 'Expire Time', value: rowData.expire_time },
        { label: 'Topics', value: rowData.topics },
        { label: 'ETag', value: rowData.etag },
      ];
    case 'Cloud KMS':
      return [
        { label: 'Key Ring', value: rowData.key_ring },
        { label: 'Purpose', value: rowData.purpose },
        { label: 'Algorithm', value: rowData.algorithm },
        { label: 'Protection Level', value: rowData.protection_level },
        { label: 'Rotation Period', value: rowData.rotation_period },
        { label: 'Next Rotation', value: rowData.next_rotation_time },
        { label: 'Versions', value: rowData.version_count },
        { label: 'Destroy Duration', value: rowData.destroy_scheduled_duration },
      ];
    case 'API Gateway':
      return [
        { label: 'Hostname', value: rowData.default_hostname },
        { label: 'Managed Service', value: rowData.managed_service },
        { label: 'Config ID', value: rowData.config_id },
        { label: 'Labels', value: rowData.labels_count },
      ];
    case 'Cloud Logging':
      return [
        { label: 'Destination', value: rowData.destination },
        { label: 'Filter', value: rowData.filter },
        { label: 'Sink Type', value: rowData.sink_type },
        { label: 'Include Children', value: rowData.include_children != null ? (rowData.include_children ? 'Yes' : 'No') : null },
        { label: 'Writer Identity', value: rowData.writer_identity },
      ];
    case 'Cloud Monitoring':
      return [
        { label: 'Conditions', value: rowData.condition_count },
        { label: 'Channels', value: rowData.notification_channels },
        { label: 'Combiner', value: rowData.combiner },
        { label: 'Alert Strategy', value: rowData.alert_strategy },
        { label: 'Severity', value: rowData.severity },
        { label: 'Documentation', value: rowData.documentation_content },
      ];
    case 'Cloud Build':
      return [
        { label: 'Machine Type', value: rowData.machine_type },
        { label: 'Timeout', value: rowData.timeout },
        { label: 'Log Bucket', value: rowData.log_bucket },
        { label: 'Service Account', value: rowData.service_account },
        { label: 'Worker Pool', value: rowData.worker_pool },
        { label: 'Substitutions', value: rowData.substitution_count },
      ];
    case 'Cloud CDN':
      return [
        { label: 'Cache Mode', value: rowData.cache_mode },
        { label: 'Protocol', value: rowData.protocol },
        { label: 'Negative Caching', value: rowData.negative_caching != null ? (rowData.negative_caching ? 'Yes' : 'No') : null },
        { label: 'Signed URL Keys', value: rowData.signed_url_key_count },
        { label: 'Max TTL (s)', value: rowData.cdn_policy_max_ttl },
        { label: 'Default TTL (s)', value: rowData.cdn_policy_default_ttl },
        { label: 'Compression', value: rowData.compression_mode },
      ];
    case 'IP Address':
      return [
        { label: 'Address', value: rowData.address },
        { label: 'Address Type', value: rowData.address_type },
        { label: 'IP Version', value: rowData.ip_version },
        { label: 'Network Tier', value: rowData.network_tier },
        { label: 'In Use By', value: rowData.in_use_by },
      ];
    case 'App Engine':
      return [
        { label: 'Runtime', value: rowData.runtime },
        { label: 'Environment', value: rowData.env },
        { label: 'Serving Status', value: rowData.serving_status },
        { label: 'Instance Class', value: rowData.instance_class },
        { label: 'Min Instances', value: rowData.automatic_scaling_min_instances },
        { label: 'Max Instances', value: rowData.automatic_scaling_max_instances },
        { label: 'Inbound Services', value: rowData.inbound_services },
      ];
    case 'Vertex AI':
      return [
        { label: 'Display Name', value: rowData.display_name },
        { label: 'Model Type', value: rowData.model_type },
        { label: 'Framework', value: rowData.framework },
        { label: 'Artifact URI', value: rowData.artifact_uri },
        { label: 'Schema', value: rowData.schema_title },
        { label: 'Versions', value: rowData.version_count },
        { label: 'Deployments', value: rowData.deployment_count },
        { label: 'Training Pipeline', value: rowData.training_pipeline },
      ];
    case 'AMI':
      return [
        { label: 'Architecture', value: rowData.architecture },
        { label: 'Platform', value: rowData.platform },
        { label: 'Virtualization', value: rowData.virtualization_type },
        { label: 'Root Device', value: rowData.root_device_type },
        { label: 'Hypervisor', value: rowData.hypervisor },
        { label: 'Image Type', value: rowData.image_type },
        { label: 'Public', value: rowData.public != null ? (rowData.public ? 'Yes' : 'No') : null },
        { label: 'Created', value: rowData.creation_date },
        { label: 'Owner', value: rowData.owner_id },
      ];
    case 'EBS Volume':
      return [
        { label: 'Type', value: rowData.volume_type },
        { label: 'Size', value: rowData.size },
        { label: 'AZ', value: rowData.availability_zone },
        { label: 'IOPS', value: rowData.iops },
        { label: 'Throughput', value: rowData.throughput ? `${rowData.throughput} MiB/s` : null },
        { label: 'Encrypted', value: rowData.encrypted != null ? (rowData.encrypted ? 'Yes' : 'No') : null },
        { label: 'Attached To', value: rowData.attached_to },
        { label: 'Device', value: rowData.attached_device },
        { label: 'Snapshot', value: rowData.snapshot_id },
      ];
    case 'EBS Snapshot':
      return [
        { label: 'Volume', value: rowData.volume_id },
        { label: 'Size', value: rowData.size },
        { label: 'Progress', value: rowData.progress },
        { label: 'Encrypted', value: rowData.encrypted != null ? (rowData.encrypted ? 'Yes' : 'No') : null },
        { label: 'Started', value: rowData.start_time },
        { label: 'Description', value: rowData.description },
      ];
    case 'Security Group':
      return [
        { label: 'Group ID', value: rowData.group_id },
        { label: 'VPC', value: rowData.vpc_id },
        { label: 'Inbound Rules', value: rowData.inbound_rules },
        { label: 'Outbound Rules', value: rowData.outbound_rules },
        { label: 'Description', value: rowData.description },
      ];
    case 'Elastic IP':
      return [
        { label: 'Public IP', value: rowData.public_ip },
        { label: 'Private IP', value: rowData.private_ip },
        { label: 'Allocation ID', value: rowData.allocation_id },
        { label: 'Instance', value: rowData.instance_id },
        { label: 'Network Interface', value: rowData.network_interface_id },
        { label: 'Domain', value: rowData.domain },
      ];
    case 'Key Pair':
      return [
        { label: 'Key Pair ID', value: rowData.key_pair_id },
        { label: 'Type', value: rowData.key_type },
        { label: 'Fingerprint', value: rowData.fingerprint },
        { label: 'Created', value: rowData.creation_time },
      ];
    case 'Network Interface':
      return [
        { label: 'Interface Type', value: rowData.interface_type },
        { label: 'VPC', value: rowData.vpc_id },
        { label: 'Subnet', value: rowData.subnet_id },
        { label: 'Private IP', value: rowData.private_ip },
        { label: 'Public IP', value: rowData.public_ip },
        { label: 'MAC', value: rowData.mac_address },
        { label: 'Security Groups', value: rowData.security_groups },
        { label: 'Attached To', value: rowData.attached_to },
      ];
    case 'Placement Group':
      return [
        { label: 'Strategy', value: rowData.strategy },
        { label: 'Partitions', value: rowData.partition_count },
        { label: 'Spread Level', value: rowData.spread_level },
      ];
    case 'Target Group':
      return [
        { label: 'Protocol', value: rowData.protocol },
        { label: 'Port', value: rowData.port },
        { label: 'Target Type', value: rowData.target_type },
        { label: 'VPC', value: rowData.vpc_id },
        { label: 'Load Balancers', value: rowData.load_balancers },
        { label: 'Health Check', value: rowData.health_check_path || rowData.health_check_protocol },
        { label: 'Healthy Threshold', value: rowData.healthy_threshold },
        { label: 'Unhealthy Threshold', value: rowData.unhealthy_threshold },
      ];
    case 'Auto Scaling Group':
      return [
        { label: 'Min', value: rowData.min_size },
        { label: 'Max', value: rowData.max_size },
        { label: 'Desired', value: rowData.desired_capacity },
        { label: 'Launch Template', value: rowData.launch_template || rowData.launch_config },
        { label: 'Health Check', value: rowData.health_check_type },
        { label: 'AZs', value: rowData.availability_zones },
      ];
    default:
      return rowData.size ? [{ label: 'Size', value: rowData.size }] : [];
  }
}

function ec2ExpansionTemplate(rowData) {
  const chipStyle = (color) => ({
    background: `${color}22`, color, borderRadius: '8px',
    padding: '2px 10px', fontSize: '0.76rem', fontWeight: 600, whiteSpace: 'nowrap',
  });

  const fieldRow = (label, value, mono = false) => {
    if (value === null || value === undefined || value === '') return null;
    return (
      <div key={label} className="flex align-items-start gap-2 mb-1" style={{ fontSize: '0.82rem' }}>
        <span style={{ color: '#64748b', minWidth: '150px', flexShrink: 0 }}>{label}</span>
        <span style={{ color: mono ? '#93c5fd' : '#e2e8f0', fontFamily: mono ? 'monospace' : 'inherit', wordBreak: 'break-all' }}>
          {String(value)}
        </span>
      </div>
    );
  };

  const boolChip = (val, trueLabel = 'Yes', falseLabel = 'No') => {
    if (val === null || val === undefined) return '—';
    return val
      ? <span style={chipStyle('#4ade80')}>{trueLabel}</span>
      : <span style={chipStyle('#f87171')}>{falseLabel}</span>;
  };

  const sectionTitle = (icon, label, color) => (
    <div className="flex align-items-center gap-2 mb-2 mt-1">
      <i className={`pi ${icon}`} style={{ color }} />
      <span className="font-semibold text-sm" style={{ color }}>{label}</span>
    </div>
  );

  return (
    <div style={{ padding: '1rem 1.5rem', background: '#0f172a', borderRadius: '10px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>

        {/* Instance Details */}
        <div>
          {sectionTitle('pi-server', 'Instance Details', '#818cf8')}
          {fieldRow('Instance ID', rowData.id, true)}
          {fieldRow('Instance Type', rowData.instance_type || rowData.size, true)}
          {fieldRow('AMI ID', rowData.ami_id, true)}
          {fieldRow('Platform', rowData.platform)}
          {fieldRow('Architecture', rowData.architecture)}
          {fieldRow('Virtualization', rowData.virtualization_type)}
          {fieldRow('Hypervisor', rowData.hypervisor)}
          {fieldRow('Launch Time', rowData.launch_time)}
          {fieldRow('State Reason', rowData.state_transition_reason)}
        </div>

        {/* Network */}
        <div>
          {sectionTitle('pi-sitemap', 'Network', '#34d399')}
          {fieldRow('Availability Zone', rowData.availability_zone, true)}
          {fieldRow('VPC ID', rowData.vpc_id, true)}
          {fieldRow('Subnet ID', rowData.subnet_id, true)}
          {fieldRow('Private IP', rowData.private_ip, true)}
          {fieldRow('Private DNS', rowData.private_dns_name, true)}
          {fieldRow('Public IP', rowData.public_ip)}
          {fieldRow('Public DNS', rowData.public_dns_name)}
          {fieldRow('Security Groups', rowData.security_groups)}
          <div className="flex align-items-start gap-2 mb-1" style={{ fontSize: '0.82rem' }}>
            <span style={{ color: '#64748b', minWidth: '150px', flexShrink: 0 }}>Source/Dest Check</span>
            <span>{boolChip(rowData.source_dest_check, 'Enabled', 'Disabled')}</span>
          </div>
        </div>

        {/* Storage */}
        <div>
          {sectionTitle('pi-database', 'Storage', '#fb923c')}
          {fieldRow('Root Device Type', rowData.root_device_type)}
          {fieldRow('Root Device Name', rowData.root_device_name, true)}
          <div className="flex align-items-start gap-2 mb-1" style={{ fontSize: '0.82rem' }}>
            <span style={{ color: '#64748b', minWidth: '150px', flexShrink: 0 }}>EBS Optimized</span>
            <span>{boolChip(rowData.ebs_optimized)}</span>
          </div>
          {fieldRow('Block Devices', rowData.block_devices, true)}
        </div>

        {/* Security */}
        <div>
          {sectionTitle('pi-shield', 'Security', '#f472b6')}
          {fieldRow('Key Pair', rowData.key_name, true)}
          {fieldRow('IAM Role', rowData.iam_role, true)}
          {fieldRow('Tenancy', rowData.tenancy)}
        </div>

        {/* Performance & Monitoring */}
        <div>
          {sectionTitle('pi-chart-line', 'Performance & Monitoring', '#60a5fa')}
          <div className="flex align-items-start gap-2 mb-1" style={{ fontSize: '0.82rem' }}>
            <span style={{ color: '#64748b', minWidth: '150px', flexShrink: 0 }}>Monitoring</span>
            <span style={chipStyle(rowData.monitoring_state === 'enabled' ? '#4ade80' : '#94a3b8')}>
              {rowData.monitoring_state || '—'}
            </span>
          </div>
          {fieldRow('CPU Cores', rowData.cpu_core_count)}
          {fieldRow('Threads/Core', rowData.cpu_threads_per_core)}
        </div>

      </div>
    </div>
  );
}

function vpcExpansionTemplate(rowData) {
  const subnets = rowData.subnets || [];
  const natGateways = rowData.nat_gateways || [];
  const igws = rowData.internet_gateways || [];

  const chipStyle = (color) => ({
    background: `${color}22`, color, borderRadius: '8px',
    padding: '2px 8px', fontSize: '0.76rem', fontWeight: 600, whiteSpace: 'nowrap',
  });

  return (
    <div style={{ padding: '1rem 1.5rem', background: '#0f172a', borderRadius: '10px' }}>
      <div className="flex flex-wrap gap-4">
        {/* Subnets */}
        <div style={{ flex: '1 1 280px' }}>
          <div className="flex align-items-center gap-2 mb-2">
            <i className="pi pi-sitemap" style={{ color: '#60a5fa' }} />
            <span className="font-semibold text-sm" style={{ color: '#93c5fd' }}>
              Subnets ({subnets.length})
            </span>
          </div>
          {subnets.length === 0 ? (
            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>No subnets found</span>
          ) : (
            <div className="flex flex-column gap-1">
              {subnets.map((s) => (
                <div key={s.id} className="flex align-items-center gap-2 flex-wrap">
                  <span style={{ fontFamily: 'monospace', color: '#e2e8f0', fontSize: '0.8rem' }}>{s.id}</span>
                  <span style={chipStyle('#4ade80')}>{s.cidr}</span>
                  <span style={chipStyle('#94a3b8')}>{s.az}</span>
                  {s.public && <span style={chipStyle('#f59e0b')}>Public</span>}
                  {!s.public && <span style={chipStyle('#64748b')}>Private</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* NAT Gateways */}
        <div style={{ flex: '1 1 220px' }}>
          <div className="flex align-items-center gap-2 mb-2">
            <i className="pi pi-arrow-right-arrow-left" style={{ color: '#f59e0b' }} />
            <span className="font-semibold text-sm" style={{ color: '#fcd34d' }}>
              NAT Gateways ({natGateways.length})
            </span>
          </div>
          {natGateways.length === 0 ? (
            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>No NAT Gateways</span>
          ) : (
            <div className="flex flex-column gap-1">
              {natGateways.map((n) => (
                <div key={n.id} className="flex align-items-center gap-2 flex-wrap">
                  <span style={{ fontFamily: 'monospace', color: '#e2e8f0', fontSize: '0.8rem' }}>{n.id}</span>
                  <span style={chipStyle('#4ade80')}>{n.state}</span>
                  {n.subnet_id && <span style={{ color: '#94a3b8', fontSize: '0.76rem' }}>{n.subnet_id}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Internet Gateways */}
        <div style={{ flex: '1 1 200px' }}>
          <div className="flex align-items-center gap-2 mb-2">
            <i className="pi pi-globe" style={{ color: '#a78bfa' }} />
            <span className="font-semibold text-sm" style={{ color: '#c4b5fd' }}>
              Internet Gateways ({igws.length})
            </span>
          </div>
          {igws.length === 0 ? (
            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>No Internet Gateways</span>
          ) : (
            <div className="flex flex-column gap-1">
              {igws.map((igwId) => (
                <span key={igwId} style={{ fontFamily: 'monospace', color: '#e2e8f0', fontSize: '0.8rem' }}>
                  {igwId}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
const AWS_REGIONS = [
  { label: 'US East (N. Virginia) — us-east-1', value: 'us-east-1' },
  { label: 'US East (Ohio) — us-east-2', value: 'us-east-2' },
  { label: 'US West (N. California) — us-west-1', value: 'us-west-1' },
  { label: 'US West (Oregon) — us-west-2', value: 'us-west-2' },
  { label: 'Canada (Central) — ca-central-1', value: 'ca-central-1' },
  { label: 'Europe (Ireland) — eu-west-1', value: 'eu-west-1' },
  { label: 'Europe (London) — eu-west-2', value: 'eu-west-2' },
  { label: 'Europe (Frankfurt) — eu-central-1', value: 'eu-central-1' },
  { label: 'Europe (Paris) — eu-west-3', value: 'eu-west-3' },
  { label: 'Europe (Stockholm) — eu-north-1', value: 'eu-north-1' },
  { label: 'Europe (Spain) — eu-south-2', value: 'eu-south-2' },
  { label: 'Europe (Milan) — eu-south-1', value: 'eu-south-1' },
  { label: 'Europe (Zurich) — eu-central-2', value: 'eu-central-2' },
  { label: 'Mexico (Mexico City) — mx-central-1', value: 'mx-central-1' },
  { label: 'Asia Pacific (Tokyo) — ap-northeast-1', value: 'ap-northeast-1' },
  { label: 'Asia Pacific (Seoul) — ap-northeast-2', value: 'ap-northeast-2' },
  { label: 'Asia Pacific (Osaka) — ap-northeast-3', value: 'ap-northeast-3' },
  { label: 'Asia Pacific (Singapore) — ap-southeast-1', value: 'ap-southeast-1' },
  { label: 'Asia Pacific (Sydney) — ap-southeast-2', value: 'ap-southeast-2' },
  { label: 'Asia Pacific (Mumbai) — ap-south-1', value: 'ap-south-1' },
  { label: 'Asia Pacific (Hyderabad) — ap-south-2', value: 'ap-south-2' },
  { label: 'Asia Pacific (Malaysia) — ap-southeast-5', value: 'ap-southeast-5' },
  { label: 'Asia Pacific (Thailand) — ap-southeast-7', value: 'ap-southeast-7' },
  { label: 'Middle East (UAE) — me-central-1', value: 'me-central-1' },
  { label: 'Middle East (Bahrain) — me-south-1', value: 'me-south-1' },
  { label: 'Africa (Cape Town) — af-south-1', value: 'af-south-1' },
  { label: 'South America (São Paulo) — sa-east-1', value: 'sa-east-1' },
];

export default function ResourcesView({ provider }) {
  // GCP uses the new service-cards-first flow
  if (provider === 'gcp') {
    return <GcpResourcesView />;
  }
  // AWS uses the service-cards-first flow with size info
  if (provider === 'aws') {
    return <AwsResourcesView />;
  }
  return <FilteredResourcesView provider={provider} />;
}

// ---------------------------------------------------------------------------
// GCP: Google Cloud Console-style product navigation sidebar
// ---------------------------------------------------------------------------

// GCP product navigation tree — mirrors the Google Cloud Console left nav.
// Each section groups related products. Products may either map directly to a
// single resourceType, or have subItems (shown inline in the sidebar when the
// product is selected) that each map to a resourceType.
const GCP_PRODUCT_NAV = [
  // ── Compute ──────────────────────────────────────────────────────────────
  {
    section: 'Compute',
    color: '#4285F4',
    products: [
      {
        id: 'compute-engine',
        label: 'Compute Engine',
        icon: 'pi-server',
        subItems: [
          { label: 'VM Instances',       resourceType: 'Compute Engine',    description: 'Running and stopped virtual machine instances' },
          { label: 'Disks',              resourceType: 'Persistent Disk',   description: 'Persistent block storage volumes attached to VMs' },
          { label: 'Snapshots',          resourceType: 'Disk Snapshot',     description: 'Point-in-time snapshots of persistent disks' },
          { label: 'Images',             resourceType: 'Compute Image',     description: 'Custom OS images for VM creation' },
          { label: 'Instance Templates', resourceType: 'Instance Template', description: 'Reusable VM configuration templates' },
          { label: 'Instance Groups',    resourceType: 'Instance Group',    description: 'Managed and unmanaged instance groups' },
          { label: 'Autoscalers',        resourceType: 'Autoscaler',        description: 'Automatic scaling policies for instance groups' },
        ],
      },
      { id: 'gke', label: 'Kubernetes Engine', icon: 'pi-sitemap', resourceType: 'GKE' },
      {
        id: 'app-engine',
        label: 'App Engine',
        icon: 'pi-globe',
        subItems: [
          { label: 'Applications', resourceType: 'App Engine',         description: 'App Engine applications in this project' },
          { label: 'Services',     resourceType: 'App Engine Service', description: 'App Engine services and versions' },
        ],
      },
      { id: 'cloud-run',       label: 'Cloud Run',       icon: 'pi-forward', resourceType: 'Cloud Run' },
      { id: 'cloud-functions', label: 'Cloud Functions', icon: 'pi-bolt',    resourceType: 'Cloud Functions' },
    ],
  },

  // ── Storage ───────────────────────────────────────────────────────────────
  {
    section: 'Storage',
    color: '#0F9D58',
    products: [
      { id: 'cloud-storage', label: 'Cloud Storage', icon: 'pi-database', resourceType: 'Cloud Storage' },
      { id: 'filestore',     label: 'Filestore',     icon: 'pi-folder',   resourceType: 'Filestore' },
    ],
  },

  // ── Databases ─────────────────────────────────────────────────────────────
  {
    section: 'Databases',
    color: '#DB4437',
    products: [
      { id: 'cloud-sql',     label: 'Cloud SQL',     icon: 'pi-database', resourceType: 'Cloud SQL' },
      { id: 'cloud-spanner', label: 'Cloud Spanner', icon: 'pi-table',    resourceType: 'Cloud Spanner' },
      { id: 'firestore-db',  label: 'Firestore',     icon: 'pi-file',     resourceType: 'Firestore' },
      { id: 'cloud-bigtable',label: 'Cloud Bigtable',icon: 'pi-table',    resourceType: 'Cloud Bigtable' },
      { id: 'memorystore',   label: 'Memorystore',   icon: 'pi-refresh',  resourceType: 'Cloud Memorystore' },
      { id: 'alloydb',       label: 'AlloyDB',       icon: 'pi-database', resourceType: 'AlloyDB' },
    ],
  },

  // ── Analytics ─────────────────────────────────────────────────────────────
  {
    section: 'Analytics',
    color: '#F4B400',
    products: [
      {
        id: 'bigquery',
        label: 'BigQuery',
        icon: 'pi-chart-bar',
        subItems: [
          { label: 'Datasets',     resourceType: 'BigQuery',             description: 'BigQuery datasets in this project' },
          { label: 'Tables',       resourceType: 'BigQuery Table',       description: 'BigQuery tables and views' },
          { label: 'Reservations', resourceType: 'BigQuery Reservation', description: 'BigQuery capacity reservations' },
        ],
      },
      {
        id: 'pub-sub',
        label: 'Pub/Sub',
        icon: 'pi-send',
        subItems: [
          { label: 'Topics',        resourceType: 'Pub/Sub',              description: 'Pub/Sub topics' },
          { label: 'Subscriptions', resourceType: 'Pub/Sub Subscription', description: 'Pub/Sub push and pull subscriptions' },
          { label: 'Lite Topics',   resourceType: 'Pub/Sub Lite',         description: 'Pub/Sub Lite low-cost topics' },
        ],
      },
      { id: 'dataflow',    label: 'Dataflow',          icon: 'pi-sort-alt',  resourceType: 'Dataflow' },
      { id: 'dataproc',    label: 'Dataproc',          icon: 'pi-share-alt', resourceType: 'Dataproc' },
      { id: 'composer',    label: 'Cloud Composer',    icon: 'pi-cog',       resourceType: 'Cloud Composer' },
      { id: 'dataform',    label: 'Dataform',          icon: 'pi-file-edit', resourceType: 'Dataform' },
      { id: 'dataplex',    label: 'Dataplex',          icon: 'pi-sitemap',   resourceType: 'Dataplex' },
      { id: 'data-fusion', label: 'Cloud Data Fusion', icon: 'pi-sync',      resourceType: 'Cloud Data Fusion' },
    ],
  },

  // ── Networking ────────────────────────────────────────────────────────────
  {
    section: 'Networking',
    color: '#8B5CF6',
    products: [
      {
        id: 'vpc',
        label: 'VPC Network',
        icon: 'pi-sitemap',
        subItems: [
          { label: 'VPC Networks',       resourceType: 'VPC Network',         description: 'Your virtual private cloud networks' },
          { label: 'Subnets',            resourceType: 'Subnet',              description: 'Subnetworks within your VPCs' },
          { label: 'Firewall Rules',     resourceType: 'Firewall Rule',       description: 'Ingress and egress firewall rules' },
          { label: 'Routes',             resourceType: 'Route',               description: 'Custom routing rules for VPC traffic' },
          { label: 'Cloud Router',       resourceType: 'Cloud Router',        description: 'Dynamic routing for VPC networks' },
          { label: 'VPN Gateways',       resourceType: 'VPN Gateway',         description: 'Classic and HA VPN gateways' },
          { label: 'VPN Tunnels',        resourceType: 'VPN Tunnel',          description: 'Encrypted VPN tunnels' },
          { label: 'VPC Connectors',     resourceType: 'VPC Connector',       description: 'Serverless VPC access connectors' },
          { label: 'IP Addresses',       resourceType: 'IP Address',          description: 'Reserved external and internal IPs' },
        ],
      },
      {
        id: 'load-balancing',
        label: 'Load Balancing',
        icon: 'pi-arrows-h',
        subItems: [
          { label: 'Load Balancers',   resourceType: 'Load Balancer',   description: 'HTTP(S), SSL, and TCP load balancers' },
          { label: 'Backend Services', resourceType: 'Backend Service', description: 'Backend service configurations' },
          { label: 'Health Checks',    resourceType: 'Health Check',    description: 'Health check probe configurations' },
          { label: 'URL Maps',         resourceType: 'URL Map',         description: 'URL map routing rules' },
          { label: 'HTTP Proxies',     resourceType: 'HTTP Proxy',      description: 'Target HTTP proxy resources' },
          { label: 'HTTPS Proxies',    resourceType: 'HTTPS Proxy',     description: 'Target HTTPS proxy resources' },
          { label: 'SSL Certificates', resourceType: 'SSL Certificate', description: 'Managed and self-managed TLS certificates' },
        ],
      },
      {
        id: 'hybrid-connectivity',
        label: 'Hybrid Connectivity',
        icon: 'pi-share-alt',
        subItems: [
          { label: 'Interconnects',        resourceType: 'Interconnect',        description: 'Dedicated and partner interconnect attachments' },
          { label: 'Network Connectivity', resourceType: 'Network Connectivity', description: 'Network Connectivity Center hubs' },
        ],
      },
      { id: 'cloud-dns',       label: 'Cloud DNS',           icon: 'pi-globe',   resourceType: 'Cloud DNS' },
      { id: 'cloud-cdn',       label: 'Cloud CDN',           icon: 'pi-cloud',   resourceType: 'Cloud CDN' },
      { id: 'cloud-armor',     label: 'Cloud Armor',         icon: 'pi-shield',  resourceType: 'Cloud Armor' },
      { id: 'cert-manager',    label: 'Certificate Manager', icon: 'pi-verified',resourceType: 'Certificate Manager' },
    ],
  },

  // ── Operations ────────────────────────────────────────────────────────────
  {
    section: 'Operations',
    color: '#10B981',
    products: [
      { id: 'cloud-monitoring',   label: 'Cloud Monitoring',            icon: 'pi-chart-line', resourceType: 'Cloud Monitoring' },
      { id: 'cloud-logging',      label: 'Cloud Logging',               icon: 'pi-list',       resourceType: 'Cloud Logging' },
      { id: 'cloud-build',        label: 'Cloud Build',                 icon: 'pi-cog',        resourceType: 'Cloud Build' },
      { id: 'artifact-registry',  label: 'Artifact Registry',          icon: 'pi-box',        resourceType: 'Artifact Registry' },
      { id: 'cloud-source-repos', label: 'Cloud Source Repositories',  icon: 'pi-code',       resourceType: 'Cloud Source Repositories' },
    ],
  },

  // ── Security ──────────────────────────────────────────────────────────────
  {
    section: 'Security',
    color: '#EA4335',
    products: [
      { id: 'service-accounts', label: 'Service Accounts',    icon: 'pi-users',  resourceType: 'Service Account' },
      { id: 'secret-manager',   label: 'Secret Manager',      icon: 'pi-lock',   resourceType: 'Secret Manager' },
      { id: 'cloud-kms',        label: 'Cloud KMS',           icon: 'pi-key',    resourceType: 'Cloud KMS' },
      { id: 'binary-auth',      label: 'Binary Authorization',icon: 'pi-shield', resourceType: 'Binary Authorization' },
    ],
  },

  // ── Serverless ────────────────────────────────────────────────────────────
  {
    section: 'Serverless',
    color: '#F97316',
    products: [
      { id: 'cloud-scheduler',  label: 'Cloud Scheduler',  icon: 'pi-calendar', resourceType: 'Cloud Scheduler' },
      { id: 'cloud-tasks',      label: 'Cloud Tasks',      icon: 'pi-list',     resourceType: 'Cloud Tasks' },
      { id: 'api-gateway',      label: 'API Gateway',      icon: 'pi-link',     resourceType: 'API Gateway' },
      { id: 'cloud-endpoints',  label: 'Cloud Endpoints',  icon: 'pi-share-alt',resourceType: 'Cloud Endpoints' },
      { id: 'cloud-workflows',  label: 'Cloud Workflows',  icon: 'pi-cog',      resourceType: 'Cloud Workflows' },
    ],
  },

  // ── AI & ML ───────────────────────────────────────────────────────────────
  {
    section: 'AI & ML',
    color: '#A855F7',
    products: [
      { id: 'vertex-ai',           label: 'Vertex AI',           icon: 'pi-star',      resourceType: 'Vertex AI' },
      { id: 'vertex-ai-notebooks', label: 'Vertex AI Notebooks', icon: 'pi-book',      resourceType: 'Vertex AI Notebooks' },
    ],
  },
];

// Flat product id → {product, sectionColor} lookup built from GCP_PRODUCT_NAV
const GCP_PRODUCT_LOOKUP = {};
GCP_PRODUCT_NAV.forEach((section) => {
  section.products.forEach((product) => {
    GCP_PRODUCT_LOOKUP[product.id] = { ...product, sectionColor: section.color };
  });
});

// ---------------------------------------------------------------------------
// GcpResourcesView — Google Cloud Console-style navigation
// Layout: persistent left sidebar (products) + dynamic right content area.
//
// States:
//   activeProductId = null          → overview / welcome screen
//   activeProductId set, no subItems → resource table for that product's type
//   activeProductId set, has subItems, activeResourceType = null
//                                   → sub-category cards for the product
//   activeProductId set, has subItems, activeResourceType set
//                                   → resource table for that sub-item's type
// ---------------------------------------------------------------------------

function GcpResourcesView() {
  const toast = useRef(null);

  // Summary data from the API: [{type, count}, ...]
  const [summary, setSummary] = useState([]);
  const [apiError, setApiError] = useState(null);
  const [requiredRoles, setRequiredRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Navigation state
  const [activeProductId, setActiveProductId] = useState(null);
  const [activeResourceType, setActiveResourceType] = useState(null);

  // Sidebar state
  const [expandedSections, setExpandedSections] = useState(
    () => new Set(GCP_PRODUCT_NAV.map((s) => s.section)),
  );
  const [sidebarSearch, setSidebarSearch] = useState('');

  // Resource table state
  const [serviceResources, setServiceResources] = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [globalFilter, setGlobalFilter] = useState('');

  // resource type → count lookup built from summary
  const countByType = useMemo(() => {
    const map = {};
    summary.forEach((s) => { map[s.type] = s.count; });
    return map;
  }, [summary]);

  // ── Data fetching ──────────────────────────────────────────────────────────
  useEffect(() => {
    getResourceSummary()
      .then((r) => {
        setSummary(r.data.summary);
        if (r.data.api_error) {
          setApiError(r.data.api_error);
          setRequiredRoles(r.data.required_roles || []);
        }
      })
      .catch((err) => {
        const msg = err?.response?.data?.detail || 'Failed to load resource summary';
        setError(msg);
        toast.current?.show({
          severity: 'error',
          summary: 'Unable to retrieve resources',
          detail: msg,
          life: 15000,
          sticky: false,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const loadResources = useCallback(async (resourceType) => {
    setActiveResourceType(resourceType);
    setLoadingResources(true);
    setGlobalFilter('');
    try {
      const res = await getResources([resourceType], null);
      setServiceResources(res.data.resources);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to load resources';
      setError(msg);
      toast.current?.show({ severity: 'error', summary: 'Error', detail: msg, life: 15000 });
    } finally {
      setLoadingResources(false);
    }
  }, []);

  // ── Navigation handlers ────────────────────────────────────────────────────
  const handleProductClick = useCallback((product) => {
    setActiveProductId(product.id);
    setGlobalFilter('');
    if (product.subItems) {
      // Products with sub-items show a sub-category card view first
      setActiveResourceType(null);
      setServiceResources([]);
    } else {
      // Direct products load their resource table immediately
      loadResources(product.resourceType);
    }
  }, [loadResources]);

  const handleSubItemClick = useCallback((e, resourceType) => {
    e.stopPropagation();
    loadResources(resourceType);
  }, [loadResources]);

  const toggleSection = useCallback((sectionName) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionName)) next.delete(sectionName);
      else next.add(sectionName);
      return next;
    });
  }, []);

  // ── Early returns ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex justify-content-center align-items-center flex-column gap-3" style={{ minHeight: '300px' }}>
        <ProgressSpinner style={{ width: '50px', height: '50px' }} strokeWidth="4" />
        <span className="text-sm" style={{ color: '#94a3b8' }}>Loading GCP resources…</span>
      </div>
    );
  }

  if (error) {
    return (
      <>
        <Toast ref={toast} />
        <Message severity="error" text={error} className="w-full" />
      </>
    );
  }

  // ── Derived values ─────────────────────────────────────────────────────────
  const activeProduct = activeProductId ? GCP_PRODUCT_LOOKUP[activeProductId] : null;

  // Filter sidebar products by the search query
  const filteredNav = sidebarSearch.trim()
    ? GCP_PRODUCT_NAV
        .map((section) => ({
          ...section,
          products: section.products.filter((p) => {
            const q = sidebarSearch.toLowerCase();
            return (
              p.label.toLowerCase().includes(q) ||
              p.subItems?.some((s) => s.label.toLowerCase().includes(q))
            );
          }),
        }))
        .filter((section) => section.products.length > 0)
    : GCP_PRODUCT_NAV;

  // ── Sidebar ────────────────────────────────────────────────────────────────
  const sidebar = (
    <div style={{
      width: '280px',
      flexShrink: 0,
      background: '#1e293b',
      borderRadius: '12px',
      border: '1px solid #334155',
      display: 'flex',
      flexDirection: 'column',
      maxHeight: 'calc(100vh - 160px)',
    }}>
      {/* Header + search */}
      <div style={{ padding: '16px 18px', borderBottom: '1px solid #334155', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <i className="pi pi-cloud" style={{ color: '#4285F4', fontSize: '1.1rem' }} />
          <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '1rem' }}>GCP Console</span>
        </div>
        <div style={{ position: 'relative' }}>
          <i className="pi pi-search" style={{
            position: 'absolute', left: '10px', top: '50%',
            transform: 'translateY(-50%)', color: '#64748b',
            fontSize: '0.85rem', pointerEvents: 'none',
          }} />
          <input
            type="text"
            value={sidebarSearch}
            onChange={(e) => setSidebarSearch(e.target.value)}
            placeholder="Search products…"
            style={{
              width: '100%', boxSizing: 'border-box',
              paddingLeft: '32px', paddingRight: '10px',
              paddingTop: '7px', paddingBottom: '7px',
              background: '#0f172a', border: '1px solid #334155',
              borderRadius: '8px', color: '#e2e8f0',
              fontSize: '0.88rem', outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Product list */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {filteredNav.map((section) => (
          <div key={section.section}>
            {/* Section label — click to collapse/expand */}
            <div
              onClick={() => toggleSection(section.section)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px 4px', cursor: 'pointer',
              }}
            >
              <span style={{
                color: '#475569', fontSize: '0.75rem', fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.07em',
              }}>
                {section.section}
              </span>
              <i
                className={`pi ${expandedSections.has(section.section) ? 'pi-chevron-down' : 'pi-chevron-right'}`}
                style={{ color: '#475569', fontSize: '0.62rem' }}
              />
            </div>

            {expandedSections.has(section.section) && section.products.map((product) => {
              const isActive = activeProductId === product.id;
              const productCount = product.subItems
                ? product.subItems.reduce((acc, s) => acc + (countByType[s.resourceType] || 0), 0)
                : (countByType[product.resourceType] || 0);

              return (
                <div key={product.id}>
                  {/* Product row */}
                  <div
                    onClick={() => handleProductClick(product)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '9px 12px 9px 18px', cursor: 'pointer',
                      background: isActive ? `${section.color}18` : 'transparent',
                      borderLeft: isActive ? `3px solid ${section.color}` : '3px solid transparent',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = '#ffffff08'; }}
                    onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0, flex: 1 }}>
                      <i
                        className={`pi ${product.icon}`}
                        style={{ color: isActive ? section.color : '#64748b', fontSize: '0.95rem', flexShrink: 0 }}
                      />
                      <span style={{
                        color: isActive ? '#f1f5f9' : '#94a3b8',
                        fontSize: '0.92rem', fontWeight: isActive ? 600 : 400,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {product.label}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                      {productCount > 0 && (
                        <span style={{
                          background: `${section.color}22`, color: section.color,
                          borderRadius: '10px', padding: '2px 8px',
                          fontSize: '0.75rem', fontWeight: 600,
                        }}>
                          {productCount}
                        </span>
                      )}
                      {product.subItems && (
                        <i className="pi pi-chevron-right" style={{ color: '#475569', fontSize: '0.62rem' }} />
                      )}
                    </div>
                  </div>

                  {/* Sub-items — shown inline under the product when it is active */}
                  {isActive && product.subItems && product.subItems.map((sub) => {
                    const isSubActive = activeResourceType === sub.resourceType;
                    return (
                      <div
                        key={sub.resourceType}
                        onClick={(e) => handleSubItemClick(e, sub.resourceType)}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          padding: '7px 12px 7px 42px', cursor: 'pointer',
                          background: isSubActive ? `${section.color}22` : 'transparent',
                          transition: 'background 0.15s',
                        }}
                        onMouseEnter={(e) => { if (!isSubActive) e.currentTarget.style.background = '#ffffff08'; }}
                        onMouseLeave={(e) => { if (!isSubActive) e.currentTarget.style.background = 'transparent'; }}
                      >
                        <span style={{
                          color: isSubActive ? '#f1f5f9' : '#64748b',
                          fontSize: '0.88rem', fontWeight: isSubActive ? 600 : 400,
                        }}>
                          {sub.label}
                        </span>
                        {(countByType[sub.resourceType] || 0) > 0 && (
                          <span style={{
                            background: `${section.color}22`, color: section.color,
                            borderRadius: '10px', padding: '2px 7px',
                            fontSize: '0.73rem', fontWeight: 600, flexShrink: 0,
                          }}>
                            {countByType[sub.resourceType]}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );

  // ── Overview panel (no product selected) ──────────────────────────────────
  const overviewPanel = (
    <div className="flex flex-column gap-4" style={{ flex: 1, minWidth: 0 }}>
      {/* IAM / API error banner */}
      {apiError && (
        <div style={{
          background: '#1e3a5f', border: '1px solid #2563eb',
          borderRadius: '12px', padding: '1rem 1.2rem',
        }}>
          <div className="flex align-items-start gap-2 mb-2">
            <i className="pi pi-info-circle" style={{ color: '#60a5fa', marginTop: '2px' }} />
            <div>
              <span className="font-semibold" style={{ color: '#93c5fd' }}>
                Showing mock data — could not connect to GCP
              </span>
              <div className="text-sm mt-1" style={{ color: '#7dd3fc', wordBreak: 'break-word' }}>
                Error: {apiError?.trim() || 'Unable to retrieve GCP resources'}
              </div>
            </div>
          </div>
          {requiredRoles.length > 0 && (
            <div className="mt-2">
              <span className="text-sm font-semibold" style={{ color: '#93c5fd' }}>
                Grant these IAM roles to your service account for real data:
              </span>
              <div className="flex flex-column gap-1 mt-1">
                {requiredRoles.map((r) => (
                  <div key={r.role} className="flex align-items-start gap-2 text-sm">
                    <span style={{
                      background: '#1d4ed8', color: '#bfdbfe',
                      borderRadius: '6px', padding: '1px 8px',
                      fontFamily: 'monospace', whiteSpace: 'nowrap',
                    }}>
                      {r.role}
                    </span>
                    <span style={{ color: '#94a3b8' }}>{r.purpose}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Summary header */}
      <div style={{
        background: '#1e293b', border: '1px solid #334155',
        borderRadius: '16px', padding: '1.5rem',
      }}>
        <div className="flex align-items-center gap-3 mb-4">
          <div style={{
            width: '48px', height: '48px', borderRadius: '12px',
            background: 'linear-gradient(135deg,#4285F4,#0F9D58)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 16px #4285F444',
          }}>
            <i className="pi pi-cloud" style={{ color: '#fff', fontSize: '1.3rem' }} />
          </div>
          <div>
            <div className="font-bold" style={{ color: '#f1f5f9', fontSize: '1.1rem' }}>
              Google Cloud Console
            </div>
            <div className="text-sm" style={{ color: '#94a3b8' }}>
              {summary.reduce((acc, s) => acc + (s.count || 0), 0).toLocaleString()} resources
              across {summary.length} services
            </div>
          </div>
        </div>

        {/* Per-section resource counts */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
          gap: '0.65rem',
        }}>
          {GCP_PRODUCT_NAV.map((section) => {
            const count = section.products.reduce((acc, p) => {
              if (p.subItems) {
                return acc + p.subItems.reduce((a, s) => a + (countByType[s.resourceType] || 0), 0);
              }
              return acc + (countByType[p.resourceType] || 0);
            }, 0);
            if (count === 0) return null;
            return (
              <div
                key={section.section}
                style={{
                  background: '#0f172a', border: '1px solid #334155',
                  borderRadius: '10px', padding: '10px 14px',
                  display: 'flex', alignItems: 'center', gap: '8px',
                }}
              >
                <span style={{ color: section.color, fontWeight: 700, fontSize: '1rem' }}>
                  {count}
                </span>
                <span style={{ color: '#64748b', fontSize: '0.78rem' }}>{section.section}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center', padding: '1rem 0' }}>
        <i className="pi pi-arrow-left mr-2" style={{ fontSize: '0.75rem' }} />
        Select a product from the left navigation to view resources
      </div>
    </div>
  );

  // ── Sub-category cards panel (product with subItems selected, no sub-item yet) ──
  const subCategoryPanel = activeProduct?.subItems ? (
    <div className="flex flex-column gap-4" style={{ flex: 1, minWidth: 0 }}>
      {/* Product heading */}
      <div className="flex align-items-center gap-2">
        <div style={{
          width: '34px', height: '34px', borderRadius: '8px',
          background: `${activeProduct.sectionColor}22`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <i className={`pi ${activeProduct.icon}`} style={{ color: activeProduct.sectionColor, fontSize: '0.95rem' }} />
        </div>
        <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '1.1rem' }}>
          {activeProduct.label}
        </span>
      </div>

      {/* Sub-category cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: '1rem',
      }}>
        {activeProduct.subItems.map((sub) => {
          const count = countByType[sub.resourceType] || 0;
          const icon = TYPE_ICON[sub.resourceType] || 'pi-box';
          return (
            <div
              key={sub.resourceType}
              onClick={() => loadResources(sub.resourceType)}
              style={{
                background: '#1e293b', border: '1px solid #334155',
                borderRadius: '14px', padding: '1.25rem 1.2rem',
                cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '0.75rem',
                transition: 'border-color 0.2s, transform 0.15s, box-shadow 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = activeProduct.sectionColor;
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = `0 4px 20px ${activeProduct.sectionColor}22`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#334155';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div className="flex align-items-center gap-3">
                <div style={{
                  width: '42px', height: '42px', borderRadius: '10px',
                  background: `${activeProduct.sectionColor}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <i className={`pi ${icon}`} style={{ color: activeProduct.sectionColor, fontSize: '1.1rem' }} />
                </div>
                <div>
                  <div style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.95rem' }}>
                    {sub.label}
                  </div>
                  <div style={{ color: '#64748b', fontSize: '0.78rem', marginTop: '2px' }}>
                    {sub.description}
                  </div>
                </div>
              </div>
              <div className="flex align-items-center justify-content-between">
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Resources</span>
                <span style={{
                  background: `${activeProduct.sectionColor}22`,
                  color: activeProduct.sectionColor,
                  borderRadius: '20px', padding: '3px 12px',
                  fontSize: '0.88rem', fontWeight: 700,
                }}>
                  {count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  ) : null;

  // ── Resource table panel ───────────────────────────────────────────────────
  const tableHeader = (
    <div
      className="flex justify-content-between align-items-center flex-wrap gap-3"
      style={{ background: '#1e293b', padding: '0.75rem 1rem' }}
    >
      <span className="text-lg font-semibold flex align-items-center gap-2" style={{ color: '#f1f5f9' }}>
        <i
          className={`pi ${TYPE_ICON[activeResourceType] || 'pi-box'}`}
          style={{ color: activeProduct?.sectionColor || '#4285F4' }}
        />
        {activeResourceType}
        <Badge
          value={serviceResources.length}
          style={{ background: 'linear-gradient(135deg,#4285F4,#0F9D58)', color: '#fff' }}
        />
      </span>
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search resources…"
          style={{ borderRadius: '20px' }}
        />
      </span>
    </div>
  );

  const resourceTablePanel = (
    <div className="flex flex-column gap-3" style={{ flex: 1, minWidth: 0 }}>
      {loadingResources ? (
        <div className="flex justify-content-center align-items-center flex-column gap-2" style={{ minHeight: '300px' }}>
          <ProgressSpinner style={{ width: '36px', height: '36px' }} strokeWidth="4" />
          <span className="text-sm" style={{ color: '#94a3b8' }}>Loading resources…</span>
        </div>
      ) : (
        <DataTable
          value={serviceResources}
          header={tableHeader}
          globalFilter={globalFilter}
          paginator
          rows={10}
          rowsPerPageOptions={[10, 25, 50]}
          sortMode="multiple"
          removableSort
          stripedRows
          dataKey="name"
          emptyMessage={
            <div className="flex flex-column align-items-center gap-2 py-6" style={{ color: '#94a3b8' }}>
              <i className="pi pi-inbox text-4xl" />
              <span>No resources found for {activeResourceType}.</span>
            </div>
          }
          style={{ borderRadius: '16px', overflow: 'hidden' }}
        >
          <Column field="name" header="Name" sortable style={{ minWidth: '160px', fontWeight: 500 }} />
          <Column field="type" header="Type" body={typeTemplate} sortable style={{ minWidth: '150px' }} />
          <Column field="region" header="Region / Zone" sortable style={{ minWidth: '120px' }} />
          <Column field="status" header="Status" body={statusTemplate} sortable style={{ minWidth: '110px' }} />
          <Column header="Configuration" body={detailsTemplate} style={{ minWidth: '260px' }} />
          <Column field="tags" header="Labels" body={tagsTemplate} style={{ minWidth: '220px' }} />
        </DataTable>
      )}
    </div>
  );

  // ── Determine which main content panel to show ────────────────────────────
  let mainContent;
  if (!activeProduct) {
    mainContent = overviewPanel;
  } else if (activeProduct.subItems && !activeResourceType) {
    mainContent = subCategoryPanel;
  } else {
    mainContent = resourceTablePanel;
  }

  return (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
      <Toast ref={toast} />
      {sidebar}
      {mainContent}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AWS: service cards → EC2 sub-categories (or direct resource table)
// ---------------------------------------------------------------------------

function sizeTemplate(rowData) {
  if (!rowData.size) return <span style={{ color: '#64748b' }}>—</span>;
  return (
    <span style={{ fontFamily: 'monospace', color: '#93c5fd', fontSize: '0.85rem' }}>
      {rowData.size}
    </span>
  );
}

// All resource types that belong to the EC2 console category
const EC2_RESOURCE_TYPES = new Set([
  'EC2', 'AMI', 'EBS Volume', 'EBS Snapshot',
  'Security Group', 'Elastic IP', 'Placement Group', 'Key Pair', 'Network Interface',
  'ELB', 'Target Group', 'Auto Scaling Group',
]);

// All resource types that belong to the VPC console category
const VPC_RESOURCE_TYPES = new Set([
  'VPC', 'Subnet', 'Route Table', 'Internet Gateway', 'Egress-only Internet Gateway',
  'DHCP Option Set', 'Managed Prefix List', 'VPC Endpoint', 'VPC Endpoint Service',
  'NAT Gateway', 'VPC Peering Connection',
  'Network ACL', 'Security Group',
  'DNS Firewall Rule Group', 'DNS Firewall Domain List',
  'Network Firewall', 'Firewall Policy', 'Network Firewall Rule Group', 'TLS Inspection Configuration',
  'Customer Gateway', 'Virtual Private Gateway', 'VPN Connection',
  'Transit Gateway', 'Transit Gateway Attachment', 'Transit Gateway Route Table',
  'Mirror Session', 'Mirror Target', 'Mirror Filter',
]);

// Map of sub-resource type → parent panel info (for search results)
const SUB_RESOURCE_META = {};
EC2_CATEGORIES.forEach((cat) => {
  cat.items.forEach((item) => {
    if (!SUB_RESOURCE_META[item.resourceType]) {
      SUB_RESOURCE_META[item.resourceType] = { parent: 'EC2', panel: 'EC2_PANEL', label: item.label };
    }
  });
});
VPC_CATEGORIES.forEach((cat) => {
  cat.items.forEach((item) => {
    if (!SUB_RESOURCE_META[item.resourceType]) {
      SUB_RESOURCE_META[item.resourceType] = { parent: 'VPC', panel: 'VPC_PANEL', label: item.label };
    }
  });
});

const AWS_SERVICE_CATEGORIES = [
  { name: 'Compute', icon: 'pi-server', color: '#f97316', services: ['EC2', 'ECS', 'EKS', 'Lambda'] },
  { name: 'Storage', icon: 'pi-database', color: '#f59e0b', services: ['S3', 'EFS', 'ECR', 'ECR Public'] },
  { name: 'Database', icon: 'pi-table', color: '#06b6d4', services: ['RDS', 'DynamoDB', 'ElastiCache', 'OpenSearch', 'MSK'] },
  { name: 'Networking', icon: 'pi-sitemap', color: '#8b5cf6', services: ['VPC', 'ELB', 'Route 53', 'API Gateway'] },
  { name: 'Security & Identity', icon: 'pi-shield', color: '#ef4444', services: ['KMS', 'Secrets Manager', 'WAF', 'Cognito'] },
  { name: 'Analytics', icon: 'pi-chart-bar', color: '#3b82f6', services: ['Athena', 'Glue', 'QuickSight', 'X-Ray'] },
  { name: 'Management & Monitoring', icon: 'pi-cog', color: '#10b981', services: ['CloudWatch', 'CloudFormation', 'CloudTrail', 'EventBridge'] },
  { name: 'Messaging & Integration', icon: 'pi-send', color: '#a855f7', services: ['SNS', 'SQS', 'SES', 'Step Functions'] },
  { name: 'Developer Tools', icon: 'pi-code', color: '#ec4899', services: ['CodeBuild', 'CodePipeline', 'Transfer Family', 'Location Service'] },
];

function AwsResourcesView() {
  const toast = useRef(null);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // null = service cards, 'EC2_PANEL' = EC2 sub-categories, or a specific type string
  const [selectedService, setSelectedService] = useState(null);
  // Tracks which panel the user navigated from so the back button goes to the right place.
  // null = came from top-level service cards, 'EC2_PANEL' = came from EC2 sub-categories,
  // 'VPC_PANEL' = came from VPC sub-categories.
  const [prevPanel, setPrevPanel] = useState(null);
  // Active sidebar category index within EC2/VPC panel (null = "All")
  const [activePanelCategory, setActivePanelCategory] = useState(null);
  const [serviceResources, setServiceResources] = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [globalFilter, setGlobalFilter] = useState('');
  const [serviceSearch, setServiceSearch] = useState('');
  const [expandedRows, setExpandedRows] = useState({});
  const [selectedRegion, setSelectedRegion] = useState('us-east-1');

  const fetchSummary = useCallback((region) => {
    setLoading(true);
    setError(null);
    getResourceSummary(region)
      .then((r) => setSummary(r.data.summary))
      .catch((err) => {
        const msg = err?.response?.data?.detail || 'Failed to load resource summary';
        setError(msg);
        toast.current?.show({ severity: 'error', summary: 'Error', detail: msg, life: 15000 });
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchSummary(selectedRegion);
  }, [fetchSummary, selectedRegion]);

  const resetDrillDown = useCallback((nextService = null, nextPrevPanel = null) => {
    setSelectedService(nextService);
    setPrevPanel(nextPrevPanel);
    setActivePanelCategory(null);
    setServiceResources([]);
    setGlobalFilter('');
    setExpandedRows({});
  }, []);

  // Shared resource-loading logic used by both the top-level service cards and
  // the EC2 panel sub-items.  Using a single helper avoids duplicating the
  // try/catch/finally pattern and ensures state is always reset consistently.
  const loadResources = useCallback(async (serviceType) => {
    setSelectedService(serviceType);
    setLoadingResources(true);
    setGlobalFilter('');
    setExpandedRows({});
    try {
      const res = await getResources([serviceType], selectedRegion);
      setServiceResources(res.data.resources);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to load resources';
      setError(msg);
      toast.current?.show({ severity: 'error', summary: 'Error', detail: msg, life: 15000 });
    } finally {
      setLoadingResources(false);
    }
  }, [selectedRegion]);

  const handleServiceClick = useCallback((serviceType) => {
    // EC2 opens the sub-category navigation panel instead of a resource table
    if (serviceType === 'EC2') {
      setPrevPanel(null);
      setActivePanelCategory(null);
      setSelectedService('EC2_PANEL');
      return;
    }
    // VPC opens the sub-category navigation panel instead of a resource table
    if (serviceType === 'VPC') {
      setPrevPanel(null);
      setActivePanelCategory(null);
      setSelectedService('VPC_PANEL');
      return;
    }
    // All other top-level service clicks: come from service cards (prevPanel = null)
    setPrevPanel(null);
    loadResources(serviceType);
  }, [loadResources]);

  // Used by EC2 panel sub-items — loads resources directly, bypassing the
  // 'EC2' → 'EC2_PANEL' redirect so that clicking "Instances" actually shows
  // the instances table.
  const handleEc2ItemClick = useCallback((resourceType) => {
    setPrevPanel('EC2_PANEL');
    loadResources(resourceType);
  }, [loadResources]);

  // Used by VPC panel sub-items — loads resources directly.
  const handleVpcItemClick = useCallback((resourceType) => {
    setPrevPanel('VPC_PANEL');
    loadResources(resourceType);
  }, [loadResources]);

  const handleBack = useCallback(() => {
    // Navigate back to wherever the user came from (EC2_PANEL, VPC_PANEL, or top-level)
    resetDrillDown(prevPanel, null);
  }, [prevPanel, resetDrillDown]);

  const handleBackToServices = useCallback(() => {
    resetDrillDown(null, null);
  }, [resetDrillDown]);

  if (loading) {
    return (
      <div className="flex justify-content-center align-items-center flex-column gap-3" style={{ minHeight: '300px' }}>
        <ProgressSpinner style={{ width: '50px', height: '50px' }} strokeWidth="4" />
        <span className="text-sm" style={{ color: '#94a3b8' }}>Loading services…</span>
      </div>
    );
  }

  if (error) return (
    <>
      <Toast ref={toast} />
      <Message severity="error" text={error} className="w-full" />
    </>
  );

  // --- EC2 sub-category panel (sidebar + content layout) ---
  if (selectedService === 'EC2_PANEL') {
    const visibleCategories = activePanelCategory === null
      ? EC2_CATEGORIES
      : EC2_CATEGORIES.filter((_, i) => i === activePanelCategory);
    return (
      <div className="flex flex-column gap-3">
        <Toast ref={toast} />

        {/* Header */}
        <div className="flex align-items-center justify-content-between flex-wrap gap-2">
          <div className="flex align-items-center gap-2">
            <Button
              icon="pi pi-arrow-left"
              label="Back to Services"
              className="p-button-text p-button-sm"
              onClick={handleBackToServices}
              style={{ color: '#a5b4fc' }}
            />
            <span style={{ color: '#475569' }}>›</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{
                width: '24px', height: '24px', borderRadius: '6px',
                background: '#667eea22',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <i className="pi pi-server" style={{ color: '#667eea', fontSize: '0.8rem' }} />
              </div>
              <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.95rem' }}>EC2 Dashboard</span>
            </div>
          </div>
          <div className="flex align-items-center gap-2">
            <i className="pi pi-map-marker" style={{ color: '#94a3b8', fontSize: '0.85rem' }} />
            <Dropdown
              value={selectedRegion}
              options={AWS_REGIONS}
              onChange={(e) => setSelectedRegion(e.value)}
              placeholder="Select a region…"
              filter
              filterPlaceholder="Search regions…"
              style={{ minWidth: '240px' }}
            />
          </div>
        </div>

        {/* Sidebar + Content */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
          {/* Left sidebar — category list */}
          <div style={{
            width: '210px',
            flexShrink: 0,
            background: '#1e293b',
            borderRadius: '12px',
            border: '1px solid #334155',
            overflow: 'hidden',
          }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Categories
            </div>
            {/* All option */}
            <div
              onClick={() => setActivePanelCategory(null)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 14px',
                cursor: 'pointer',
                background: activePanelCategory === null ? '#667eea22' : 'transparent',
                borderLeft: activePanelCategory === null ? '3px solid #667eea' : '3px solid transparent',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => { if (activePanelCategory !== null) e.currentTarget.style.background = '#ffffff08'; }}
              onMouseLeave={(e) => { if (activePanelCategory !== null) e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ color: activePanelCategory === null ? '#a5b4fc' : '#cbd5e1', fontSize: '0.85rem', fontWeight: activePanelCategory === null ? 600 : 400 }}>All</span>
              <span style={{ background: '#667eea22', color: '#818cf8', borderRadius: '10px', padding: '1px 7px', fontSize: '0.7rem', fontWeight: 600 }}>
                {EC2_CATEGORIES.reduce((a, c) => a + c.items.length, 0)}
              </span>
            </div>
            {EC2_CATEGORIES.map((cat, idx) => (
              <div
                key={cat.name}
                onClick={() => setActivePanelCategory(idx)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px',
                  cursor: 'pointer',
                  background: activePanelCategory === idx ? `${cat.color}18` : 'transparent',
                  borderLeft: activePanelCategory === idx ? `3px solid ${cat.color}` : '3px solid transparent',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { if (activePanelCategory !== idx) e.currentTarget.style.background = '#ffffff08'; }}
                onMouseLeave={(e) => { if (activePanelCategory !== idx) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <i className={`pi ${cat.icon}`} style={{ color: activePanelCategory === idx ? cat.color : '#64748b', fontSize: '0.8rem' }} />
                  <span style={{ color: activePanelCategory === idx ? '#f1f5f9' : '#94a3b8', fontSize: '0.82rem', fontWeight: activePanelCategory === idx ? 600 : 400 }}>
                    {cat.name}
                  </span>
                </div>
                <span style={{ background: `${cat.color}22`, color: cat.color, borderRadius: '10px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 600 }}>
                  {cat.items.length}
                </span>
              </div>
            ))}
          </div>

          {/* Right content area — resource items */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {visibleCategories.map((category) => (
              <div key={category.name} style={{ marginBottom: '1.25rem' }}>
                {/* Category header */}
                <div className="flex align-items-center gap-2" style={{ marginBottom: '0.75rem' }}>
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '7px',
                    background: `${category.color}22`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <i className={`pi ${category.icon}`} style={{ color: category.color, fontSize: '0.9rem' }} />
                  </div>
                  <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.9rem' }}>{category.name}</span>
                  <span style={{
                    background: `${category.color}22`, color: category.color,
                    borderRadius: '12px', padding: '1px 8px',
                    fontSize: '0.72rem', fontWeight: 600,
                  }}>
                    {category.items.length}
                  </span>
                </div>
                {/* Items grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.6rem' }}>
                  {category.items.map((item) => (
                    <div
                      key={item.resourceType}
                      onClick={() => handleEc2ItemClick(item.resourceType)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '0.65rem 0.9rem',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        background: '#1e293b',
                        border: `1px solid #334155`,
                        transition: 'border-color 0.15s, background 0.15s, box-shadow 0.15s',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = category.color;
                        e.currentTarget.style.background = `${category.color}11`;
                        e.currentTarget.style.boxShadow = `0 2px 12px ${category.color}22`;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#334155';
                        e.currentTarget.style.background = '#1e293b';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div style={{ color: '#e2e8f0', fontSize: '0.875rem', fontWeight: 500, marginBottom: '2px' }}>
                          {item.label}
                        </div>
                        <div style={{ color: '#64748b', fontSize: '0.72rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.description}
                        </div>
                      </div>
                      <i className="pi pi-chevron-right" style={{ color: `${category.color}88`, fontSize: '0.75rem', flexShrink: 0, marginLeft: '6px' }} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // --- VPC sub-category panel (sidebar + content layout) ---
  if (selectedService === 'VPC_PANEL') {
    const visibleVpcCategories = activePanelCategory === null
      ? VPC_CATEGORIES
      : VPC_CATEGORIES.filter((_, i) => i === activePanelCategory);
    return (
      <div className="flex flex-column gap-3">
        <Toast ref={toast} />

        {/* Header */}
        <div className="flex align-items-center justify-content-between flex-wrap gap-2">
          <div className="flex align-items-center gap-2">
            <Button
              icon="pi pi-arrow-left"
              label="Back to Services"
              className="p-button-text p-button-sm"
              onClick={handleBackToServices}
              style={{ color: '#a5b4fc' }}
            />
            <span style={{ color: '#475569' }}>›</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{
                width: '24px', height: '24px', borderRadius: '6px',
                background: '#667eea22',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <i className="pi pi-sitemap" style={{ color: '#667eea', fontSize: '0.8rem' }} />
              </div>
              <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.95rem' }}>VPC Dashboard</span>
            </div>
          </div>
          <div className="flex align-items-center gap-2">
            <i className="pi pi-map-marker" style={{ color: '#94a3b8', fontSize: '0.85rem' }} />
            <Dropdown
              value={selectedRegion}
              options={AWS_REGIONS}
              onChange={(e) => setSelectedRegion(e.value)}
              placeholder="Select a region…"
              filter
              filterPlaceholder="Search regions…"
              style={{ minWidth: '240px' }}
            />
          </div>
        </div>

        {/* Sidebar + Content */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
          {/* Left sidebar — category list */}
          <div style={{
            width: '210px',
            flexShrink: 0,
            background: '#1e293b',
            borderRadius: '12px',
            border: '1px solid #334155',
            overflow: 'hidden',
          }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Categories
            </div>
            {/* All option */}
            <div
              onClick={() => setActivePanelCategory(null)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 14px',
                cursor: 'pointer',
                background: activePanelCategory === null ? '#667eea22' : 'transparent',
                borderLeft: activePanelCategory === null ? '3px solid #667eea' : '3px solid transparent',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => { if (activePanelCategory !== null) e.currentTarget.style.background = '#ffffff08'; }}
              onMouseLeave={(e) => { if (activePanelCategory !== null) e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ color: activePanelCategory === null ? '#a5b4fc' : '#cbd5e1', fontSize: '0.85rem', fontWeight: activePanelCategory === null ? 600 : 400 }}>All</span>
              <span style={{ background: '#667eea22', color: '#818cf8', borderRadius: '10px', padding: '1px 7px', fontSize: '0.7rem', fontWeight: 600 }}>
                {VPC_CATEGORIES.reduce((a, c) => a + c.items.length, 0)}
              </span>
            </div>
            {VPC_CATEGORIES.map((cat, idx) => (
              <div
                key={cat.name}
                onClick={() => setActivePanelCategory(idx)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px',
                  cursor: 'pointer',
                  background: activePanelCategory === idx ? `${cat.color}18` : 'transparent',
                  borderLeft: activePanelCategory === idx ? `3px solid ${cat.color}` : '3px solid transparent',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { if (activePanelCategory !== idx) e.currentTarget.style.background = '#ffffff08'; }}
                onMouseLeave={(e) => { if (activePanelCategory !== idx) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <i className={`pi ${cat.icon}`} style={{ color: activePanelCategory === idx ? cat.color : '#64748b', fontSize: '0.8rem' }} />
                  <span style={{ color: activePanelCategory === idx ? '#f1f5f9' : '#94a3b8', fontSize: '0.82rem', fontWeight: activePanelCategory === idx ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '120px' }}>
                    {cat.name}
                  </span>
                </div>
                <span style={{ background: `${cat.color}22`, color: cat.color, borderRadius: '10px', padding: '1px 6px', fontSize: '0.68rem', fontWeight: 600, flexShrink: 0 }}>
                  {cat.items.length}
                </span>
              </div>
            ))}
          </div>

          {/* Right content area — resource items */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {visibleVpcCategories.map((category) => (
              <div key={category.name} style={{ marginBottom: '1.25rem' }}>
                {/* Category header */}
                <div className="flex align-items-center gap-2" style={{ marginBottom: '0.75rem' }}>
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '7px',
                    background: `${category.color}22`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <i className={`pi ${category.icon}`} style={{ color: category.color, fontSize: '0.9rem' }} />
                  </div>
                  <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.9rem' }}>{category.name}</span>
                  <span style={{
                    background: `${category.color}22`, color: category.color,
                    borderRadius: '12px', padding: '1px 8px',
                    fontSize: '0.72rem', fontWeight: 600,
                  }}>
                    {category.items.length}
                  </span>
                </div>
                {/* Items grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.6rem' }}>
                  {category.items.map((item) => (
                    <div
                      key={item.resourceType}
                      onClick={() => handleVpcItemClick(item.resourceType)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '0.65rem 0.9rem',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        background: '#1e293b',
                        border: `1px solid #334155`,
                        transition: 'border-color 0.15s, background 0.15s, box-shadow 0.15s',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = category.color;
                        e.currentTarget.style.background = `${category.color}11`;
                        e.currentTarget.style.boxShadow = `0 2px 12px ${category.color}22`;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#334155';
                        e.currentTarget.style.background = '#1e293b';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div style={{ color: '#e2e8f0', fontSize: '0.875rem', fontWeight: 500, marginBottom: '2px' }}>
                          {item.label}
                        </div>
                        <div style={{ color: '#64748b', fontSize: '0.72rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.description}
                        </div>
                      </div>
                      <i className="pi pi-chevron-right" style={{ color: `${category.color}88`, fontSize: '0.75rem', flexShrink: 0, marginLeft: '6px' }} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // --- Drill-down: resources for a specific service ---
  if (selectedService) {
    const tableHeader = (
      <div className="flex justify-content-between align-items-center flex-wrap gap-3"
           style={{ background: '#1e293b', padding: '0.75rem 1rem' }}>
        <span className="text-lg font-semibold flex align-items-center gap-2" style={{ color: '#f1f5f9' }}>
          <i className={`pi ${TYPE_ICON[selectedService] || 'pi-box'}`} style={{ color: '#818cf8' }} />
          {selectedService}
          <Badge value={serviceResources.length}
            style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff' }} />
        </span>
        <span className="p-input-icon-left">
          <i className="pi pi-search" />
          <InputText
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search resources…"
            style={{ borderRadius: '20px' }}
          />
        </span>
      </div>
    );

    const isVpc = selectedService === 'VPC';
    const isEc2 = selectedService === 'EC2';
    const hasExpansion = isVpc || isEc2;

    // Determine breadcrumb label for back button based on where the user came from.
    const backLabel = prevPanel === 'EC2_PANEL' ? 'Back to EC2' : prevPanel === 'VPC_PANEL' ? 'Back to VPC' : 'Back to Services';

    return (
      <div className="flex flex-column gap-4">
        <Toast ref={toast} />
        <div className="flex align-items-center gap-2 flex-wrap">
          <Button
            icon="pi pi-arrow-left"
            label={backLabel}
            className="p-button-text"
            onClick={handleBack}
            style={{ color: '#a5b4fc' }}
          />
          {isVpc && (
            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
              <i className="pi pi-info-circle mr-1" />
              Click the expand icon on a row to view subnets, NAT Gateways, and Internet Gateways
            </span>
          )}
          {isEc2 && (
            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
              <i className="pi pi-info-circle mr-1" />
              Click the expand icon on a row to view all EC2 instance details
            </span>
          )}
        </div>
        {loadingResources ? (
          <div className="flex justify-content-center align-items-center flex-column gap-2" style={{ minHeight: '200px' }}>
            <ProgressSpinner style={{ width: '36px', height: '36px' }} strokeWidth="4" />
            <span className="text-sm" style={{ color: '#94a3b8' }}>Loading resources…</span>
          </div>
        ) : (
          <DataTable
            value={serviceResources}
            header={tableHeader}
            globalFilter={globalFilter}
            paginator
            rows={10}
            rowsPerPageOptions={[10, 25, 50]}
            sortMode="multiple"
            removableSort
            stripedRows
            expandedRows={hasExpansion ? expandedRows : undefined}
            onRowToggle={hasExpansion ? (e) => setExpandedRows(e.data) : undefined}
            rowExpansionTemplate={isVpc ? vpcExpansionTemplate : isEc2 ? ec2ExpansionTemplate : undefined}
            dataKey="id"
            emptyMessage={
              <div className="flex flex-column align-items-center gap-2 py-6" style={{ color: '#94a3b8' }}>
                <i className="pi pi-inbox text-4xl" />
                <span>No resources found for {selectedService}.</span>
              </div>
            }
            style={{ borderRadius: '16px', overflow: 'hidden' }}
          >
            {hasExpansion && <Column expander style={{ width: '3rem' }} />}
            <Column field="name" header="Name" sortable style={{ minWidth: '160px', fontWeight: 500 }} />
            {isVpc && (
              <Column field="id" header="VPC ID" sortable
                body={(row) => (
                  <span style={{ fontFamily: 'monospace', color: '#93c5fd', fontSize: '0.85rem' }}>{row.id}</span>
                )}
                style={{ minWidth: '160px' }} />
            )}
            {isEc2 && (
              <Column field="id" header="Instance ID" sortable
                body={(row) => (
                  <span style={{ fontFamily: 'monospace', color: '#93c5fd', fontSize: '0.85rem' }}>{row.id}</span>
                )}
                style={{ minWidth: '160px' }} />
            )}
            <Column field="region" header={isEc2 ? 'Availability Zone' : 'Region'} sortable style={{ minWidth: '120px' }} />
            <Column field="status" header="Status" body={statusTemplate} sortable style={{ minWidth: '110px' }} />
            <Column header="Details" body={detailsTemplate} style={{ minWidth: '260px' }} />
            <Column field="tags" header="Tags" body={tagsTemplate} style={{ minWidth: '220px' }} />
          </DataTable>
        )}
      </div>
    );
  }

  // --- Overview: service cards grid with search bar ---
  const searchLower = serviceSearch.trim().toLowerCase();
  // Filter out EC2 and VPC sub-types from the top-level cards (they appear inside the respective panels)
  const topLevelSummary = summary.filter((s) =>
    (!EC2_RESOURCE_TYPES.has(s.type) || s.type === 'EC2') &&
    (!VPC_RESOURCE_TYPES.has(s.type) || s.type === 'VPC')
  );
  // When searching, also include matching sub-resources (EC2/VPC sub-types)
  const subResourceSummary = searchLower
    ? summary.filter((s) =>
        ((EC2_RESOURCE_TYPES.has(s.type) && s.type !== 'EC2') ||
         (VPC_RESOURCE_TYPES.has(s.type) && s.type !== 'VPC')) &&
        s.type.toLowerCase().includes(searchLower)
      )
    : [];
  const filteredSummary = searchLower
    ? [
        ...topLevelSummary.filter((s) => s.type.toLowerCase().includes(searchLower)),
        ...subResourceSummary,
      ]
    : topLevelSummary;

  const renderServiceCard = (svc, overrideColor) => {
    const icon = TYPE_ICON[svc.type] || 'pi-box';
    const colorIdx = svc.type.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % TYPE_COLORS.length;
    const color = overrideColor || TYPE_COLORS[colorIdx];
    const isEc2Card = svc.type === 'EC2';
    const isVpcCard = svc.type === 'VPC';
    const isPanelCard = isEc2Card || isVpcCard;
    const subMeta = SUB_RESOURCE_META[svc.type];
    return (
      <div
        key={svc.type}
        onClick={() => {
          if (subMeta && !isPanelCard) {
            loadResources(svc.type);
          } else {
            handleServiceClick(svc.type);
          }
        }}
        style={{
          background: '#1e293b',
          border: isPanelCard ? `1px solid ${color}66` : '1px solid #334155',
          borderRadius: '12px',
          padding: '1rem 0.9rem',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.6rem',
          transition: 'border-color 0.2s, transform 0.15s, box-shadow 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = color;
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = `0 4px 20px ${color}22`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = isPanelCard ? `${color}66` : '#334155';
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <div className="flex align-items-center gap-2">
          <div style={{
            width: '34px', height: '34px', borderRadius: '8px',
            background: `${color}22`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <i className={`pi ${icon}`} style={{ color, fontSize: '1rem' }} />
          </div>
          <div className="flex flex-column" style={{ flex: 1, minWidth: 0 }}>
            <span className="font-semibold" style={{ color: '#f1f5f9', fontSize: '0.85rem', lineHeight: '1.3' }}>
              {svc.type}
            </span>
            {subMeta && (
              <span style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '1px' }}>
                via {subMeta.parent}
              </span>
            )}
          </div>
        </div>
        <div className="flex align-items-center justify-content-between">
          <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
            {isPanelCard ? 'Sub-categories' : 'Resources'}
          </span>
          {isEc2Card ? (
            <span style={{
              background: `${color}22`, color,
              borderRadius: '20px', padding: '2px 8px',
              fontSize: '0.72rem', fontWeight: 600,
            }}>
              {EC2_CATEGORIES.length} groups
            </span>
          ) : isVpcCard ? (
            <span style={{
              background: `${color}22`, color,
              borderRadius: '20px', padding: '2px 8px',
              fontSize: '0.72rem', fontWeight: 600,
            }}>
              {VPC_CATEGORIES.length} groups
            </span>
          ) : (
            <span style={{
              background: `${color}22`, color,
              borderRadius: '20px', padding: '2px 8px',
              fontSize: '0.82rem', fontWeight: 700,
            }}>
              {svc.count}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-column gap-4">
      <Toast ref={toast} />

      {/* ── Summary header card ── */}
      {!searchLower && (
        <div style={{
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '16px',
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
        }}>
          <div className="flex align-items-center gap-3">
            <div style={{
              width: '44px', height: '44px', borderRadius: '12px',
              background: 'linear-gradient(135deg,#FF9900,#e07b00)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              boxShadow: '0 4px 16px #FF990044',
            }}>
              <i className="pi pi-server" style={{ color: '#fff', fontSize: '1.25rem' }} />
            </div>
            <div>
              <div className="font-bold" style={{ color: '#f1f5f9', fontSize: '1rem' }}>AWS Resources</div>
              <div className="text-sm" style={{ color: '#94a3b8' }}>
                <span style={{ background: '#FF990022', color: '#fb923c', borderRadius: '8px', padding: '1px 8px', fontFamily: 'monospace', fontWeight: 600, marginRight: '6px' }}>
                  {selectedRegion}
                </span>
                {topLevelSummary.reduce((acc, s) => acc + (s.count || 0), 0).toLocaleString()} total resources across {topLevelSummary.length} services
              </div>
            </div>
          </div>
          {/* Category quick stats */}
          <div className="flex gap-2 flex-wrap">
            {AWS_SERVICE_CATEGORIES.slice(0, 4).map((cat) => {
              const summaryMap = Object.fromEntries(topLevelSummary.map((s) => [s.type, s]));
              const count = cat.services.reduce((a, t) => a + (summaryMap[t]?.count || 0), 0);
              if (count === 0) return null;
              return (
                <div key={cat.name} style={{
                  background: '#0f172a', border: '1px solid #334155',
                  borderRadius: '10px', padding: '6px 12px',
                  display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                  <i className={`pi ${cat.icon}`} style={{ color: cat.color, fontSize: '0.8rem' }} />
                  <span style={{ color: cat.color, fontWeight: 700, fontSize: '0.85rem' }}>{count}</span>
                  <span style={{ color: '#64748b', fontSize: '0.72rem' }}>{cat.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex align-items-center justify-content-between flex-wrap gap-3">
        <div className="flex align-items-center gap-2">
          <i className="pi pi-th-large" style={{ color: '#818cf8', fontSize: '1.2rem' }} />
          <span className="text-lg font-semibold" style={{ color: '#f1f5f9' }}>
            AWS Services
          </span>
          <Badge value={filteredSummary.length} style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff' }} />
        </div>
        <div className="flex align-items-center gap-3 flex-wrap">
          <div className="flex align-items-center gap-2">
            <i className="pi pi-map-marker" style={{ color: '#94a3b8' }} />
            <Dropdown
              value={selectedRegion}
              options={AWS_REGIONS}
              onChange={(e) => setSelectedRegion(e.value)}
              placeholder="Select a region…"
              filter
              filterPlaceholder="Search regions…"
              style={{ minWidth: '260px' }}
            />
          </div>
          <span className="p-input-icon-left">
            <i className="pi pi-search" />
            <InputText
              value={serviceSearch}
              onChange={(e) => setServiceSearch(e.target.value)}
              placeholder="Search services…"
              style={{ borderRadius: '20px', minWidth: '220px' }}
            />
          </span>
        </div>
      </div>
      {!searchLower ? (
        // Categorized view
        <div className="flex flex-column gap-5">
          {(() => {
            const summaryMap = Object.fromEntries(topLevelSummary.map((s) => [s.type, s]));
            const categorized = new Set();
            return (
              <>
                {AWS_SERVICE_CATEGORIES.map((cat) => {
                  const catServices = cat.services
                    .map((t) => summaryMap[t])
                    .filter(Boolean);
                  if (catServices.length === 0) return null;
                  catServices.forEach((s) => categorized.add(s.type));
                  return (
                    <div key={cat.name}>
                      <div className="flex align-items-center gap-2 mb-3"
                        style={{ borderBottom: `2px solid ${cat.color}33`, paddingBottom: '0.5rem' }}>
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '6px',
                          background: `${cat.color}22`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                          <i className={`pi ${cat.icon}`} style={{ color: cat.color, fontSize: '0.9rem' }} />
                        </div>
                        <span className="font-semibold" style={{ color: '#cbd5e1', fontSize: '0.95rem' }}>
                          {cat.name}
                        </span>
                        <span style={{
                          background: `${cat.color}22`, color: cat.color,
                          borderRadius: '12px', padding: '1px 8px',
                          fontSize: '0.75rem', fontWeight: 600,
                        }}>
                          {catServices.length}
                        </span>
                      </div>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
                        gap: '0.75rem',
                      }}>
                        {catServices.map((svc) => renderServiceCard(svc, cat.color))}
                      </div>
                    </div>
                  );
                })}
                {(() => {
                  const uncategorized = topLevelSummary.filter((s) => !categorized.has(s.type));
                  if (uncategorized.length === 0) return null;
                  return (
                    <div key="other">
                      <div className="flex align-items-center gap-2 mb-3"
                        style={{ borderBottom: '2px solid #33415533', paddingBottom: '0.5rem' }}>
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '6px',
                          background: '#33415522',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                          <i className="pi pi-box" style={{ color: '#94a3b8', fontSize: '0.9rem' }} />
                        </div>
                        <span className="font-semibold" style={{ color: '#cbd5e1', fontSize: '0.95rem' }}>
                          Other Services
                        </span>
                      </div>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
                        gap: '0.75rem',
                      }}>
                        {uncategorized.map((svc) => renderServiceCard(svc))}
                      </div>
                    </div>
                  );
                })()}
              </>
            );
          })()}
        </div>
      ) : (
        // Search results: flat grid
        filteredSummary.length === 0 ? (
          <div className="flex flex-column align-items-center gap-2 py-6" style={{ color: '#94a3b8' }}>
            <i className="pi pi-search text-4xl" />
            <span>No services match "<strong>{serviceSearch}</strong>"</span>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
            gap: '0.75rem',
          }}>
            {filteredSummary.map((svc) => renderServiceCard(svc))}
          </div>
        )
      )}
    </div>
  );
}



function FilteredResourcesView({ provider }) {
  const toast = useRef(null);
  const [resources, setResources] = useState([]);
  const [resourceTypes, setResourceTypes] = useState([]);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [pendingTypes, setPendingTypes] = useState([]);
  const [pendingRegion, setPendingRegion] = useState('us-east-1');
  const [appliedRegion, setAppliedRegion] = useState(null);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [filtering, setFiltering] = useState(false);
  const [hasApplied, setHasApplied] = useState(false);
  const [error, setError] = useState(null);
  const [globalFilter, setGlobalFilter] = useState('');

  // On mount – only fetch the list of resource types, no resources yet
  useEffect(() => {
    getResourceTypes()
      .then((r) => {
        setResourceTypes(r.data.resource_types.map((t, i) => ({
          label: t,
          value: t,
          color: TYPE_COLORS[i % TYPE_COLORS.length],
          icon: TYPE_ICON[t] || 'pi-box',
        })));
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || 'Failed to load resource types');
      })
      .finally(() => setLoadingTypes(false));
  }, []);

  const handleApply = useCallback(async () => {
    if (!pendingTypes || pendingTypes.length === 0) return;
    setFiltering(true);
    setSelectedTypes(pendingTypes);
    setAppliedRegion(provider === 'aws' ? pendingRegion : null);
    setHasApplied(true);
    try {
      const res = await getResources(pendingTypes, provider === 'aws' ? pendingRegion : null);
      setResources(res.data.resources);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to load resources';
      setError(msg);
      toast.current?.show({
        severity: 'error',
        summary: 'Unable to retrieve resources',
        detail: msg,
        life: 15000,
        sticky: false,
      });
    } finally {
      setFiltering(false);
    }
  }, [pendingTypes, pendingRegion, provider]);

  const handleClear = useCallback(() => {
    setPendingTypes([]);
    setSelectedTypes([]);
    setPendingRegion('us-east-1');
    setAppliedRegion(null);
    setResources([]);
    setHasApplied(false);
    setGlobalFilter('');
  }, []);

  const typeOptionTemplate = (option) => (
    <div className="flex align-items-center gap-2">
      <i className={`pi ${option.icon}`} style={{ color: option.color }} />
      <span>{option.label}</span>
    </div>
  );

  if (loadingTypes) return (
    <div className="flex justify-content-center align-items-center flex-column gap-3" style={{ minHeight: '300px' }}>
      <ProgressSpinner style={{ width: '50px', height: '50px' }} strokeWidth="4" />
      <span className="text-sm" style={{ color: '#94a3b8' }}>Loading resource types…</span>
    </div>
  );

  if (error) return (
    <>
      <Toast ref={toast} />
      <Message severity="error" text={error} className="w-full" />
    </>
  );

  const header = (
    <div className="flex justify-content-between align-items-center flex-wrap gap-3"
         style={{ background: '#1e293b', padding: '0.75rem 1rem' }}>
      <span className="text-lg font-semibold flex align-items-center gap-2" style={{ color: '#f1f5f9' }}>
        <i className="pi pi-server" style={{ color: '#818cf8' }} />
        {selectedTypes.length === 1 ? `${selectedTypes[0]} ` : selectedTypes.length > 1 ? `${selectedTypes.length} Types ` : ''}Resources
        <Badge value={resources.length}
          style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff' }} />
      </span>
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search resources…"
          style={{ borderRadius: '20px' }}
        />
      </span>
    </div>
  );

  return (
    <div className="flex flex-column gap-4">
      <Toast ref={toast} />
      {/* Filter Panel */}
      <Card
        style={{
          borderRadius: '16px',
          background: '#1e293b',
          border: '1px solid #334155',
        }}
      >
        <div className="flex flex-column gap-3">
          <div className="flex align-items-center gap-2 mb-1">
            <i className="pi pi-filter" style={{ color: '#818cf8' }} />
            <span className="font-semibold" style={{ color: '#f1f5f9' }}>Select Resource Types</span>
          </div>
          <div className="flex flex-wrap align-items-end gap-3">
            {provider === 'aws' && (
              <div className="flex flex-column gap-1" style={{ minWidth: '220px' }}>
                <label className="text-sm" style={{ color: '#94a3b8' }}>Region</label>
                <Dropdown
                  value={pendingRegion}
                  options={AWS_REGIONS}
                  onChange={(e) => setPendingRegion(e.value)}
                  placeholder="Select a region…"
                  filter
                  filterPlaceholder="Search regions…"
                  style={{ borderRadius: '10px', minWidth: '260px' }}
                  panelStyle={{ borderRadius: '12px' }}
                />
              </div>
            )}
            <div className="flex flex-column gap-1 flex-1" style={{ minWidth: '220px' }}>
              <label className="text-sm" style={{ color: '#94a3b8' }}>
                Choose one or more resource types to view
              </label>
              <MultiSelect
                value={pendingTypes}
                options={resourceTypes}
                onChange={(e) => setPendingTypes(e.value)}
                itemTemplate={typeOptionTemplate}
                placeholder="Select resource types…"
                filter
                filterPlaceholder="Search types…"
                showClear
                display="chip"
                maxSelectedLabels={3}
                style={{ borderRadius: '10px', minWidth: '260px' }}
                panelStyle={{ borderRadius: '12px' }}
              />
            </div>
            <Button
              label="Apply"
              icon="pi pi-check"
              onClick={handleApply}
              loading={filtering}
              disabled={!pendingTypes || pendingTypes.length === 0}
              style={{
                borderRadius: '10px',
                background: pendingTypes && pendingTypes.length > 0
                  ? 'linear-gradient(135deg,#667eea,#764ba2)'
                  : '#334155',
                border: 'none',
                fontWeight: 600,
              }}
            />
            {hasApplied && (
              <Button
                label="Clear"
                icon="pi pi-times"
                className="p-button-outlined"
                onClick={handleClear}
                style={{ borderRadius: '10px', borderColor: '#475569', color: '#94a3b8' }}
              />
            )}
          </div>
          {hasApplied && selectedTypes.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedTypes.map((t) => (
                <div key={t} style={{
                  display: 'inline-flex', alignItems: 'center', gap: '6px',
                  padding: '4px 12px', borderRadius: '20px',
                  background: '#312e81', color: '#a5b4fc', fontSize: '0.8rem', fontWeight: 600,
                }}>
                  <i className="pi pi-filter" style={{ fontSize: '0.78rem' }} />
                  {t}
                </div>
              ))}
              {appliedRegion && (
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: '6px',
                  padding: '4px 12px', borderRadius: '20px',
                  background: '#1e3a5f', color: '#93c5fd', fontSize: '0.8rem', fontWeight: 600,
                }}>
                  <i className="pi pi-map-marker" style={{ fontSize: '0.78rem' }} />
                  {appliedRegion}
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Resources Table — only shown after Apply is clicked */}
      {!hasApplied ? (
        <div className="flex flex-column align-items-center justify-content-center gap-3 py-8"
             style={{
               background: '#1e293b', borderRadius: '16px', border: '1px solid #334155',
               minHeight: '280px',
             }}>
          <i className="pi pi-filter" style={{ fontSize: '3rem', color: '#4c1d95' }} />
          <span className="text-xl font-semibold" style={{ color: '#f1f5f9' }}>
            Select Resource Types
          </span>
          <span className="text-center" style={{ color: '#94a3b8', maxWidth: '340px' }}>
            {provider === 'aws'
              ? 'Choose a region and one or more resource types from above, then click '
              : 'Choose one or more resource types from above, then click '}
            <strong style={{ color: '#a5b4fc' }}>Apply</strong> to view resources.
          </span>
        </div>
      ) : filtering ? (
        <div className="flex justify-content-center align-items-center flex-column gap-2" style={{ minHeight: '200px' }}>
          <ProgressSpinner style={{ width: '36px', height: '36px' }} strokeWidth="4" />
          <span className="text-sm" style={{ color: '#94a3b8' }}>Loading resources…</span>
        </div>
      ) : (
        <DataTable
          value={resources}
          header={header}
          globalFilter={globalFilter}
          paginator
          rows={10}
          rowsPerPageOptions={[10, 25, 50]}
          sortMode="multiple"
          removableSort
          stripedRows
          emptyMessage={
            <div className="flex flex-column align-items-center gap-2 py-6" style={{ color: '#94a3b8' }}>
              <i className="pi pi-inbox text-4xl" />
              <span>{`No resources found for the selected type(s).`}</span>
            </div>
          }
          style={{ borderRadius: '16px', overflow: 'hidden' }}
        >
          <Column field="name" header="Name" sortable style={{ minWidth: '160px', fontWeight: 500 }} />
          <Column field="type" header="Type" body={typeTemplate} sortable style={{ minWidth: '150px' }} />
          <Column field="region" header="Region" sortable style={{ minWidth: '120px' }} />
          <Column field="status" header="Status" body={statusTemplate} sortable style={{ minWidth: '110px' }} />
          <Column field="tags" header="Tags" body={tagsTemplate} style={{ minWidth: '220px' }} />
        </DataTable>
      )}
    </div>
  );
}
