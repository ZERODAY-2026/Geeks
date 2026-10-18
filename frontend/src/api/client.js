import { ENDPOINTS, USE_MOCKS } from "./config";
import * as MockData from "./mockData";

/** An API error with the backend's problem+json code (e.g. NOT_FOUND, CONFLICT, MODEL_UNAVAILABLE). */
export class ApiError extends Error {
  constructor(message, { status = 0, code = "NETWORK_ERROR" } = {}) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/**
 * Calls the local backend. The contract fixture is returned ONLY in demo mode (VITE_USE_MOCKS=true).
 * In normal use every failure surfaces as an ApiError, so the UI never shows a fixture as if it were
 * about the user's document.
 */
async function fetchWithFallback(url, options = {}, fallbackData = null) {
  if (USE_MOCKS && fallbackData !== null) {
    return fallbackData;
  }
  let res;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    throw new ApiError("The LexiShield server is not reachable. Is it running?", { code: "NETWORK_ERROR" });
  }

  if (res.ok) {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return await res.json();
    }
    return await res.text();
  }

  const problem = await res.json().catch(() => ({}));
  throw new ApiError(problem.detail || problem.title || `HTTP error ${res.status}`, {
    status: res.status,
    code: problem.code || `HTTP_${res.status}`,
  });
}

/** URL of the original uploaded file. For a PDF, `#page=N` opens the browser's built-in viewer at that page. */
export function documentFileUrl(documentId, page = null) {
  const url = ENDPOINTS.DOCUMENT_FILE(documentId);
  return page ? `${url}#page=${page}` : url;
}

export const ApiClient = {
  // =========================================================================
  // Category 1: Documents & Source Ingestion (5 Endpoints)
  // =========================================================================

  /** 1. POST /api/v1/documents - Upload PDF/DOCX/TXT file */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);
    return fetchWithFallback(
      ENDPOINTS.DOCUMENTS,
      { method: "POST", body: formData },
      MockData.document_summary
    );
  },

  /** 2. POST /api/v1/documents/text - Paste plain text directly */
  async uploadText(text, filename = "pasted.txt") {
    return fetchWithFallback(
      ENDPOINTS.DOCUMENTS_TEXT,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, filename }),
      },
      MockData.document_summary
    );
  },

  /** 3. GET /api/v1/documents/{document_id} - Fetch page text & clauses */
  async getDocument(documentId) {
    return fetchWithFallback(
      ENDPOINTS.DOCUMENT_DETAIL(documentId),
      { method: "GET" },
      MockData.document_detail
    );
  },

  /** 4. GET /api/v1/documents/{document_id}/clauses/{clause_id} - Lookup single clause */
  async getClause(documentId, clauseId) {
    return fetchWithFallback(
      ENDPOINTS.DOCUMENT_CLAUSE(documentId, clauseId),
      { method: "GET" },
      MockData.document_detail?.clauses?.find((c) => c.id === clauseId) || {
        id: clauseId,
        heading: `Clause ${clauseId}`,
        text: "Clause details retrieved from document index.",
      }
    );
  },

  /** 5. DELETE /api/v1/documents/{document_id} - Cryptographically shred document from RAM */
  async deleteDocument(documentId) {
    return fetchWithFallback(
      ENDPOINTS.DOCUMENT_DELETE(documentId),
      { method: "DELETE" },
      { deleted: true, crypto_shredded: true }
    );
  },

  // =========================================================================
  // Category 2: Pipeline Analysis & Progressive Streaming (5 Endpoints)
  // =========================================================================

  /** 6. POST /api/v1/documents/{document_id}/analyze - Start background pipeline */
  async startAnalysis(documentId, params = {}) {
    return fetchWithFallback(
      ENDPOINTS.ANALYZE(documentId),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // No default role: the backend detects party roles. Send user_role only when the user chose one.
        body: JSON.stringify({ language: "en", ...params }),
      },
      MockData.job_accepted
    );
  },

  /** 7. GET /api/v1/jobs/{job_id}/events - SSE progressive stream */
  subscribeJobEvents(jobId, onEvent, onError) {
    const eventSource = new EventSource(ENDPOINTS.JOB_EVENTS(jobId));

    const events = [
      "job.stage",
      "classification.ready",
      "checklist.item",
      "card.ready",
      "warning",
      "report.ready",
      "job.failed",
    ];

    events.forEach((eventType) => {
      eventSource.addEventListener(eventType, (e) => {
        try {
          const data = JSON.parse(e.data);
          onEvent(eventType, data);
        } catch (err) {
          console.error("Failed to parse SSE payload", err);
        }
      });
    });

    eventSource.onerror = (err) => {
      if (onError) onError(err);
      eventSource.close();
    };

    return () => eventSource.close();
  },

  /** 8. GET /api/v1/jobs/{job_id} - Poll job progress */
  async getJobInfo(jobId) {
    return fetchWithFallback(
      ENDPOINTS.JOB_INFO(jobId),
      { method: "GET" },
      MockData.job_info
    );
  },

  /** 9. POST /api/v1/jobs/{job_id}/cancel - Cancel in-flight job */
  async cancelJob(jobId) {
    return fetchWithFallback(
      ENDPOINTS.JOB_CANCEL(jobId),
      { method: "POST" },
      { job_id: jobId, status: "cancelled" }
    );
  },

  /** 10. GET /api/v1/documents/{document_id}/report - Get full triage report */
  async getReport(documentId) {
    return fetchWithFallback(
      ENDPOINTS.REPORT(documentId),
      { method: "GET" },
      MockData.report
    );
  },

  // =========================================================================
  // Category 3: Grounded Chat & Verification (1 Endpoint)
  // =========================================================================

  /** 11. POST /api/v1/documents/{document_id}/ask - Grounded Q&A */
  async askQuestion(documentId, { question, conversationId = null, userRole = null }) {
    return fetchWithFallback(
      ENDPOINTS.ASK(documentId),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          conversation_id: conversationId,
          user_role: userRole,
        }),
      },
      MockData.ask_answered
    );
  },

  // =========================================================================
  // Category 4: "What-If" Crisis Scenarios (2 Endpoints)
  // =========================================================================

  /** 12. GET /api/v1/scenarios - List life crisis scenarios */
  async getScenarios(docType = null) {
    return fetchWithFallback(
      ENDPOINTS.SCENARIOS(docType),
      { method: "GET" },
      MockData.scenarios
    );
  },

  /** 13. POST /api/v1/documents/{document_id}/scenarios/{scenario_id}/run */
  async runScenario(documentId, scenarioId, params = {}) {
    return fetchWithFallback(
      ENDPOINTS.SCENARIO_RUN(documentId, scenarioId),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ params }),
      },
      MockData.scenario_result
    );
  },

  // =========================================================================
  // Category 5: Statutes, Checklists & Lawyer Consultation Brief (4 Endpoints)
  // =========================================================================

  /** 14. GET /api/v1/documents/{document_id}/statutes - Offline Open India Law excerpts */
  async getStatutes(documentId) {
    return fetchWithFallback(
      ENDPOINTS.STATUTES(documentId),
      { method: "GET" },
      MockData.statutes
    );
  },

  /** 15. GET /api/v1/documents/{document_id}/brief - 1-page escalation summary */
  async getBrief(documentId, format = "json") {
    return fetchWithFallback(
      ENDPOINTS.BRIEF(documentId, format),
      { method: "GET" },
      MockData.brief
    );
  },

  /** 16. GET /api/v1/packs - List checklist packs */
  async getPacks() {
    return fetchWithFallback(
      ENDPOINTS.PACKS,
      { method: "GET" },
      MockData.packs
    );
  },

  /** 17. GET /api/v1/packs/{pack_id} - Inspect specific pack */
  async getPack(packId) {
    return fetchWithFallback(
      ENDPOINTS.PACK_DETAIL(packId),
      { method: "GET" },
      MockData.packs?.find?.((p) => p.pack_id === packId) || {
        pack_id: packId,
        doc_type: "rental",
        jurisdiction: "IN",
        version: "1.0",
        depth: "deep",
        topics: [],
      }
    );
  },

  // =========================================================================
  // Category 6: Privacy, Egress Guard & Cryptographic Receipts (5 Endpoints)
  // =========================================================================

  /** 18. GET /api/v1/privacy/status - Egress guard telemetry */
  async getPrivacyStatus() {
    return fetchWithFallback(
      ENDPOINTS.PRIVACY_STATUS,
      { method: "GET" },
      MockData.privacy_status
    );
  },

  /** 19. GET /api/v1/privacy/events - Network audit logs intercepted by audit hook */
  async getPrivacyEvents() {
    return fetchWithFallback(
      ENDPOINTS.PRIVACY_EVENTS,
      { method: "GET" },
      MockData.privacy_events || []
    );
  },

  /** 20. POST /api/v1/privacy/receipts - Mint Ed25519 signed JSON receipt */
  async createPrivacyReceipt(documentId = null) {
    return fetchWithFallback(
      ENDPOINTS.PRIVACY_RECEIPTS,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId }),
      },
      MockData.privacy_receipt
    );
  },

  /** 21. GET /api/v1/privacy/receipts/{receipt_id} - Inspect previously minted receipt */
  async getPrivacyReceipt(receiptId) {
    return fetchWithFallback(
      ENDPOINTS.PRIVACY_RECEIPT_DETAIL(receiptId),
      { method: "GET" },
      MockData.privacy_receipt
    );
  },

  /** 22. DELETE /api/v1/sessions - Panic wipe all docs, sessions & cache */
  async wipeSessions() {
    return fetchWithFallback(
      ENDPOINTS.SESSIONS_WIPE,
      { method: "DELETE" },
      { wiped: 1 }
    );
  },

  // =========================================================================
  // Category 7: System Health, Benchmarks & Evaluation (4 Endpoints)
  // =========================================================================

  /** 23. GET /api/v1/health - System health probe */
  async getHealth() {
    return fetchWithFallback(
      ENDPOINTS.HEALTH,
      { method: "GET" },
      MockData.health
    );
  },

  /** 24. GET /api/v1/system/info - Hardware & model telemetry */
  async getSystemInfo() {
    return fetchWithFallback(
      ENDPOINTS.SYSTEM_INFO,
      { method: "GET" },
      MockData.system_info
    );
  },

  /** 25. GET /api/v1/system/benchmark - On-device benchmarks */
  async getBenchmark() {
    return fetchWithFallback(
      ENDPOINTS.BENCHMARK,
      { method: "GET" },
      MockData.benchmark
    );
  },

  /** 26. GET /api/v1/eval/summary - Evaluation rubric scores */
  async getEvalSummary() {
    return fetchWithFallback(
      ENDPOINTS.EVAL_SUMMARY,
      { method: "GET" },
      { redteam: { pass_rate: 0.94, total: 25 }, cuad: { precision: 0.89 } }
    );
  },
};
