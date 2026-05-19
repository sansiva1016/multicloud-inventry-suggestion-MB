import React, { useEffect, useState, useCallback } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Button } from 'primereact/button';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { SelectButton } from 'primereact/selectbutton';
import { getGcpSuggestions } from '../api/cloudApi';

// ─── Severity helpers ────────────────────────────────────────────────────────

const SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 };

const severityTag = (sev) => {
  const map = {
    critical: { severity: 'danger', icon: 'pi pi-times-circle', label: 'Critical' },
    warning:  { severity: 'warning', icon: 'pi pi-exclamation-triangle', label: 'Warning' },
    info:     { severity: 'info', icon: 'pi pi-info-circle', label: 'Info' },
  };
  const cfg = map[sev] || map.info;
  return <Tag value={cfg.label} severity={cfg.severity} icon={cfg.icon} />;
};

const typeTag = (type) => {
  const map = {
    overused:          { label: 'Over-used',   color: '#ef4444' },
    underused:         { label: 'Under-used',  color: '#f59e0b' },
    security:          { label: 'Security',    color: '#8b5cf6' },
    cost_optimization: { label: 'Cost',        color: '#10b981' },
  };
  const cfg = map[type] || { label: type, color: '#64748b' };
  return (
    <span
      style={{
        background: cfg.color + '22',
        color: cfg.color,
        border: `1px solid ${cfg.color}55`,
        borderRadius: '12px',
        padding: '2px 10px',
        fontSize: '0.75rem',
        fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      {cfg.label}
    </span>
  );
};

// ─── Summary card ────────────────────────────────────────────────────────────

function SummaryCard({ icon, label, counts, iconColor }) {
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '10px',
        padding: '16px 20px',
        flex: '1 1 200px',
        minWidth: '160px',
      }}
    >
      <div className="flex align-items-center gap-2 mb-2">
        <i className={`${icon} text-xl`} style={{ color: iconColor }} />
        <span style={{ color: '#94a3b8', fontWeight: 600, fontSize: '0.85rem' }}>{label}</span>
      </div>
      <div style={{ color: '#f1f5f9', fontSize: '1.5rem', fontWeight: 700 }}>{counts.total}</div>
      <div className="flex gap-2 mt-1" style={{ fontSize: '0.75rem' }}>
        {counts.critical > 0 && (
          <span style={{ color: '#ef4444' }}>● {counts.critical} critical</span>
        )}
        {counts.warning > 0 && (
          <span style={{ color: '#f59e0b' }}>● {counts.warning} warning</span>
        )}
        {counts.info > 0 && (
          <span style={{ color: '#60a5fa' }}>● {counts.info} info</span>
        )}
        {counts.total === 0 && <span style={{ color: '#22c55e' }}>✓ No issues</span>}
      </div>
    </div>
  );
}

// ─── Expandable row detail ────────────────────────────────────────────────────

function RowDetail({ data }) {
  return (
    <div
      style={{
        background: '#0f172a',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '16px 20px',
        margin: '4px 0',
      }}
    >
      <div className="grid" style={{ gap: '16px' }}>
        <div style={{ flex: '1 1 300px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginBottom: '4px' }}>
            CURRENT VALUE
          </div>
          <code
            style={{
              color: '#f59e0b',
              background: '#1e293b',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              display: 'block',
              wordBreak: 'break-all',
            }}
          >
            {data.current_value || '—'}
          </code>
        </div>
        <div style={{ flex: '2 1 400px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginBottom: '4px' }}>
            RECOMMENDATION
          </div>
          <div style={{ color: '#e2e8f0', fontSize: '0.85rem', lineHeight: 1.6 }}>
            {data.recommendation}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

const CATEGORY_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Resources', value: 'resources' },
  { label: 'Billing', value: 'billing' },
  { label: 'IAM', value: 'iam' },
];

const SEVERITY_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Critical', value: 'critical' },
  { label: 'Warning', value: 'warning' },
  { label: 'Info', value: 'info' },
];

export default function GcpSuggestionsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getGcpSuggestions();
      setData(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load suggestions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Apply filters
  const suggestions = (data?.suggestions || [])
    .filter((s) => categoryFilter === 'all' || s.category === categoryFilter)
    .filter((s) => severityFilter === 'all' || s.severity === severityFilter)
    .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2));

  const summary = data?.summary || {
    resources: { total: 0, critical: 0, warning: 0, info: 0 },
    billing:   { total: 0, critical: 0, warning: 0, info: 0 },
    iam:       { total: 0, critical: 0, warning: 0, info: 0 },
  };

  const dataErrors = [
    data?.resources_error && { label: 'Resources', msg: data.resources_error },
    data?.billing_error   && { label: 'Billing',   msg: data.billing_error },
    data?.iam_error       && { label: 'IAM',        msg: data.iam_error },
  ].filter(Boolean);

  return (
    <div style={{ color: '#e2e8f0' }}>
      {/* Header row */}
      <div className="flex align-items-center justify-content-between mb-4" style={{ flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div className="text-xl font-bold" style={{ color: '#f1f5f9' }}>
            <i className="pi pi-lightbulb mr-2" style={{ color: '#f59e0b' }} />
            Resource Optimization Suggestions
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
            Analyses your GCP resources, billing, and IAM policy to detect over-used or
            under-used configurations and security risks.
          </div>
        </div>
        <Button
          label="Refresh"
          icon="pi pi-refresh"
          className="p-button-outlined p-button-sm"
          onClick={load}
          loading={loading}
        />
      </div>

      {/* Data-source error banners */}
      {dataErrors.map(({ label, msg }) => (
        <Message
          key={label}
          severity="warn"
          text={`${label}: ${msg}`}
          style={{ marginBottom: '8px', width: '100%', justifyContent: 'flex-start' }}
        />
      ))}

      {loading && !data && (
        <div className="flex justify-content-center align-items-center py-6">
          <ProgressSpinner style={{ width: '48px', height: '48px' }} />
          <span style={{ marginLeft: '12px', color: '#94a3b8' }}>
            Analysing resources, billing, and IAM…
          </span>
        </div>
      )}

      {error && (
        <Message severity="error" text={error} style={{ width: '100%', justifyContent: 'flex-start' }} />
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div className="flex gap-3 mb-4" style={{ flexWrap: 'wrap' }}>
            <SummaryCard
              icon="pi pi-server"
              label="Resources"
              counts={summary.resources}
              iconColor="#60a5fa"
            />
            <SummaryCard
              icon="pi pi-dollar"
              label="Billing"
              counts={summary.billing}
              iconColor="#34d399"
            />
            <SummaryCard
              icon="pi pi-shield"
              label="IAM"
              counts={summary.iam}
              iconColor="#a78bfa"
            />
            <div
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '10px',
                padding: '16px 20px',
                flex: '1 1 160px',
                minWidth: '160px',
              }}
            >
              <div className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-list text-xl" style={{ color: '#f59e0b' }} />
                <span style={{ color: '#94a3b8', fontWeight: 600, fontSize: '0.85rem' }}>Total</span>
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '1.5rem', fontWeight: 700 }}>
                {(data.suggestions || []).length}
              </div>
              <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '4px' }}>
                suggestions
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-3 align-items-center" style={{ flexWrap: 'wrap' }}>
            <div className="flex align-items-center gap-2">
              <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Category:</span>
              <SelectButton
                value={categoryFilter}
                options={CATEGORY_OPTIONS}
                onChange={(e) => setCategoryFilter(e.value || 'all')}
                style={{ fontSize: '0.8rem' }}
              />
            </div>
            <div className="flex align-items-center gap-2">
              <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Severity:</span>
              <SelectButton
                value={severityFilter}
                options={SEVERITY_OPTIONS}
                onChange={(e) => setSeverityFilter(e.value || 'all')}
                style={{ fontSize: '0.8rem' }}
              />
            </div>
          </div>

          {/* Suggestions table */}
          {suggestions.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '48px',
                color: '#94a3b8',
                background: '#1e293b',
                borderRadius: '10px',
                border: '1px solid #334155',
              }}
            >
              <i className="pi pi-check-circle text-5xl mb-3" style={{ color: '#22c55e', display: 'block' }} />
              <div className="text-lg font-bold" style={{ color: '#f1f5f9' }}>
                No suggestions found
              </div>
              <div style={{ marginTop: '8px', fontSize: '0.85rem' }}>
                {(data.suggestions || []).length === 0
                  ? 'Your GCP configuration looks well-optimised!'
                  : 'No results match the selected filters.'}
              </div>
            </div>
          ) : (
            <DataTable
              value={suggestions}
              expandedRows={expandedRows}
              onRowToggle={(e) => setExpandedRows(e.data)}
              rowExpansionTemplate={(rowData) => <RowDetail data={rowData} />}
              dataKey="id"
              paginator
              rows={20}
              rowsPerPageOptions={[10, 20, 50]}
              emptyMessage="No suggestions found."
              style={{ fontSize: '0.85rem' }}
              tableStyle={{ minWidth: '700px' }}
            >
              <Column expander style={{ width: '3rem' }} />
              <Column
                field="severity"
                header="Severity"
                style={{ width: '100px' }}
                body={(row) => severityTag(row.severity)}
                sortable
              />
              <Column
                field="type"
                header="Type"
                style={{ width: '110px' }}
                body={(row) => typeTag(row.type)}
              />
              <Column
                field="category"
                header="Category"
                style={{ width: '100px', textTransform: 'capitalize' }}
                body={(row) => (
                  <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
                    {row.category}
                  </span>
                )}
                sortable
              />
              <Column field="resource_type" header="Service" style={{ width: '130px' }} sortable />
              <Column field="resource_name" header="Resource" sortable />
              <Column
                field="title"
                header="Finding"
                style={{ minWidth: '260px' }}
                body={(row) => (
                  <div>
                    <div style={{ fontWeight: 600, color: '#e2e8f0' }}>{row.title}</div>
                    <div style={{ color: '#94a3b8', fontSize: '0.78rem', marginTop: '2px', lineHeight: 1.4 }}>
                      {row.description}
                    </div>
                  </div>
                )}
              />
            </DataTable>
          )}
        </>
      )}
    </div>
  );
}
