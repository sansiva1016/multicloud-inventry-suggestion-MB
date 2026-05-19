import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { validateCredentials, gcpOAuthInit } from '../api/cloudApi';

const PROVIDER_META = {
  aws: {
    name: 'Amazon Web Services',
    shortName: 'AWS',
    color: '#FF9900',
    fields: [
      { key: 'access_key_id', label: 'Access Key ID', type: 'text', required: true, placeholder: 'AKIAIOSFODNN7EXAMPLE' },
      { key: 'secret_access_key', label: 'Secret Access Key', type: 'password', required: true, placeholder: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' },
    ],
  },
  gcp: {
    name: 'Google Cloud Platform',
    shortName: 'GCP',
    color: '#4285F4',
    // GCP uses OAuth login – no credentials needed here; BigQuery config is set after project selection
    fields: [],
  },
  azure: {
    name: 'Microsoft Azure',
    shortName: 'Azure',
    color: '#0078D4',
    fields: [
      { key: 'subscription_id', label: 'Subscription ID', type: 'text', required: true, placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
      { key: 'tenant_id', label: 'Tenant ID', type: 'text', required: true, placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
      { key: 'client_secret', label: 'Client Secret', type: 'password', required: true, placeholder: 'your-client-secret' },
    ],
  },
};

export default function CredentialsForm({ provider, onSuccess, onBack }) {
  const meta = PROVIDER_META[provider];
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const handleChange = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  // GCP uses OAuth – redirect the browser to Google's consent screen
  const handleGcpOAuth = async () => {
    setError(null);
    setInfo(null);
    setLoading(true);
    try {
      const res = await gcpOAuthInit('', '', '', '');
      const { auth_url, error: apiError } = res.data;
      if (apiError) {
        setError(apiError);
        return;
      }
      // Redirect to Google's OAuth consent screen
      window.location.href = auth_url;
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to connect to backend. Is the server running?');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (provider === 'gcp') {
      return handleGcpOAuth();
    }
    setError(null);
    setInfo(null);
    setLoading(true);
    try {
      const res = await validateCredentials(provider, values);
      const data = res.data;
      if (data.valid) {
        if (data.mock) {
          setInfo(data.message);
          setTimeout(() => onSuccess(provider, data.mock), 1200);
        } else {
          onSuccess(provider, data.mock);
        }
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to connect to backend. Is the server running?');
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = async () => {
    setLoading(true);
    try {
      await validateCredentials(provider, {});
      onSuccess(provider, true);
    } catch {
      onSuccess(provider, true);
    } finally {
      setLoading(false);
    }
  };

  const isGcp = provider === 'gcp';

  return (
    <div className="flex flex-column align-items-center justify-content-center min-h-screen"
         style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}>
      <Card style={{ width: '500px', borderRadius: '16px', boxShadow: '0 4px 24px rgba(0,0,0,0.10)' }}>
        <div className="text-center mb-4">
          <div
            className="inline-flex align-items-center justify-content-center border-circle mb-3"
            style={{ width: '60px', height: '60px', background: meta.color }}>
            <span style={{ color: '#fff', fontWeight: 700 }}>{meta.shortName}</span>
          </div>
          <h2 className="text-2xl font-bold m-0">{meta.name}</h2>
          <p className="text-500 mt-1 mb-0">
            {isGcp
              ? 'Sign in with your Google account to access your GCP resources'
              : 'Enter your credentials or skip to use mock data'}
          </p>
          {isGcp && (
            <p className="text-xs text-400 mt-2 mb-0" style={{ lineHeight: 1.4 }}>
              OAuth credentials are pre-configured on the server. Click &quot;Login with Google&quot; to authenticate.
            </p>
          )}
        </div>

        {error && <Message severity="error" text={error} className="w-full mb-3" />}
        {info && <Message severity="info" text={info} className="w-full mb-3" />}

        <form onSubmit={handleSubmit}>
          {meta.fields.map((field) => (
            <div key={field.key} className="field mb-3">
              <label className="block font-semibold mb-1 text-700">
                {field.label}
                {field.required && <span style={{ color: '#e74c3c' }}> *</span>}
              </label>
              {field.type === 'textarea' ? (
                <InputTextarea
                  value={values[field.key] || ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  rows={4}
                  className="w-full"
                  style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}
                />
              ) : field.type === 'password' ? (
                <Password
                  value={values[field.key] || ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full"
                  inputClassName="w-full"
                  feedback={false}
                  toggleMask
                />
              ) : (
                <InputText
                  value={values[field.key] || ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full"
                />
              )}
            </div>
          ))}

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
              label="Use Mock Data"
              icon="pi pi-database"
              className="p-button-secondary"
              style={{ flex: 1 }}
              onClick={handleSkip}
              disabled={loading}
            />
            {isGcp ? (
              <Button
                type="submit"
                label="Login with Google"
                icon="pi pi-google"
                style={{ flex: 1.5, background: meta.color, borderColor: meta.color }}
                loading={loading}
                disabled={loading}
              />
            ) : (
              <Button
                type="submit"
                label="Connect"
                icon="pi pi-cloud"
                style={{ flex: 1, background: meta.color, borderColor: meta.color }}
                loading={loading}
                disabled={loading}
              />
            )}
          </div>
        </form>

        {loading && (
          <div className="flex justify-content-center mt-3">
            <ProgressSpinner style={{ width: '30px', height: '30px' }} />
          </div>
        )}
      </Card>
    </div>
  );
}
