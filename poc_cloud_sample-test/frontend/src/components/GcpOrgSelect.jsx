import React, { useEffect, useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { getGcpOrganizations, selectGcpOrg } from '../api/cloudApi';

export default function GcpOrgSelect({ onSuccess, onSkip, onBack }) {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getGcpOrganizations()
      .then((res) => setOrganizations(res.data.organizations || []))
      .catch(() => setError('Failed to load your GCP organizations.'))
      .finally(() => setLoading(false));
  }, []);

  const handleContinue = async () => {
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await selectGcpOrg(selected.org_id);
      const projects = res.data.projects || [];
      onSuccess(selected.org_id, projects);
    } catch {
      setError('Failed to select organization. Please try again.');
      setSubmitting(false);
    }
  };

  const orgOptions = organizations.map((o) => ({
    label: o.name,
    value: o,
  }));

  return (
    <div
      className="flex flex-column align-items-center justify-content-center min-h-screen"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}
    >
      <Card style={{ width: '520px', borderRadius: '16px', boxShadow: '0 4px 24px rgba(0,0,0,0.10)' }}>
        <div className="text-center mb-4">
          <div
            className="inline-flex align-items-center justify-content-center border-circle mb-3"
            style={{ width: '60px', height: '60px', background: '#4285F4' }}
          >
            <i className="pi pi-building" style={{ color: '#fff', fontSize: '1.4rem' }} />
          </div>
          <h2 className="text-2xl font-bold m-0">Select an Organization</h2>
          <p className="text-500 mt-1 mb-0">
            Choose the GCP organization to browse its projects.
          </p>
        </div>

        {error && <Message severity="error" text={error} className="w-full mb-3" />}

        {loading ? (
          <div className="flex justify-content-center py-4">
            <ProgressSpinner style={{ width: '40px', height: '40px' }} />
          </div>
        ) : organizations.length === 0 ? (
          <div className="flex flex-column gap-3">
            <Message
              severity="info"
              text="No organizations found. You can still select a project directly."
              className="w-full"
            />
            <Button
              label="Select a Project"
              icon="pi pi-arrow-right"
              iconPos="right"
              className="w-full"
              onClick={onSkip}
            />
          </div>
        ) : (
          <div className="flex flex-column gap-3">
            <label className="font-semibold text-sm" htmlFor="gcp-org-dropdown">
              GCP Organization
            </label>
            <Dropdown
              id="gcp-org-dropdown"
              value={selected}
              options={orgOptions}
              onChange={(e) => setSelected(e.value)}
              placeholder="Select an organization..."
              className="w-full"
              disabled={submitting}
              filter
              filterPlaceholder="Search organizations..."
            />
            <Button
              label="Continue"
              icon="pi pi-arrow-right"
              iconPos="right"
              className="w-full"
              disabled={!selected || submitting}
              loading={submitting}
              onClick={handleContinue}
            />
            <Button
              label="Skip – show all projects"
              icon="pi pi-list"
              className="p-button-outlined w-full"
              onClick={onSkip}
              disabled={submitting}
            />
          </div>
        )}

        <div className="mt-3">
          <Button
            label="Back"
            icon="pi pi-arrow-left"
            className="p-button-outlined w-full"
            onClick={onBack}
            disabled={submitting}
          />
        </div>
      </Card>
    </div>
  );
}
