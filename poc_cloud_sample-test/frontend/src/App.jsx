import React, { useState, useEffect } from 'react';
import { PrimeReactProvider } from 'primereact/api';
import CloudSelector from './components/CloudSelector';
import CredentialsForm from './components/CredentialsForm';
import GcpOrgSelect from './components/GcpOrgSelect';
import GcpProjectSelect from './components/GcpProjectSelect';
import GcpBillingConfig from './components/GcpBillingConfig';
import Dashboard from './components/Dashboard';
import { clearCredentials, getSession } from './api/cloudApi';

export default function App() {
  // steps: 'cloud-select' | 'credentials' | 'gcp-org-select' | 'gcp-project-select' | 'gcp-billing-config' | 'dashboard'
  const [step, setStep] = useState('cloud-select');
  const [provider, setProvider] = useState(null);
  const [isMock, setIsMock] = useState(true);
  const [hasGcpProjects, setHasGcpProjects] = useState(false);
  // Selected org state (org_id + pre-fetched projects for that org)
  const [gcpSelectedOrg, setGcpSelectedOrg] = useState('');
  const [gcpOrgProjects, setGcpOrgProjects] = useState(null);
  // Where the gcp-org-select step should navigate back to
  const [gcpOrgBackTo, setGcpOrgBackTo] = useState('cloud-select');
  // Where the gcp-project-select step should navigate back to
  const [gcpProjectBackTo, setGcpProjectBackTo] = useState('cloud-select');
  // Where the gcp-billing-config step should navigate back to
  const [gcpBillingBackTo, setGcpBillingBackTo] = useState('gcp-project-select');
  // Current BigQuery config for the "Change Billing" pre-fill
  const [gcpBillingDataset, setGcpBillingDataset] = useState('');
  const [gcpBillingTable, setGcpBillingTable] = useState('');

  // On mount: restore an active session (handles page refresh) and GCP OAuth redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gcpAuth = params.get('gcp_auth');

    if (gcpAuth) {
      // Remove the query param from the URL without triggering a reload
      window.history.replaceState({}, '', '/');

      if (gcpAuth === 'select_org') {
        // Organizations found – let user pick an org before choosing a project
        setProvider('gcp');
        setIsMock(false);
        setGcpOrgBackTo('cloud-select');
        setStep('gcp-org-select');
        return;
      }

      if (gcpAuth === 'select_project') {
        // No organisations but projects exist – go straight to project selection
        setProvider('gcp');
        setIsMock(false);
        setGcpProjectBackTo('cloud-select');
        setStep('gcp-project-select');
        return;
      }
      // For 'success' or 'error', fall through to session check below
    }

    // Restore session state on page refresh (or after OAuth success redirect)
    getSession()
      .then((res) => {
        const {
          active, provider: p, mock, project_id,
          has_gcp_projects, has_gcp_organizations,
          bigquery_dataset, bigquery_table,
        } = res.data;
        if (!active) return;
        setProvider(p);
        setIsMock(mock ?? false);
        if (p === 'gcp') {
          setHasGcpProjects(has_gcp_projects ?? false);
          setGcpBillingDataset(bigquery_dataset || '');
          setGcpBillingTable(bigquery_table || '');
          if (!mock && !project_id) {
            // Always require project selection for real (non-mock) GCP sessions,
            // regardless of whether projects were auto-discovered at login time.
            if (has_gcp_organizations) {
              setGcpOrgBackTo('cloud-select');
              setStep('gcp-org-select');
              return;
            }
            setGcpProjectBackTo('cloud-select');
            setStep('gcp-project-select');
            return;
          }
        }
        setStep('dashboard');
      })
      .catch(() => {});
  }, []);

  const handleCloudSelect = (p) => {
    setProvider(p);
    setStep('credentials');
  };

  const handleCredentialsSuccess = (p, mock) => {
    setProvider(p);
    setIsMock(mock);
    setStep('dashboard');
  };

  // User picked an organization → go to project selection for that org
  const handleGcpOrgSuccess = (orgId, orgProjects) => {
    setGcpSelectedOrg(orgId);
    setGcpOrgProjects(orgProjects);
    setGcpProjectBackTo('gcp-org-select');
    setStep('gcp-project-select');
  };

  // User skipped org selection → show all projects
  const handleGcpOrgSkip = () => {
    setGcpSelectedOrg('');
    setGcpOrgProjects(null);
    setGcpProjectBackTo('gcp-org-select');
    setStep('gcp-project-select');
  };

  const handleChangeProject = () => {
    setGcpProjectBackTo('dashboard');
    setStep('gcp-project-select');
  };

  const handleGcpProjectSuccess = (p, mock) => {
    setHasGcpProjects(true);
    setProvider(p);
    setIsMock(mock);
    // After selecting a project, go to billing config
    setGcpBillingBackTo('gcp-project-select');
    setStep('gcp-billing-config');
  };

  const handleGcpBillingSuccess = () => {
    setStep('dashboard');
  };

  const handleChangeBilling = () => {
    setGcpBillingBackTo('dashboard');
    setStep('gcp-billing-config');
  };

  const handleLogout = async () => {
    try { await clearCredentials(); } catch { /* ignore */ }
    setProvider(null);
    setIsMock(true);
    setHasGcpProjects(false);
    setGcpSelectedOrg('');
    setGcpOrgProjects(null);
    setGcpOrgBackTo('cloud-select');
    setGcpProjectBackTo('cloud-select');
    setGcpBillingDataset('');
    setGcpBillingTable('');
    setStep('cloud-select');
  };

  return (
    <PrimeReactProvider>
      {step === 'cloud-select' && (
        <CloudSelector onSelect={handleCloudSelect} />
      )}
      {step === 'credentials' && provider && (
        <CredentialsForm
          provider={provider}
          onSuccess={handleCredentialsSuccess}
          onBack={() => setStep('cloud-select')}
        />
      )}
      {step === 'gcp-org-select' && (
        <GcpOrgSelect
          onSuccess={handleGcpOrgSuccess}
          onSkip={handleGcpOrgSkip}
          onBack={() => setStep(gcpOrgBackTo)}
        />
      )}
      {step === 'gcp-project-select' && (
        <GcpProjectSelect
          orgId={gcpSelectedOrg}
          orgProjects={gcpOrgProjects}
          onSuccess={handleGcpProjectSuccess}
          onBack={() => setStep(gcpProjectBackTo)}
        />
      )}
      {step === 'gcp-billing-config' && (
        <GcpBillingConfig
          initialDataset={gcpBillingDataset}
          initialTable={gcpBillingTable}
          onSuccess={handleGcpBillingSuccess}
          onBack={() => setStep(gcpBillingBackTo)}
        />
      )}
      {step === 'dashboard' && provider && (
        <Dashboard
          provider={provider}
          isMock={isMock}
          onLogout={handleLogout}
          onChangeProject={hasGcpProjects ? handleChangeProject : null}
          onChangeBilling={provider === 'gcp' ? handleChangeBilling : null}
        />
      )}
    </PrimeReactProvider>
  );
}
