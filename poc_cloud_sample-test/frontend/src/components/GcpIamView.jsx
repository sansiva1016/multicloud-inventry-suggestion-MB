import React, { useEffect, useState } from 'react';
import { Card } from 'primereact/card';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { getGcpIamRoles } from '../api/cloudApi';

// Friendly descriptions for common GCP predefined roles
const ROLE_DESCRIPTIONS = {
  'roles/owner': 'Full access to all resources',
  'roles/editor': 'Edit access to all resources',
  'roles/viewer': 'Read-only access to all resources',
  'roles/cloudasset.viewer': 'View Cloud Asset Inventory',
  'roles/billing.viewer': 'View billing information',
  'roles/billing.admin': 'Full billing access',
  'roles/compute.admin': 'Full Compute Engine access',
  'roles/compute.viewer': 'Read-only Compute Engine access',
  'roles/storage.admin': 'Full Cloud Storage access',
  'roles/storage.objectViewer': 'Read Cloud Storage objects',
  'roles/bigquery.admin': 'Full BigQuery access',
  'roles/bigquery.dataViewer': 'View BigQuery datasets',
  'roles/container.admin': 'Full GKE access',
  'roles/iam.securityReviewer': 'View IAM policies',
  'roles/resourcemanager.projectViewer': 'View project resources',
  'roles/resourcemanager.projectEditor': 'Edit project resources',
  'roles/resourcemanager.projectOwner': 'Owner of the project',
};

function roleDescription(role) {
  return ROLE_DESCRIPTIONS[role] || role.replace('roles/', '').replace(/\./g, ' › ');
}

// Derive principal type label and icon from the member prefix
function principalType(member) {
  if (member.startsWith('user:')) return { label: 'user', icon: 'pi-user' };
  if (member.startsWith('serviceAccount:')) return { label: 'serviceAccount', icon: 'pi-cog' };
  if (member.startsWith('group:')) return { label: 'group', icon: 'pi-users' };
  if (member.startsWith('domain:')) return { label: 'domain', icon: 'pi-globe' };
  return { label: 'principal', icon: 'pi-id-card' };
}

// Strip the type prefix (e.g. "user:", "serviceAccount:") from a principal identifier
function stripPrincipalPrefix(member) {
  const colonIdx = member.indexOf(':');
  return colonIdx !== -1 ? member.slice(colonIdx + 1) : member;
}

// Build a sorted principal → roles[] map from all_bindings (role → members[])
function buildPrincipalRows(allBindings) {
  const map = {};
  allBindings.forEach(({ role, members = [] }) => {
    members.forEach((member) => {
      if (!map[member]) map[member] = [];
      map[member].push(role);
    });
  });
  return Object.keys(map)
    .sort((a, b) => a.localeCompare(b))
    .map((member) => ({
      id: member,
      principal: member,
      roles: map[member].sort((a, b) => a.localeCompare(b)),
      roleCount: map[member].length,
      type: principalType(member),
    }));
}

function RolesCell({ roles }) {
  if (!roles || roles.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {roles.map((role) => (
        <span
          key={role}
          title={roleDescription(role)}
          className="text-xs px-2 py-1"
          style={{ background: '#1e3a5f', borderRadius: '12px', color: '#93c5fd', fontFamily: 'monospace' }}
        >
          {role.replace('roles/', '')}
        </span>
      ))}
    </div>
  );
}

export default function GcpIamView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getGcpIamRoles()
      .then((res) => setData(res.data))
      .catch((err) => setError(err?.response?.data?.detail || 'Failed to load IAM data.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-content-center align-items-center" style={{ minHeight: '200px' }}>
        <ProgressSpinner style={{ width: '40px', height: '40px' }} />
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

  const { email, project_id, user_roles = [], all_bindings = [] } = data || {};

  // Build principal-first rows sorted alphabetically by principal
  const principalRows = buildPrincipalRows(all_bindings);

  return (
    <div className="mt-3">
      {/* Identity card */}
      <Card
        className="mb-4"
        style={{ background: '#1e293b', border: '1px solid #334155' }}
      >
        <div className="flex align-items-center gap-3 flex-wrap">
          <div
            className="flex align-items-center justify-content-center border-circle"
            style={{ width: '48px', height: '48px', background: '#4285F4', flexShrink: 0 }}
          >
            <i className="pi pi-user" style={{ color: '#fff', fontSize: '1.2rem' }} />
          </div>
          <div>
            <div className="font-bold text-lg" style={{ color: '#f1f5f9' }}>
              {email || 'Service Account / Unknown Identity'}
            </div>
            <div className="text-sm" style={{ color: '#94a3b8' }}>
              Project: <span style={{ color: '#60a5fa' }}>{project_id}</span>
            </div>
          </div>
        </div>

        {user_roles.length > 0 && (
          <div className="mt-3">
            <div className="font-semibold mb-2" style={{ color: '#cbd5e1' }}>
              Your Roles ({user_roles.length})
            </div>
            <div className="flex flex-wrap gap-2">
              {user_roles.map((role) => (
                <Tag
                  key={role}
                  value={role.replace('roles/', '')}
                  severity="info"
                  style={{ background: '#1d4ed8', borderRadius: '8px', fontSize: '0.8rem' }}
                  title={roleDescription(role)}
                />
              ))}
            </div>
          </div>
        )}

        {user_roles.length === 0 && email && (
          <Message
            severity="warn"
            text="No IAM roles found for your account in this project."
            className="w-full mt-3"
          />
        )}
      </Card>

      {/* Project IAM policy sorted by Principal */}
      <Card
        style={{ background: '#1e293b', border: '1px solid #334155' }}
      >
        <div className="font-bold text-lg mb-3" style={{ color: '#f1f5f9' }}>
          Project IAM Policy ({principalRows.length} principals)
        </div>
        <DataTable
          value={principalRows}
          paginator
          rows={15}
          rowsPerPageOptions={[15, 30, 50]}
          emptyMessage="No IAM bindings found."
          style={{ background: '#1e293b' }}
          className="p-datatable-sm"
          stripedRows
          sortField="principal"
          sortOrder={1}
        >
          <Column
            field="principal"
            header="Principal"
            sortable
            style={{ minWidth: '260px' }}
            body={(row) => (
              <div className="flex align-items-center gap-2">
                <i
                  className={`pi ${row.type.icon}`}
                  style={{ color: '#60a5fa', fontSize: '0.95rem', flexShrink: 0 }}
                />
                <div>
                  <div className="font-medium" style={{ color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.85rem', wordBreak: 'break-all' }}>
                    {stripPrincipalPrefix(row.principal)}
                  </div>
                  <div className="text-xs" style={{ color: '#64748b' }}>
                    {row.type.label}
                  </div>
                </div>
              </div>
            )}
          />
          <Column
            field="roleCount"
            header="Roles"
            sortable
            style={{ width: '80px', textAlign: 'center' }}
            body={(row) => (
              <Tag value={row.roleCount} severity="secondary" />
            )}
          />
          <Column
            field="roles"
            header="Roles & Permissions"
            style={{ minWidth: '320px' }}
            body={(row) => <RolesCell roles={row.roles} />}
          />
        </DataTable>
      </Card>
    </div>
  );
}
