import React, { useEffect, useState } from 'react';
import { Card } from 'primereact/card';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { TabView, TabPanel } from 'primereact/tabview';
import { InputText } from 'primereact/inputtext';
import { Tooltip } from 'primereact/tooltip';
import { getAwsIamRoles } from '../api/cloudApi';

// Friendly descriptions for common AWS managed policies
const POLICY_DESCRIPTIONS = {
  AdministratorAccess: 'Full access to all AWS services and resources',
  PowerUserAccess: 'Full access except IAM user and group management',
  ReadOnlyAccess: 'Read-only access to all AWS services',
  SecurityAudit: 'Read-only access for security auditing',
  AmazonS3FullAccess: 'Full access to S3',
  AmazonS3ReadOnlyAccess: 'Read-only access to S3',
  AWSLambdaFullAccess: 'Full access to Lambda',
  AWSLambdaBasicExecutionRole: 'Write logs to CloudWatch',
  AmazonEC2FullAccess: 'Full access to EC2',
  AmazonEC2ReadOnlyAccess: 'Read-only access to EC2',
  AmazonRDSFullAccess: 'Full access to RDS',
  AmazonDynamoDBFullAccess: 'Full access to DynamoDB',
  AmazonDynamoDBReadOnlyAccess: 'Read-only access to DynamoDB',
  AmazonECRFullAccess: 'Full access to ECR',
  AWSCodeDeployFullAccess: 'Full access to CodeDeploy',
  AmazonAthenaFullAccess: 'Full access to Athena',
  AmazonSQSFullAccess: 'Full access to SQS',
};

const ADMIN_POLICIES = new Set(['AdministratorAccess', 'PowerUserAccess']);

function policyDescription(policy) {
  return POLICY_DESCRIPTIONS[policy] || policy;
}

function PoliciesCell({ policies }) {
  if (!policies || policies.length === 0) return <span style={{ color: '#64748b' }}>—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {policies.map((policy) => {
        const isAdmin = ADMIN_POLICIES.has(policy);
        return (
          <span
            key={policy}
            data-pr-tooltip={policyDescription(policy)}
            data-pr-position="top"
            className={`iam-policy-tag text-xs px-2 py-1`}
            style={{
              background: isAdmin ? '#450a0a' : '#1e3a5f',
              borderRadius: '12px',
              color: isAdmin ? '#fca5a5' : '#93c5fd',
              fontFamily: 'monospace',
              border: isAdmin ? '1px solid #991b1b' : 'none',
              cursor: 'default',
              whiteSpace: 'nowrap',
            }}
          >
            {isAdmin && <i className="pi pi-exclamation-triangle mr-1" style={{ fontSize: '0.7rem' }} />}
            {policy}
          </span>
        );
      })}
    </div>
  );
}

function GroupsCell({ groups }) {
  if (!groups || groups.length === 0) return <span style={{ color: '#64748b' }}>—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {groups.map((g) => (
        <span
          key={g}
          className="text-xs px-2 py-1"
          style={{
            background: '#1e3a5f',
            borderRadius: '12px',
            color: '#93c5fd',
            fontFamily: 'monospace',
          }}
        >
          {g}
        </span>
      ))}
    </div>
  );
}

function SearchableTableHeader({ title, icon, iconColor, count, globalFilter, onFilterChange }) {
  return (
    <div
      className="flex align-items-center justify-content-between flex-wrap gap-3"
      style={{ padding: '0.5rem 0 0.75rem 0' }}
    >
      <span className="font-bold text-lg flex align-items-center gap-2" style={{ color: '#f1f5f9' }}>
        <i className={`pi ${icon}`} style={{ color: iconColor }} />
        {title}
        <span
          style={{
            background: `${iconColor}22`,
            color: iconColor,
            borderRadius: '20px',
            padding: '1px 10px',
            fontSize: '0.82rem',
            fontWeight: 700,
          }}
        >
          {count}
        </span>
      </span>
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilter}
          onChange={(e) => onFilterChange(e.target.value)}
          placeholder={`Search ${title.toLowerCase()}…`}
          style={{ borderRadius: '20px', minWidth: '200px' }}
        />
      </span>
    </div>
  );
}

function Dash() {
  return <span style={{ color: '#475569' }}>—</span>;
}

function EmptyState({ icon, message }) {
  return (
    <div className="flex flex-column align-items-center gap-2 py-6" style={{ color: '#94a3b8' }}>
      <i className={`pi ${icon}`} style={{ fontSize: '2.5rem', color: '#334155' }} />
      <span className="text-sm">{message}</span>
    </div>
  );
}

export default function AwsIamView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userFilter, setUserFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [policyFilter, setPolicyFilter] = useState('');

  useEffect(() => {
    getAwsIamRoles()
      .then((res) => setData(res.data))
      .catch((err) => setError(err?.response?.data?.detail || 'Failed to load IAM data.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-content-center align-items-center flex-column gap-3" style={{ minHeight: '260px' }}>
        <ProgressSpinner style={{ width: '44px', height: '44px' }} strokeWidth="4" />
        <span className="text-sm" style={{ color: '#94a3b8' }}>Loading IAM data…</span>
      </div>
    );
  }

  if (error || data?.error) {
    return (
      <Message
        severity="error"
        text={error || data.error}
        className="w-full mt-3"
      />
    );
  }

  const { account_id, users = [], roles = [], groups = [], policies = [] } = data || {};

  const noMfaUsers = users.filter((u) => !u.mfa_enabled);
  const adminUsers = users.filter((u) =>
    (u.policies || []).some((p) => ADMIN_POLICIES.has(p))
  );
  const customerPolicies = policies.filter((p) => p.type === 'Customer managed');
  const unusedPolicies = policies.filter((p) => p.attachment_count === 0);

  const statCards = [
    { label: 'Users', count: users.length, icon: 'pi-user', color: '#60a5fa', gradient: 'linear-gradient(135deg,#1d4ed8,#2563eb)' },
    { label: 'Roles', count: roles.length, icon: 'pi-cog', color: '#a78bfa', gradient: 'linear-gradient(135deg,#6d28d9,#7c3aed)' },
    { label: 'Groups', count: groups.length, icon: 'pi-users', color: '#34d399', gradient: 'linear-gradient(135deg,#065f46,#059669)' },
    { label: 'Policies', count: policies.length, icon: 'pi-file', color: '#fb923c', gradient: 'linear-gradient(135deg,#92400e,#b45309)' },
  ];

  const securityAlerts = [
    noMfaUsers.length > 0 && {
      severity: 'danger',
      icon: 'pi-lock-open',
      color: '#f87171',
      bg: '#450a0a',
      border: '#991b1b',
      text: `${noMfaUsers.length} user${noMfaUsers.length > 1 ? 's have' : ' has'} MFA disabled`,
      sub: noMfaUsers.map((u) => u.name).join(', '),
    },
    adminUsers.length > 0 && {
      severity: 'warning',
      icon: 'pi-exclamation-triangle',
      color: '#fbbf24',
      bg: '#451a03',
      border: '#b45309',
      text: `${adminUsers.length} user${adminUsers.length > 1 ? 's have' : ' has'} admin-level access`,
      sub: adminUsers.map((u) => u.name).join(', '),
    },
    unusedPolicies.length > 0 && {
      severity: 'info',
      icon: 'pi-info-circle',
      color: '#60a5fa',
      bg: '#0c2d48',
      border: '#1e6fa5',
      text: `${unusedPolicies.length} polic${unusedPolicies.length > 1 ? 'ies are' : 'y is'} not attached to any entity`,
      sub: null,
    },
  ].filter(Boolean);

  return (
    <div className="flex flex-column gap-4 mt-3">
      <Tooltip target=".iam-policy-tag" />

      {/* ── Account summary ── */}
      <Card style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '16px' }}>
        <div className="flex align-items-center gap-3 flex-wrap">
          <div
            style={{
              width: '52px', height: '52px', borderRadius: '14px',
              background: 'linear-gradient(135deg,#FF9900,#e07b00)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              boxShadow: '0 4px 16px #FF990044',
            }}
          >
            <i className="pi pi-shield" style={{ color: '#fff', fontSize: '1.4rem' }} />
          </div>
          <div>
            <div className="font-bold text-xl" style={{ color: '#f1f5f9' }}>AWS IAM &amp; Permissions</div>
            <div className="text-sm mt-1" style={{ color: '#94a3b8' }}>
              Account ID:&nbsp;
              <span
                style={{
                  background: '#FF990022', color: '#fb923c',
                  borderRadius: '8px', padding: '1px 8px',
                  fontFamily: 'monospace', fontWeight: 600,
                }}
              >
                {account_id}
              </span>
            </div>
          </div>
          {/* Stat pills */}
          <div className="flex gap-3 ml-auto flex-wrap">
            {statCards.map(({ label, count, icon, color, gradient }) => (
              <div
                key={label}
                style={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  padding: '12px 18px',
                  textAlign: 'center',
                  minWidth: '88px',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    position: 'absolute', top: 0, left: 0, right: 0,
                    height: '3px', background: gradient,
                  }}
                />
                <i className={`pi ${icon}`} style={{ color, fontSize: '1.15rem' }} />
                <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '1.5rem', lineHeight: 1.1, marginTop: '4px' }}>{count}</div>
                <div style={{ color: '#64748b', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ── Security insights ── */}
      {securityAlerts.length > 0 && (
        <div className="flex flex-column gap-2">
          {securityAlerts.map((alert, i) => (
            <div
              key={i}
              style={{
                background: alert.bg,
                border: `1px solid ${alert.border}`,
                borderRadius: '12px',
                padding: '0.75rem 1.1rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.75rem',
              }}
            >
              <i className={`pi ${alert.icon}`} style={{ color: alert.color, fontSize: '1rem', marginTop: '2px', flexShrink: 0 }} />
              <div>
                <span className="font-semibold text-sm" style={{ color: alert.color }}>{alert.text}</span>
                {alert.sub && (
                  <div className="text-xs mt-1" style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{alert.sub}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Tabbed sections ── */}
      <Card style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '16px' }}>
        <TabView>
          {/* Users tab */}
          <TabPanel
            header={
              <span className="flex align-items-center gap-2">
                <i className="pi pi-user" style={{ color: '#60a5fa' }} />
                Users
                <span style={{ background: '#1d4ed822', color: '#60a5fa', borderRadius: '10px', padding: '0 7px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {users.length}
                </span>
              </span>
            }
          >
            <DataTable
              value={users}
              paginator
              rows={15}
              rowsPerPageOptions={[15, 30, 50]}
              globalFilter={userFilter}
              globalFilterFields={['name', 'groups', 'policies', 'password_last_used']}
              header={
                <SearchableTableHeader
                  title="Users"
                  icon="pi-user"
                  iconColor="#60a5fa"
                  count={users.length}
                  globalFilter={userFilter}
                  onFilterChange={setUserFilter}
                />
              }
              emptyMessage={<EmptyState icon="pi-user" message="No IAM users found." />}
              className="p-datatable-sm"
              stripedRows
              sortField="name"
              sortOrder={1}
            >
              <Column
                field="name"
                header="Username"
                sortable
                style={{ minWidth: '160px' }}
                body={(row) => (
                  <div className="flex align-items-center gap-2">
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '50%',
                      background: '#1d4ed822',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <i className="pi pi-user" style={{ color: '#60a5fa', fontSize: '0.8rem' }} />
                    </div>
                    <span style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {row.name}
                    </span>
                  </div>
                )}
              />
              <Column
                field="mfa_enabled"
                header="MFA"
                sortable
                style={{ width: '110px' }}
                body={(row) => (
                  row.mfa_enabled
                    ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#06402122', color: '#34d399', borderRadius: '8px', padding: '2px 10px', fontSize: '0.78rem', fontWeight: 600 }}>
                        <i className="pi pi-check-circle" style={{ fontSize: '0.78rem' }} />
                        Enabled
                      </span>
                    )
                    : (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#450a0a', color: '#f87171', borderRadius: '8px', padding: '2px 10px', fontSize: '0.78rem', fontWeight: 600, border: '1px solid #991b1b' }}>
                        <i className="pi pi-times-circle" style={{ fontSize: '0.78rem' }} />
                        Disabled
                      </span>
                    )
                )}
              />
              <Column
                field="groups"
                header="Groups"
                style={{ minWidth: '180px' }}
                body={(row) => <GroupsCell groups={row.groups} />}
              />
              <Column
                field="policies"
                header="Policies"
                style={{ minWidth: '280px' }}
                body={(row) => <PoliciesCell policies={row.policies} />}
              />
              <Column
                field="password_last_used"
                header="Last Active"
                sortable
                style={{ width: '140px' }}
                body={(row) => (
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {row.password_last_used
                      ? <span>{String(row.password_last_used).split('T')[0]}</span>
                      : <span style={{ color: '#475569' }}>Never</span>}
                  </span>
                )}
              />
            </DataTable>
          </TabPanel>

          {/* Roles tab */}
          <TabPanel
            header={
              <span className="flex align-items-center gap-2">
                <i className="pi pi-cog" style={{ color: '#a78bfa' }} />
                Roles
                <span style={{ background: '#6d28d922', color: '#a78bfa', borderRadius: '10px', padding: '0 7px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {roles.length}
                </span>
              </span>
            }
          >
            <DataTable
              value={roles}
              paginator
              rows={15}
              rowsPerPageOptions={[15, 30, 50]}
              globalFilter={roleFilter}
              globalFilterFields={['name', 'description', 'policies']}
              header={
                <SearchableTableHeader
                  title="Roles"
                  icon="pi-cog"
                  iconColor="#a78bfa"
                  count={roles.length}
                  globalFilter={roleFilter}
                  onFilterChange={setRoleFilter}
                />
              }
              emptyMessage={<EmptyState icon="pi-cog" message="No IAM roles found." />}
              className="p-datatable-sm"
              stripedRows
              sortField="name"
              sortOrder={1}
            >
              <Column
                field="name"
                header="Role Name"
                sortable
                style={{ minWidth: '180px' }}
                body={(row) => (
                  <div className="flex align-items-center gap-2">
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '8px',
                      background: '#6d28d922',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <i className="pi pi-cog" style={{ color: '#a78bfa', fontSize: '0.8rem' }} />
                    </div>
                    <span style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {row.name}
                    </span>
                  </div>
                )}
              />
              <Column
                field="description"
                header="Description"
                style={{ minWidth: '200px' }}
                body={(row) => (
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {row.description || <Dash />}
                  </span>
                )}
              />
              <Column
                field="policies"
                header="Attached Policies"
                style={{ minWidth: '280px' }}
                body={(row) => <PoliciesCell policies={row.policies} />}
              />
            </DataTable>
          </TabPanel>

          {/* Groups tab */}
          <TabPanel
            header={
              <span className="flex align-items-center gap-2">
                <i className="pi pi-users" style={{ color: '#34d399' }} />
                Groups
                <span style={{ background: '#06402122', color: '#34d399', borderRadius: '10px', padding: '0 7px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {groups.length}
                </span>
              </span>
            }
          >
            <DataTable
              value={groups}
              paginator
              rows={15}
              rowsPerPageOptions={[15, 30, 50]}
              globalFilter={groupFilter}
              globalFilterFields={['name', 'policies']}
              header={
                <SearchableTableHeader
                  title="Groups"
                  icon="pi-users"
                  iconColor="#34d399"
                  count={groups.length}
                  globalFilter={groupFilter}
                  onFilterChange={setGroupFilter}
                />
              }
              emptyMessage={<EmptyState icon="pi-users" message="No IAM groups found." />}
              className="p-datatable-sm"
              stripedRows
              sortField="name"
              sortOrder={1}
            >
              <Column
                field="name"
                header="Group Name"
                sortable
                style={{ minWidth: '180px' }}
                body={(row) => (
                  <div className="flex align-items-center gap-2">
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '8px',
                      background: '#06402122',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <i className="pi pi-users" style={{ color: '#34d399', fontSize: '0.8rem' }} />
                    </div>
                    <span style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {row.name}
                    </span>
                  </div>
                )}
              />
              <Column
                field="member_count"
                header="Members"
                sortable
                style={{ width: '110px' }}
                body={(row) => (
                  <span style={{
                    background: '#06402122', color: '#34d399',
                    borderRadius: '20px', padding: '2px 12px',
                    fontSize: '0.82rem', fontWeight: 700,
                    display: 'inline-flex', alignItems: 'center', gap: '4px',
                  }}>
                    <i className="pi pi-user" style={{ fontSize: '0.72rem' }} />
                    {row.member_count}
                  </span>
                )}
              />
              <Column
                field="policies"
                header="Attached Policies"
                style={{ minWidth: '280px' }}
                body={(row) => <PoliciesCell policies={row.policies} />}
              />
            </DataTable>
          </TabPanel>

          {/* Policies tab */}
          <TabPanel
            header={
              <span className="flex align-items-center gap-2">
                <i className="pi pi-file" style={{ color: '#fb923c' }} />
                Policies
                <span style={{ background: '#92400e22', color: '#fb923c', borderRadius: '10px', padding: '0 7px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {policies.length}
                </span>
              </span>
            }
          >
            {/* Policy type quick stats */}
            <div className="flex gap-3 flex-wrap mb-3">
              {[
                { label: 'AWS Managed', count: policies.length - customerPolicies.length, color: '#818cf8' },
                { label: 'Customer Managed', count: customerPolicies.length, color: '#fb923c' },
                { label: 'Unused', count: unusedPolicies.length, color: '#94a3b8' },
              ].map(({ label, count, color }) => (
                <div key={label} style={{
                  background: '#0f172a', border: '1px solid #334155',
                  borderRadius: '10px', padding: '8px 16px',
                  display: 'flex', alignItems: 'center', gap: '8px',
                }}>
                  <span style={{ color, fontWeight: 700, fontSize: '1.1rem' }}>{count}</span>
                  <span style={{ color: '#64748b', fontSize: '0.8rem' }}>{label}</span>
                </div>
              ))}
            </div>
            <DataTable
              value={policies}
              paginator
              rows={15}
              rowsPerPageOptions={[15, 30, 50]}
              globalFilter={policyFilter}
              globalFilterFields={['name', 'type', 'description']}
              header={
                <SearchableTableHeader
                  title="Policies"
                  icon="pi-file"
                  iconColor="#fb923c"
                  count={policies.length}
                  globalFilter={policyFilter}
                  onFilterChange={setPolicyFilter}
                />
              }
              emptyMessage={<EmptyState icon="pi-file" message="No IAM policies found." />}
              className="p-datatable-sm"
              stripedRows
              sortField="name"
              sortOrder={1}
            >
              <Column
                field="name"
                header="Policy Name"
                sortable
                style={{ minWidth: '200px' }}
                body={(row) => (
                  <div className="flex align-items-center gap-2">
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '8px',
                      background: '#92400e22',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                      <i className="pi pi-file" style={{ color: '#fb923c', fontSize: '0.8rem' }} />
                    </div>
                    <span style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {row.name}
                    </span>
                  </div>
                )}
              />
              <Column
                field="type"
                header="Type"
                sortable
                style={{ width: '170px' }}
                body={(row) => (
                  <span style={{
                    background: row.type === 'Customer managed' ? '#818cf822' : '#33415522',
                    color: row.type === 'Customer managed' ? '#818cf8' : '#94a3b8',
                    borderRadius: '8px', padding: '3px 10px',
                    fontSize: '0.78rem', fontWeight: 600,
                    display: 'inline-flex', alignItems: 'center', gap: '4px',
                  }}>
                    <i className={`pi ${row.type === 'Customer managed' ? 'pi-user' : 'pi-amazon'}`} style={{ fontSize: '0.72rem' }} />
                    {row.type}
                  </span>
                )}
              />
              <Column
                field="attachment_count"
                header="Attachments"
                sortable
                style={{ width: '120px' }}
                body={(row) => (
                  <span style={{
                    background: row.attachment_count > 0 ? '#06402122' : '#33415522',
                    color: row.attachment_count > 0 ? '#34d399' : '#94a3b8',
                    borderRadius: '20px', padding: '2px 10px',
                    fontSize: '0.82rem', fontWeight: 700,
                  }}>
                    {row.attachment_count}
                  </span>
                )}
              />
              <Column
                field="description"
                header="Description"
                style={{ minWidth: '220px' }}
                body={(row) => (
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {row.description || <Dash />}
                  </span>
                )}
              />
              <Column
                field="default_version_id"
                header="Version"
                style={{ width: '90px' }}
                body={(row) => (
                  <span style={{ color: '#64748b', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                    {row.default_version_id || '—'}
                  </span>
                )}
              />
              <Column
                field="update_date"
                header="Last Updated"
                sortable
                style={{ width: '140px' }}
                body={(row) => (
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {row.update_date ? String(row.update_date).split('T')[0] : '—'}
                  </span>
                )}
              />
            </DataTable>
          </TabPanel>
        </TabView>
      </Card>
    </div>
  );
}
