import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card } from 'primereact/card';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Calendar } from 'primereact/calendar';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { Divider } from 'primereact/divider';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Toast } from 'primereact/toast';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts';
import {
  getOverallBilling,
  getResourceTypes,
  getBillingByResourceType,
  getGcpBqProjects,
} from '../api/cloudApi';

function fmtCost(val, currency = 'USD') {
  return Number(val).toLocaleString('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// Use local date components to avoid UTC-shift bugs
function isoDate(d) {
  if (!d) return null;
  if (d instanceof Date) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
  return d;
}

function defaultRange() {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  return { start, end: today };
}

// Quick date preset ranges
const DATE_PRESETS = [
  {
    label: 'This Month',
    icon: 'pi-calendar',
    getRange: () => {
      const today = new Date();
      return { start: new Date(today.getFullYear(), today.getMonth(), 1), end: today };
    },
  },
  {
    label: 'Last Month',
    icon: 'pi-calendar-minus',
    getRange: () => {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const end = new Date(today.getFullYear(), today.getMonth(), 0);
      return { start, end };
    },
  },
  {
    label: 'Last 3 Months',
    icon: 'pi-history',
    getRange: () => {
      const today = new Date();
      return { start: new Date(today.getFullYear(), today.getMonth() - 2, 1), end: today };
    },
  },
  {
    label: 'Last 6 Months',
    icon: 'pi-history',
    getRange: () => {
      const today = new Date();
      return { start: new Date(today.getFullYear(), today.getMonth() - 5, 1), end: today };
    },
  },
  {
    label: 'This Year',
    icon: 'pi-calendar-plus',
    getRange: () => {
      const today = new Date();
      return { start: new Date(today.getFullYear(), 0, 1), end: today };
    },
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
  '#a18cd1', '#fda085', '#30cfd0', '#a1c4fd', '#ffecd2',
];

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
  { label: 'Asia Pacific (Tokyo) — ap-northeast-1', value: 'ap-northeast-1' },
  { label: 'Asia Pacific (Seoul) — ap-northeast-2', value: 'ap-northeast-2' },
  { label: 'Asia Pacific (Singapore) — ap-southeast-1', value: 'ap-southeast-1' },
  { label: 'Asia Pacific (Sydney) — ap-southeast-2', value: 'ap-southeast-2' },
  { label: 'Asia Pacific (Mumbai) — ap-south-1', value: 'ap-south-1' },
  { label: 'South America (São Paulo) — sa-east-1', value: 'sa-east-1' },
];

export default function BillingView({ provider }) {
  const toast = useRef(null);
  const { start: defStart, end: defEnd } = defaultRange();

  // Pending (user-selected but not yet applied) state
  const [pendingStart, setPendingStart] = useState(defStart);
  const [pendingEnd, setPendingEnd] = useState(defEnd);
  const [pendingTypes, setPendingTypes] = useState([]);
  const [pendingRegion, setPendingRegion] = useState('');
  const [pendingBqProject, setPendingBqProject] = useState(null);

  // Applied state used in API calls
  const [start, setStart] = useState(defStart);
  const [end, setEnd] = useState(defEnd);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [appliedRegion, setAppliedRegion] = useState(null);
  const [appliedBqProject, setAppliedBqProject] = useState(null);

  // Resource-type filter options
  const [resourceTypes, setResourceTypes] = useState([]);

  // GCP BigQuery project filter options (only populated when source === 'bigquery')
  const [bqProjects, setBqProjects] = useState([]);

  const [overall, setOverall] = useState(null);
  const [typesBilling, setTypesBilling] = useState([]);
  const [loadingOverall, setLoadingOverall] = useState(true);
  const [loadingType, setLoadingType] = useState(false);
  const [error, setError] = useState(null);

  const fetchOverall = useCallback(async (s, e, rgn, bqProj) => {
    setLoadingOverall(true);
    setError(null);
    try {
      const res = await getOverallBilling(isoDate(s), isoDate(e), rgn || null, bqProj || null);
      setOverall(res.data);
      if (res.data?.estimated) {
        toast.current?.show({
          severity: 'warn',
          summary: 'Estimated billing data',
          detail: res.data.note || 'Actual billing data is not available. The figures shown are estimates only.',
          life: 12000,
          sticky: false,
        });
      } else if (res.data?.bigquery_error) {
        toast.current?.show({
          severity: 'warn',
          summary: 'BigQuery query failed — showing estimated data',
          detail: res.data.bigquery_error,
          life: 10000,
          sticky: false,
        });
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load billing data');
    } finally {
      setLoadingOverall(false);
    }
  }, []);

  useEffect(() => {
    const { start: s, end: e } = defaultRange();
    fetchOverall(s, e, null, null);
    getResourceTypes()
      .then((r) => setResourceTypes(
        r.data.resource_types.map((t, i) => ({
          label: t, value: t,
          color: TYPE_COLORS[i % TYPE_COLORS.length],
          icon: TYPE_ICON[t] || 'pi-box',
        }))
      ))
      .catch(() => {});
    if (provider === 'gcp') {
      getGcpBqProjects()
        .then((r) => setBqProjects(r.data.projects || []))
        .catch(() => {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- intentional: run only on mount

  // Single Apply handler for date + resource type + region
  const handleApply = useCallback(() => {
    if (!pendingStart || !pendingEnd) {
      toast.current?.show({ severity: 'warn', summary: 'Incomplete range', detail: 'Please select both From and To dates.', life: 3000 });
      return;
    }
    if (pendingEnd < pendingStart) {
      toast.current?.show({ severity: 'warn', summary: 'Invalid range', detail: '"To" date must be on or after "From" date.', life: 3000 });
      return;
    }
    const rgn = provider === 'aws' ? (pendingRegion || null) : null;
    const bqProj = provider === 'gcp' ? (pendingBqProject || null) : null;
    setStart(pendingStart);
    setEnd(pendingEnd);
    setSelectedTypes(pendingTypes);
    setAppliedRegion(rgn);
    setAppliedBqProject(bqProj);
    fetchOverall(pendingStart, pendingEnd, rgn, bqProj);
    if (pendingTypes.length > 0) {
      setLoadingType(true);
      Promise.all(
        pendingTypes.map((type) =>
          getBillingByResourceType(type, isoDate(pendingStart), isoDate(pendingEnd), rgn, bqProj)
            .then((r) => r.data)
            .catch((err) => { console.error(`Failed to load billing for ${type}:`, err); return null; })
        )
      )
        .then((results) => {
          const valid = results.filter(Boolean);
          setTypesBilling(valid);
          valid.forEach((r) => {
            if (r?.estimated) {
              toast.current?.show({
                severity: 'warn',
                summary: `Estimated billing data for ${r.resource_type}`,
                detail: r.note || 'Actual billing data is not available. The figures shown are estimates only.',
                life: 12000,
                sticky: false,
              });
            } else if (r?.bigquery_error) {
              toast.current?.show({
                severity: 'warn',
                summary: `BigQuery query failed for ${r.resource_type} — showing estimated data`,
                detail: r.bigquery_error,
                life: 10000,
                sticky: false,
              });
            }
          });
        })
        .finally(() => setLoadingType(false));
    } else {
      setTypesBilling([]);
    }
  }, [pendingStart, pendingEnd, pendingTypes, pendingRegion, pendingBqProject, provider, fetchOverall]);

  const typeOptionTemplate = (option) => (
    <div className="flex align-items-center gap-2">
      <i className={`pi ${option.icon}`} style={{ color: option.color }} />
      <span>{option.label}</span>
    </div>
  );

  const selectedTypeTemplate = (option, props) => {
    if (option) {
      return (
        <div className="flex align-items-center gap-2">
          <i className={`pi ${option.icon}`} style={{ color: option.color }} />
          <span>{option.label}</span>
        </div>
      );
    }
    return <span style={{ color: '#94a3b8' }}>{props.placeholder}</span>;
  };

  return (
    <div className="flex flex-column gap-4">
      <Toast ref={toast} />

      {/* ── Estimated data banner — shown for Azure (no billing API available) ── */}
      {overall?.estimated && (
        <div style={{
          background: '#451a03',
          border: '1px solid #b45309',
          borderRadius: '12px',
          padding: '0.85rem 1.2rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
        }}>
          <i className="pi pi-exclamation-triangle" style={{ color: '#fbbf24', fontSize: '1.1rem', marginTop: '2px', flexShrink: 0 }} />
          <div>
            <span className="font-semibold" style={{ color: '#fde68a' }}>
              ⚠ Estimated data — not from your actual account
            </span>
            <div className="text-sm mt-1" style={{ color: '#fcd34d' }}>
              {overall.note || 'Actual billing data is not available. The figures shown are estimates only.'}
            </div>
          </div>
        </div>
      )}

      {/* ── BigQuery source banner — shown when real billing data was loaded ── */}
      {overall?.source === 'bigquery' && overall?.bigquery_project && (
        <div style={{
          background: '#0c2d48',
          border: '1px solid #1e6fa5',
          borderRadius: '12px',
          padding: '0.75rem 1.2rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <i className="pi pi-database" style={{ color: '#4facfe', fontSize: '1.1rem', flexShrink: 0 }} />
          <div className="text-sm" style={{ color: '#93c5fd' }}>
            Billing data loaded from BigQuery in project:{' '}
            <strong style={{ color: '#bfdbfe' }}>{overall.bigquery_project}</strong>
          </div>
        </div>
      )}

      {/* ── Filter Panel ─────────────────────────────────────────────── */}
      <Card
        style={{
          borderRadius: '16px',
          background: '#1e293b',
          border: '1px solid #334155',
        }}
      >
        {/* Quick date presets */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="text-xs font-semibold align-self-center" style={{ color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Quick Select:
          </span>
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              onClick={() => {
                const { start, end } = preset.getRange();
                setPendingStart(start);
                setPendingEnd(end);
              }}
              style={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '20px',
                color: '#94a3b8',
                fontSize: '0.78rem',
                fontWeight: 500,
                padding: '4px 12px',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'border-color 0.2s, color 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#818cf8';
                e.currentTarget.style.color = '#a5b4fc';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#334155';
                e.currentTarget.style.color = '#94a3b8';
              }}
            >
              <i className={`pi ${preset.icon}`} style={{ fontSize: '0.72rem' }} />
              {preset.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-4 align-items-end">
          {/* Date range */}
          <div className="flex flex-column gap-1">
            <label className="text-sm font-semibold mb-1" style={{ color: '#94a3b8' }}>
              <i className="pi pi-calendar mr-1" style={{ color: '#818cf8' }} />
              Date Range
            </label>
            <div className="flex align-items-center gap-2 flex-wrap">
              <div className="flex flex-column gap-1">
                <label className="text-xs" style={{ color: '#94a3b8' }}>From</label>
                <Calendar
                  value={pendingStart}
                  onChange={(e) => setPendingStart(e.value)}
                  readOnlyInput
                  showIcon
                  dateFormat="yy-mm-dd"
                  maxDate={pendingEnd || new Date()}
                  placeholder="Start date"
                  style={{ minWidth: '160px' }}
                  inputStyle={{ borderRadius: '10px' }}
                />
              </div>
              <div className="flex flex-column gap-1">
                <label className="text-xs" style={{ color: '#94a3b8' }}>To</label>
                <Calendar
                  value={pendingEnd}
                  onChange={(e) => setPendingEnd(e.value)}
                  readOnlyInput
                  showIcon
                  dateFormat="yy-mm-dd"
                  minDate={pendingStart}
                  maxDate={new Date()}
                  placeholder="End date"
                  style={{ minWidth: '160px' }}
                  inputStyle={{ borderRadius: '10px' }}
                />
              </div>
            </div>
          </div>

          <Divider layout="vertical" style={{ margin: '0 4px' }} />

          {/* Resource type */}
          <div className="flex flex-column gap-1">
            <label className="text-sm font-semibold mb-1" style={{ color: '#94a3b8' }}>
              <i className="pi pi-filter mr-1" style={{ color: '#818cf8' }} />
              Service Type
            </label>
            <div className="flex flex-column gap-1">
              <label className="text-xs" style={{ color: '#94a3b8' }}>Type</label>
              <MultiSelect
                value={pendingTypes}
                options={resourceTypes}
                onChange={(e) => setPendingTypes(e.value || [])}
                itemTemplate={typeOptionTemplate}
                placeholder="All service types"
                filter
                filterPlaceholder="Search types…"
                showClear
                onClear={() => setPendingTypes([])}
                display="chip"
                maxSelectedLabels={3}
                style={{ borderRadius: '10px', minWidth: '220px' }}
                panelStyle={{ borderRadius: '12px' }}
              />
            </div>
          </div>

          {/* Region (AWS only) */}
          {provider === 'aws' && (
            <>
              <Divider layout="vertical" style={{ margin: '0 4px' }} />
              <div className="flex flex-column gap-1">
                <label className="text-sm font-semibold mb-1" style={{ color: '#94a3b8' }}>
                  <i className="pi pi-map-marker mr-1" style={{ color: '#818cf8' }} />
                  Region
                </label>
                <div className="flex flex-column gap-1">
                  <label className="text-xs" style={{ color: '#94a3b8' }}>Region</label>
                  <Dropdown
                    value={pendingRegion}
                    options={[{ label: 'All Regions', value: '' }, ...AWS_REGIONS]}
                    onChange={(e) => setPendingRegion(e.value)}
                    placeholder="All Regions"
                    filter
                    filterPlaceholder="Search regions…"
                    style={{ borderRadius: '10px', minWidth: '240px' }}
                    panelStyle={{ borderRadius: '12px' }}
                  />
                </div>
              </div>
            </>
          )}

          {/* GCP BigQuery project filter (GCP + BigQuery only) */}
          {provider === 'gcp' && bqProjects.length > 0 && (
            <>
              <Divider layout="vertical" style={{ margin: '0 4px' }} />
              <div className="flex flex-column gap-1">
                <label className="text-sm font-semibold mb-1" style={{ color: '#94a3b8' }}>
                  <i className="pi pi-database mr-1" style={{ color: '#818cf8' }} />
                  GCP Project
                </label>
                <div className="flex flex-column gap-1">
                  <label className="text-xs" style={{ color: '#94a3b8' }}>Project</label>
                  <Dropdown
                    value={pendingBqProject}
                    options={[{ label: 'All Projects', value: null }, ...bqProjects.map((p) => ({ label: p, value: p }))]}
                    onChange={(e) => setPendingBqProject(e.value)}
                    placeholder="All Projects"
                    filter
                    filterPlaceholder="Search projects…"
                    showClear
                    onClear={() => setPendingBqProject(null)}
                    style={{ borderRadius: '10px', minWidth: '220px' }}
                    panelStyle={{ borderRadius: '12px' }}
                  />
                </div>
              </div>
            </>
          )}

          {/* Single Apply button */}
          <div className="flex align-items-end" style={{ paddingBottom: '2px' }}>
            <Button
              label="Apply"
              icon="pi pi-check"
              onClick={handleApply}
              loading={loadingOverall || loadingType}
              style={{
                borderRadius: '10px',
                background: 'linear-gradient(135deg,#667eea,#764ba2)',
                border: 'none',
                fontWeight: 600,
                whiteSpace: 'nowrap',
                marginTop: '1.5rem',
              }}
            />
          </div>
        </div>

        {/* Applied filter badges */}
        <div className="flex flex-wrap gap-2 mt-3">
          <span
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '4px 12px', borderRadius: '20px',
              background: '#312e81', color: '#a5b4fc', fontSize: '0.8rem', fontWeight: 600,
            }}
          >
            <i className="pi pi-calendar" style={{ fontSize: '0.78rem' }} />
            {isoDate(start)} → {isoDate(end)}
          </span>
          {selectedTypes.map((type) => (
            <span
              key={type}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '4px 12px', borderRadius: '20px',
                background: '#4a044e', color: '#f0abfc', fontSize: '0.8rem', fontWeight: 600,
              }}
            >
              <i className="pi pi-filter" style={{ fontSize: '0.78rem' }} />
              {type}
            </span>
          ))}
          {provider === 'aws' && (
            <span
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '4px 12px', borderRadius: '20px',
                background: '#1e3a5f', color: '#93c5fd', fontSize: '0.8rem', fontWeight: 600,
              }}
            >
              <i className="pi pi-map-marker" style={{ fontSize: '0.78rem' }} />
              {appliedRegion || 'All Regions'}
            </span>
          )}
          {appliedBqProject && (
            <span
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '4px 12px', borderRadius: '20px',
                background: '#0c2d48', color: '#93c5fd', fontSize: '0.8rem', fontWeight: 600,
              }}
            >
              <i className="pi pi-database" style={{ fontSize: '0.78rem' }} />
              {appliedBqProject}
            </span>
          )}
        </div>
      </Card>

      {/* ── Summary cards ────────────────────────────────────────────── */}
      {loadingOverall ? (
        <div className="flex justify-content-center flex-column align-items-center gap-2" style={{ minHeight: '120px' }}>
          <ProgressSpinner style={{ width: '40px', height: '40px' }} strokeWidth="4" />
          <span className="text-sm" style={{ color: '#94a3b8' }}>Loading billing data…</span>
        </div>
      ) : error ? (
        <Card style={{ borderRadius: '16px', background: '#1e293b', border: '1px solid #334155' }}>
          <div className="flex flex-column align-items-center justify-content-center gap-3"
               style={{ padding: '3rem', minHeight: '200px', textAlign: 'center' }}>
            <i className="pi pi-ban" style={{ fontSize: '3rem', color: '#475569' }} />
            <div className="text-xl font-semibold" style={{ color: '#94a3b8' }}>
              Billing Data Not Available
            </div>
            <div className="text-sm" style={{ color: '#64748b', maxWidth: '520px', lineHeight: '1.6' }}>
              {error}
            </div>
          </div>
        </Card>
      ) : overall && (
        <>
          <div className="grid">
            <div className="col-12 md:col-3">
              <Card className="text-center h-full"
                style={{ borderRadius: '16px', background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff', boxShadow: '0 8px 32px #667eea44' }}>
                <div className="text-lg font-semibold opacity-80 mb-1">Total Cost</div>
                <div className="text-4xl font-bold">{fmtCost(overall.total, overall.currency)}</div>
                <div className="text-sm opacity-70 mt-1">{overall.start_date} → {overall.end_date}</div>
              </Card>
            </div>
            <div className="col-12 md:col-3">
              <Card className="text-center h-full"
                style={{ borderRadius: '16px', background: 'linear-gradient(135deg,#f093fb,#f5576c)', color: '#fff', boxShadow: '0 8px 32px #f093fb44' }}>
                <div className="text-lg font-semibold opacity-80 mb-1">Daily Average</div>
                <div className="text-4xl font-bold">
                  {fmtCost(overall.daily_costs.length ? overall.total / overall.daily_costs.length : 0, overall.currency)}
                </div>
                <div className="text-sm opacity-70 mt-1">per day</div>
              </Card>
            </div>
            <div className="col-12 md:col-3">
              <Card className="text-center h-full"
                style={{ borderRadius: '16px', background: 'linear-gradient(135deg,#4facfe,#00f2fe)', color: '#fff', boxShadow: '0 8px 32px #4facfe44' }}>
                <div className="text-lg font-semibold opacity-80 mb-1">Top Service</div>
                <div className="text-2xl font-bold">{overall.breakdown[0]?.service || '—'}</div>
                <div className="text-sm opacity-70 mt-1">
                  {overall.breakdown[0] ? fmtCost(overall.breakdown[0].cost, overall.currency) : '—'}
                </div>
              </Card>
            </div>
            <div className="col-12 md:col-3">
              <Card className="text-center h-full"
                style={{ borderRadius: '16px', background: 'linear-gradient(135deg,#43e97b,#38f9d7)', color: '#fff', boxShadow: '0 8px 32px #43e97b44' }}>
                <div className="text-lg font-semibold opacity-80 mb-1">Total Services</div>
                <div className="text-4xl font-bold">{overall.breakdown.length}</div>
                <div className="text-sm opacity-70 mt-1">with active cost</div>
              </Card>
            </div>
          </div>

          {/* Daily cost chart – top-5 services as stacked colored bars */}
          <Card style={{ borderRadius: '16px', background: '#1e293b', border: '1px solid #334155' }}>
            <div className="font-semibold text-lg mb-3" style={{ color: '#f1f5f9' }}>
              <i className="pi pi-chart-bar mr-2" style={{ color: '#818cf8' }} />
              Daily Cost Trend
            </div>
            {(() => {
              const top5 = overall.breakdown.slice(0, 5);
              let chartData;
              if (overall.service_daily) {
                // Real BigQuery data: use actual per-service-per-day costs
                chartData = overall.daily_costs.map((day) => {
                  const entry = { date: day.date };
                  const daySvcs = overall.service_daily[day.date] || {};
                  top5.forEach((svc) => {
                    entry[svc.service] = +(daySvcs[svc.service] || 0).toFixed(2);
                  });
                  return entry;
                });
              } else {
                // Mock/estimated data: split daily total proportionally by service share
                const proportions = top5.map((svc) =>
                  overall.total > 0 ? svc.cost / overall.total : 0
                );
                chartData = overall.daily_costs.map((day) => {
                  const entry = { date: day.date };
                  top5.forEach((svc, i) => {
                    entry[svc.service] = +(day.cost * proportions[i]).toFixed(2);
                  });
                  return entry;
                });
              }
              return (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} interval="preserveStartEnd" />
                    <YAxis tickFormatter={(v) => fmtCost(v, overall.currency)} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                    <Tooltip
                      formatter={(v, name) => [fmtCost(v, overall.currency), name]}
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                    <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '12px' }} />
                    {top5.map((svc, idx) => (
                      <Bar
                        key={svc.service}
                        dataKey={svc.service}
                        stackId="total"
                        fill={TYPE_COLORS[idx % TYPE_COLORS.length]}
                        radius={idx === top5.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              );
            })()}
          </Card>
        </>
      )}

      {/* ── Resource-type specific billing ───────────────────────────── */}
      {selectedTypes.length > 0 && (
        <>
          <Divider />
          <div className="font-bold text-xl flex align-items-center gap-2 flex-wrap" style={{ color: '#f1f5f9' }}>
            <i className="pi pi-filter text-primary" />
            Billing for:
            {selectedTypes.map((type) => (
              <Badge key={type} value={type}
                style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff', fontSize: '0.9rem', padding: '6px 12px' }} />
            ))}
          </div>
          {loadingType ? (
            <div className="flex justify-content-center flex-column align-items-center gap-2" style={{ minHeight: '100px' }}>
              <ProgressSpinner style={{ width: '36px', height: '36px' }} strokeWidth="4" />
            </div>
          ) : typesBilling.length > 0 && (
            <div className="grid">
              {typesBilling.map((typeBilling) => (
                <React.Fragment key={typeBilling.resource_type}>
                  <div className="col-12 md:col-6">
                    <Card style={{ borderRadius: '16px', border: '2px solid #667eea', background: '#1e293b' }}>
                      <div className="flex justify-content-between align-items-center mb-3">
                        <span className="font-semibold text-lg" style={{ color: '#f1f5f9' }}>{typeBilling.resource_type} Total</span>
                        <span className="text-3xl font-bold" style={{ color: '#818cf8' }}>{fmtCost(typeBilling.total, typeBilling.currency)}</span>
                      </div>
                      <div className="text-sm" style={{ color: '#94a3b8' }}>
                        Average: {fmtCost(typeBilling.average_daily, typeBilling.currency)} / day &nbsp;|&nbsp;
                        {typeBilling.start_date} → {typeBilling.end_date}
                      </div>
                    </Card>
                  </div>
                  <div className="col-12">
                    <Card style={{ borderRadius: '16px', background: '#1e293b', border: '1px solid #334155' }}>
                      <div className="font-semibold mb-3" style={{ color: '#f1f5f9' }}>Daily Cost – {typeBilling.resource_type}</div>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={typeBilling.daily_costs} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} interval="preserveStartEnd" />
                          <YAxis tickFormatter={(v) => fmtCost(v, typeBilling.currency)} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                          <Tooltip
                            formatter={(v) => [fmtCost(v, typeBilling.currency), typeBilling.resource_type]}
                            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }}
                          />
                          <Legend wrapperStyle={{ color: '#94a3b8' }} />
                          <Bar dataKey="cost" name={typeBilling.resource_type} fill={`url(#typeGrad-${typeBilling.resource_type})`} radius={[6, 6, 0, 0]} />
                          <defs>
                            <linearGradient id={`typeGrad-${typeBilling.resource_type}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#f093fb" />
                              <stop offset="100%" stopColor="#f5576c" />
                            </linearGradient>
                          </defs>
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  </div>
                </React.Fragment>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── All services breakdown ────────────────────────────────────── */}
      {!loadingOverall && overall && overall.breakdown.length > 0 && (
        <>
          <Divider />
          <Card style={{ borderRadius: '16px', background: '#1e293b', border: '1px solid #334155' }}>
            <div className="font-semibold text-lg mb-4 flex align-items-center gap-2" style={{ color: '#f1f5f9' }}>
              <i className="pi pi-chart-pie" style={{ color: '#818cf8' }} />
              Cost Breakdown by Service
              <Badge value={overall.breakdown.length}
                style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff' }} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px,1fr) auto', gap: '2rem', alignItems: 'start' }}>
              {/* Left: progress bars */}
              <div className="flex flex-column gap-3">
                {overall.breakdown.map((item, idx) => {
                  const pct = overall.total > 0 ? (item.cost / overall.total) * 100 : 0;
                  const color = TYPE_COLORS[idx % TYPE_COLORS.length];
                  return (
                    <div key={item.service} className="flex align-items-center gap-3">
                      <div
                        style={{
                          width: '8px', height: '8px', borderRadius: '50%',
                          background: color, flexShrink: 0,
                        }}
                      />
                      <span className="font-medium flex-shrink-0 flex align-items-center gap-2"
                        style={{ color: '#e2e8f0', width: '10rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.85rem' }}>
                        <i className={`pi ${TYPE_ICON[item.service] || 'pi-box'}`} style={{ color }} />
                        {item.service}
                      </span>
                      <div className="flex-1" style={{ background: '#334155', borderRadius: '99px', height: '8px' }}>
                        <div style={{ width: `${pct}%`, background: `linear-gradient(90deg,${color},${color}aa)`, borderRadius: '99px', height: '100%', transition: 'width 0.5s ease' }} />
                      </div>
                      <span className="text-right font-semibold" style={{ color: '#f1f5f9', minWidth: '5rem', fontSize: '0.85rem' }}>{fmtCost(item.cost, overall.currency)}</span>
                      <span className="text-sm text-right" style={{ color: '#64748b', minWidth: '3rem' }}>{pct.toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
              {/* Right: donut chart */}
              <div style={{ width: '220px', flexShrink: 0 }}>
                <ResponsiveContainer width={220} height={220}>
                  <PieChart>
                    <Pie
                      data={overall.breakdown.slice(0, 10).map((item, idx) => ({
                        name: item.service,
                        value: item.cost,
                        color: TYPE_COLORS[idx % TYPE_COLORS.length],
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {overall.breakdown.slice(0, 10).map((_, idx) => (
                        <Cell key={idx} fill={TYPE_COLORS[idx % TYPE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v) => [fmtCost(v, overall.currency)]}
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="text-center mt-1">
                  <div style={{ color: '#64748b', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Top 10 Services</div>
                </div>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
