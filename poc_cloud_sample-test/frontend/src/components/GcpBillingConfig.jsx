import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { updateGcpBillingConfig } from '../api/cloudApi';

export default function GcpBillingConfig({ onSuccess, onBack, initialDataset = '', initialTable = '' }) {
  const [dataset, setDataset] = useState(initialDataset);
  const [table, setTable] = useState(initialTable);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async () => {
    setError(null);
    setLoading(true);
    try {
      await updateGcpBillingConfig(dataset.trim(), table.trim());
      onSuccess();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save billing configuration.');
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = async () => {
    setError(null);
    setLoading(true);
    try {
      await updateGcpBillingConfig('', '');
    } catch (err) {
      // Non-fatal: proceed anyway; billing config defaults to empty
      console.warn('Failed to clear billing config:', err?.response?.data?.detail || err?.message);
    } finally {
      setLoading(false);
      onSuccess();
    }
  };

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
            <i className="pi pi-database" style={{ color: '#fff', fontSize: '1.4rem' }} />
          </div>
          <h2 className="text-2xl font-bold m-0">Billing Configuration</h2>
          <p className="text-500 mt-1 mb-0">
            Enter your BigQuery billing export dataset and table to view real billing data.
          </p>
          <p className="text-xs text-400 mt-2 mb-0" style={{ lineHeight: 1.4 }}>
            You can skip this step and configure it later using the &ldquo;Change Billing&rdquo; button in the dashboard.
          </p>
        </div>

        {error && <Message severity="error" text={error} className="w-full mb-3" />}

        <div className="flex flex-column gap-3">
          <div className="field">
            <label className="block font-semibold mb-1 text-700">
              Billing Dataset
            </label>
            <InputText
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
              placeholder="my_billing_dataset"
              className="w-full"
              disabled={loading}
            />
          </div>
          <div className="field">
            <label className="block font-semibold mb-1 text-700">
              Billing Table
            </label>
            <InputText
              value={table}
              onChange={(e) => setTable(e.target.value)}
              placeholder="gcp_billing_export_v1_XXXXXX"
              className="w-full"
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button
            type="button"
            label="Back"
            icon="pi pi-arrow-left"
            className="p-button-outlined"
            style={{ flex: 1 }}
            onClick={onBack}
            disabled={loading}
          />
          <Button
            type="button"
            label="Skip"
            icon="pi pi-forward"
            className="p-button-secondary"
            style={{ flex: 1 }}
            onClick={handleSkip}
            disabled={loading}
          />
          <Button
            type="button"
            label="Save & Continue"
            icon="pi pi-check"
            style={{ flex: 1.5, background: '#4285F4', borderColor: '#4285F4' }}
            loading={loading}
            onClick={handleSave}
          />
        </div>

        {loading && (
          <div className="flex justify-content-center mt-3">
            <ProgressSpinner style={{ width: '30px', height: '30px' }} />
          </div>
        )}
      </Card>
    </div>
  );
}
