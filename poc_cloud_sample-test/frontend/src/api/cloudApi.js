import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

export const validateCredentials = (provider, credentials) =>
  api.post('/api/credentials/validate', { provider, credentials });

export const clearCredentials = () => api.delete('/api/credentials');

export const getSession = () => api.get('/api/session');

export const getResources = (resourceTypes = null, region = null) =>
  api.get('/api/resources', {
    params: {
      ...(resourceTypes && resourceTypes.length && { resource_types: resourceTypes.join(',') }),
      ...(region && { region }),
    },
  });

export const getResourceTypes = () => api.get('/api/billing/resource-types');

export const getResourceSummary = (region = null) =>
  api.get('/api/resources/summary', {
    params: {
      ...(region && { region }),
    },
  });

export const getOverallBilling = (startDate, endDate, region = null, bqProject = null) =>
  api.get('/api/billing/overall', {
    params: {
      ...(startDate && { start_date: startDate }),
      ...(endDate && { end_date: endDate }),
      ...(region && { region }),
      ...(bqProject && { bq_project: bqProject }),
    },
  });

export const getBillingByResourceType = (resourceType, startDate, endDate, region = null, bqProject = null) =>
  api.get('/api/billing/by-resource-type', {
    params: {
      resource_type: resourceType,
      ...(startDate && { start_date: startDate }),
      ...(endDate && { end_date: endDate }),
      ...(region && { region }),
      ...(bqProject && { bq_project: bqProject }),
    },
  });

export const getGcpBqProjects = () => api.get('/api/billing/gcp-bq-projects');

export const gcpOAuthInit = (clientId, clientSecret, bigqueryDataset = '', bigqueryTable = '') =>
  api.post('/api/gcp/oauth/init', {
    client_id: clientId,
    client_secret: clientSecret,
    bigquery_dataset: bigqueryDataset,
    bigquery_table: bigqueryTable,
  });

export const getGcpOrganizations = () => api.get('/api/gcp/organizations');

export const selectGcpOrg = (orgId) =>
  api.post('/api/gcp/select-org', { org_id: orgId });

export const getGcpProjects = (orgId = '') =>
  api.get('/api/gcp/projects', { params: orgId ? { org_id: orgId } : {} });

export const selectGcpProject = (projectId) =>
  api.post('/api/gcp/select-project', { project_id: projectId });

export const updateGcpBillingConfig = (bigqueryDataset, bigqueryTable) =>
  api.post('/api/gcp/billing-config', {
    bigquery_dataset: bigqueryDataset,
    bigquery_table: bigqueryTable,
  });

export const getGcpIamRoles = () => api.get('/api/gcp/iam');

export const getGcpSuggestions = () => api.get('/api/gcp/suggestions');

export const getAwsIamRoles = () => api.get('/api/aws/iam');

export const getAwsSuggestions = () => api.get('/api/aws/suggestions');

export default api;
