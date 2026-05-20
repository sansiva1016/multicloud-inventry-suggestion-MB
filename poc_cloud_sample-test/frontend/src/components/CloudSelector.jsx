import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';

const PROVIDERS = [
  {
    id: 'aws',
    name: 'Amazon Web Services',
    shortName: 'AWS',
    color: '#FF9900',
    bg: '#1e1a0d',
    borderColor: '#FF9900',
    description: 'Compute, storage, databases, AI/ML and 200+ services',
    icon: '🟠',
  },
  {
    id: 'gcp',
    name: 'Google Cloud Platform',
    shortName: 'GCP',
    color: '#4285F4',
    bg: '#0d1929',
    borderColor: '#4285F4',
    description: 'Data analytics, machine learning, and cloud infrastructure',
    icon: '🔵',
  },
  {
    id: 'azure',
    name: 'Microsoft Azure',
    shortName: 'Azure',
    color: '#0078D4',
    bg: '#0d1829',
    borderColor: '#0078D4',
    description: 'Hybrid cloud, enterprise applications, and AI services',
    icon: '🔷',
  },
];

export default function CloudSelector({ onSelect }) {
  return (
    <div className="flex flex-column align-items-center justify-content-center min-h-screen"
         style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}>
      <div className="text-center mb-5">
        <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>☁️</div>
        <h1 className="text-4xl font-bold m-0" style={{ color: '#f1f5f9' }}>
          Cloud Management Console
        </h1>
        <p className="text-xl mt-2" style={{ color: '#94a3b8' }}>Select your cloud provider to get started</p>
      </div>

      <div className="flex flex-wrap gap-4 justify-content-center" style={{ maxWidth: '900px' }}>
        {PROVIDERS.map((p) => (
          <Card
            key={p.id}
            className="cursor-pointer transition-all transition-duration-200"
            style={{
              width: '260px',
              border: `2px solid ${p.borderColor}`,
              background: p.bg,
              borderRadius: '16px',
              boxShadow: `0 4px 24px ${p.color}30`,
            }}
            onClick={() => onSelect(p.id)}
          >
            <div className="flex flex-column align-items-center text-center p-3">
              <div
                className="flex align-items-center justify-content-center border-circle mb-3"
                style={{
                  width: '72px',
                  height: '72px',
                  background: p.color,
                  fontSize: '1.8rem',
                }}
              >
                <span style={{ color: '#fff', fontWeight: 700, fontSize: '1.1rem' }}>
                  {p.shortName}
                </span>
              </div>
              <h2 className="text-xl font-bold m-0 mb-1" style={{ color: '#f1f5f9' }}>
                {p.name}
              </h2>
              <p className="text-sm m-0 mb-3" style={{ color: '#94a3b8' }}>{p.description}</p>
              <Button
                label={`Connect to ${p.shortName}`}
                style={{ background: p.color, borderColor: p.color, width: '100%' }}
                onClick={(e) => { e.stopPropagation(); onSelect(p.id); }}
              />
            </div>
          </Card>
        ))}
      </div>

      <p className="text-sm mt-5" style={{ color: '#64748b' }}>
        💡 No real credentials required — mock data is used automatically
      </p>
    </div>
  );
}
