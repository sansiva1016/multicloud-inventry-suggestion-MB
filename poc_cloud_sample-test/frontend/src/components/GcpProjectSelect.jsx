import React, { useCallback, useEffect, useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { getGcpProjects, selectGcpProject } from '../api/cloudApi';

export default function GcpProjectSelect({ orgId = '', orgProjects = null, onSuccess, onBack }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(!orgProjects);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  // Manual entry fallback when auto-discovery returns nothing
  const [manualProjectId, setManualProjectId] = useState('');

  const fetchProjects = useCallback(() => {
    setLoading(true);
    setError(null);
    getGcpProjects(orgId)
      .then((res) => setProjects(res.data.projects || []))
      .catch(() => setError('Failed to load your GCP projects.'))
      .finally(() => setLoading(false));
  }, [orgId]);

  useEffect(() => {
    // If the parent already resolved projects for this org, use them directly.
    if (orgProjects) {
      setProjects(orgProjects);
      setLoading(false);
      return;
    }
    fetchProjects();
  }, [orgProjects, fetchProjects]);

  const handleProjectChange = (e) => {
    setSelected(e.value);
    setManualProjectId('');
  };

  const handleContinue = async () => {
    const projectId = selected ? selected.project_id : manualProjectId.trim();
    if (!projectId) return;
    setSubmitting(true);
    setError(null);
    try {
      await selectGcpProject(projectId);
      onSuccess('gcp', false);
    } catch {
      setError('Failed to select project. Please try again.');
      setSubmitting(false);
    }
  };

  const projectOptions = projects.map((p) => ({
    label: `${p.name} (${p.project_id})`,
    value: p,
  }));

  const canContinue = selected || manualProjectId.trim().length > 0;

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
            <i className="pi pi-list" style={{ color: '#fff', fontSize: '1.4rem' }} />
          </div>
          <h2 className="text-2xl font-bold m-0">Select a GCP Project</h2>
          <p className="text-500 mt-1 mb-0">
            Choose the project you want to manage.
          </p>
        </div>

        {error && <Message severity="error" text={error} className="w-full mb-3" />}

        {loading ? (
          <div className="flex justify-content-center py-4">
            <ProgressSpinner style={{ width: '40px', height: '40px' }} />
          </div>
        ) : projects.length > 0 ? (
          <div className="flex flex-column gap-3">
            <label className="font-semibold text-sm" htmlFor="gcp-project-dropdown">
              GCP Project
            </label>
            <Dropdown
              id="gcp-project-dropdown"
              value={selected}
              options={projectOptions}
              onChange={handleProjectChange}
              placeholder="Select a project..."
              className="w-full"
              disabled={submitting}
              filter
              filterPlaceholder="Search projects..."
            />
          </div>
        ) : (
          <div className="flex flex-column gap-3">
            <Message
              severity="warn"
              text="No projects were auto-discovered. Enter your Project ID manually or retry."
              className="w-full"
            />
            <Button
              label="Retry"
              icon="pi pi-refresh"
              className="p-button-outlined w-full"
              onClick={fetchProjects}
              disabled={submitting}
            />
            <div className="field">
              <label className="block font-semibold mb-1 text-sm" htmlFor="manual-project-id">
                Project ID
              </label>
              <InputText
                id="manual-project-id"
                value={manualProjectId}
                onChange={(e) => setManualProjectId(e.target.value)}
                placeholder="my-gcp-project-id"
                className="w-full"
                disabled={submitting}
              />
              <small className="text-400">
                Find it in the GCP Console under Project Info.
              </small>
            </div>
          </div>
        )}

        <div className="flex flex-column gap-2 mt-4">
          <Button
            label="Continue"
            icon="pi pi-arrow-right"
            iconPos="right"
            className="w-full"
            disabled={!canContinue || submitting}
            loading={submitting}
            onClick={handleContinue}
          />
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
