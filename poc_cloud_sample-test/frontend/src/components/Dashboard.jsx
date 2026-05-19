import React from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import ResourcesView from './ResourcesView';
import BillingView from './BillingView';
import GcpIamView from './GcpIamView';
import GcpSuggestionsView from './GcpSuggestionsView';
import AwsIamView from './AwsIamView';
import AwsSuggestionsView from './AwsSuggestionsView';

const PROVIDER_META = {
  aws: { name: 'Amazon Web Services', shortName: 'AWS', color: '#FF9900' },
  gcp: { name: 'Google Cloud Platform', shortName: 'GCP', color: '#4285F4' },
  azure: { name: 'Microsoft Azure', shortName: 'Azure', color: '#0078D4' },
};

export default function Dashboard({ provider, isMock, onLogout, onChangeProject, onChangeBilling }) {
  const meta = PROVIDER_META[provider] || { name: provider, shortName: provider, color: '#555' };

  return (
    <div className="flex flex-column" style={{ minHeight: '100vh', background: '#0f172a' }}>
      {/* Header */}
      <div
        className="flex align-items-center justify-content-between px-5 py-3"
        style={{
          background: '#1e293b',
          borderBottom: '1px solid #334155',
          boxShadow: '0 1px 8px rgba(0,0,0,0.4)',
        }}
      >
        <div className="flex align-items-center gap-3">
          <div
            className="flex align-items-center justify-content-center border-circle"
            style={{ width: '40px', height: '40px', background: meta.color }}
          >
            <span style={{ color: '#fff', fontWeight: 700, fontSize: '0.8rem' }}>{meta.shortName}</span>
          </div>
          <div>
            <div className="font-bold text-xl" style={{ color: '#f1f5f9' }}>Cloud Management Console</div>
            <div className="text-sm" style={{ color: '#94a3b8' }}>{meta.name}</div>
          </div>
          {isMock && (
            <Tag
              value="Mock Data"
              severity="warning"
              icon="pi pi-database"
              style={{ marginLeft: '8px' }}
            />
          )}
        </div>
        <div className="flex align-items-center gap-2">
          {onChangeProject && (
            <Button
              label="Change Project"
              icon="pi pi-arrow-left"
              className="p-button-outlined p-button-sm"
              onClick={onChangeProject}
            />
          )}
          {onChangeBilling && (
            <Button
              label="Change Billing"
              icon="pi pi-database"
              className="p-button-outlined p-button-sm"
              onClick={onChangeBilling}
            />
          )}
          <Button
            label="Change Cloud"
            icon="pi pi-sign-out"
            className="p-button-outlined p-button-sm"
            onClick={onLogout}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4" style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <TabView>
          <TabPanel
            header={
              <span>
                <i className="pi pi-server mr-2" />
                Resources
              </span>
            }
          >
            <ResourcesView provider={provider} />
          </TabPanel>
          <TabPanel
            header={
              <span>
                <i className="pi pi-dollar mr-2" />
                Billing
              </span>
            }
          >
            <BillingView provider={provider} />
          </TabPanel>
          {provider === 'gcp' && (
            <TabPanel
              header={
                <span>
                  <i className="pi pi-shield mr-2" />
                  IAM &amp; Permissions
                </span>
              }
            >
              <GcpIamView />
            </TabPanel>
          )}
          {provider === 'gcp' && (
            <TabPanel
              header={
                <span>
                  <i className="pi pi-lightbulb mr-2" />
                  Suggestions
                </span>
              }
            >
              <GcpSuggestionsView />
            </TabPanel>
          )}
          {provider === 'aws' && (
            <TabPanel
              header={
                <span>
                  <i className="pi pi-shield mr-2" />
                  IAM &amp; Permissions
                </span>
              }
            >
              <AwsIamView />
            </TabPanel>
          )}
          {provider === 'aws' && (
            <TabPanel
              header={
                <span>
                  <i className="pi pi-lightbulb mr-2" />
                  Suggestions
                </span>
              }
            >
              <AwsSuggestionsView />
            </TabPanel>
          )}
        </TabView>
      </div>
    </div>
  );
}
