// API route map for the LexiShield backend (contracts/openapi.json).
//
// The base is relative: in development Vite proxies /api to the backend (vite.config.js); in production the backend
// serves this app itself, so both run on one local origin with no CORS and no network access.
// Set VITE_API_BASE only to point at a backend on another origin.

export const API_BASE = import.meta.env?.VITE_API_BASE || "/api/v1";

// Contract fixtures are shown ONLY in explicit demo mode. Otherwise a failed call shows its real error:
// a fixture answer looks grounded but is not about the user's document.
export const USE_MOCKS = import.meta.env?.VITE_USE_MOCKS === "true";

export const ENDPOINTS = {
  // Documents & source
  DOCUMENTS: `${API_BASE}/documents`,
  DOCUMENTS_TEXT: `${API_BASE}/documents/text`,
  DOCUMENT_DETAIL: (id) => `${API_BASE}/documents/${id}`,
  DOCUMENT_FILE: (id) => `${API_BASE}/documents/${id}/file`,
  DOCUMENT_CLAUSE: (docId, clauseId) => `${API_BASE}/documents/${docId}/clauses/${clauseId}`,
  DOCUMENT_DELETE: (id) => `${API_BASE}/documents/${id}`,

  // Analysis
  ANALYZE: (id) => `${API_BASE}/documents/${id}/analyze`,
  JOB_EVENTS: (jobId) => `${API_BASE}/jobs/${jobId}/events`,
  JOB_INFO: (jobId) => `${API_BASE}/jobs/${jobId}`,
  JOB_CANCEL: (jobId) => `${API_BASE}/jobs/${jobId}/cancel`,
  REPORT: (id) => `${API_BASE}/documents/${id}/report`,

  // Grounded chat
  ASK: (id) => `${API_BASE}/documents/${id}/ask`,

  // What-if scenarios
  SCENARIOS: (docType) => (docType ? `${API_BASE}/scenarios?doc_type=${docType}` : `${API_BASE}/scenarios`),
  SCENARIO_RUN: (docId, sid) => `${API_BASE}/documents/${docId}/scenarios/${sid}/run`,

  // Statutes, brief, packs
  STATUTES: (id) => `${API_BASE}/documents/${id}/statutes`,
  BRIEF: (id, format = "json") => `${API_BASE}/documents/${id}/brief?format=${format}`,
  PACKS: `${API_BASE}/packs`,
  PACK_DETAIL: (id) => `${API_BASE}/packs/${id}`,

  // Privacy
  PRIVACY_STATUS: `${API_BASE}/privacy/status`,
  PRIVACY_EVENTS: `${API_BASE}/privacy/events`,
  PRIVACY_RECEIPTS: `${API_BASE}/privacy/receipts`,
  PRIVACY_RECEIPT_DETAIL: (id) => `${API_BASE}/privacy/receipts/${id}`,
  SESSIONS_WIPE: `${API_BASE}/sessions`,

  // System
  HEALTH: `${API_BASE}/health`,
  SYSTEM_INFO: `${API_BASE}/system/info`,
  BENCHMARK: `${API_BASE}/system/benchmark`,
  EVAL_SUMMARY: `${API_BASE}/eval/summary`,
};
