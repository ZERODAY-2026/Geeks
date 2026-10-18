import React, { useState, useEffect, useRef } from "react";
import { ApiClient } from "./api/client";
import { citationLocation, fileTypeLabel } from "./lib/format";
import { TierBadge, DistortionBadge } from "./components/Badges";
import TrustModal from "./components/TrustModal";
import ClausesPanel from "./components/ClausesPanel";
import DocumentViewer from "./components/DocumentViewer";
import DocumentMetadataPanel from "./components/DocumentMetadataPanel";
import PasteTextModal from "./components/PasteTextModal";
import AnalysisProgressModal from "./components/AnalysisProgressModal";
import ScenariosModal from "./components/ScenariosModal";
import LegalLibraryModal from "./components/LegalLibraryModal";
import EmptyStateLanding from "./components/EmptyStateLanding";

// --- Inline SVGs for local zero-dependency bundling ---
const Icons = {
  Logo: () => (
    <svg className="w-6 h-6 text-emerald-500" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6l-8-4zm-1 15l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z" />
    </svg>
  ),
  SidebarToggle: () => (
    <svg className="w-4 h-4 text-neutral-400 hover:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <rect x="3" y="4" width="18" height="16" rx="2" strokeWidth="2" />
      <line x1="9" y1="4" x2="9" y2="20" strokeWidth="2" />
    </svg>
  ),
  Plus: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  FileText: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Library: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M8 14v5m4-9v9m4-5v5m2 2H6a2 2 0 01-2-2V5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2z" />
    </svg>
  ),
  Settings: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  Folder: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  ShieldCheck: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  PdfIcon: () => (
    <div className="w-6 h-6 rounded bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 font-bold text-[10px] tracking-tight">
      PDF
    </div>
  ),
  Lock: () => (
    <svg className="w-3.5 h-3.5 text-emerald-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 018 0v4" />
    </svg>
  ),
  MoreVertical: () => (
    <svg className="w-4 h-4 text-neutral-400 hover:text-neutral-600" fill="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="5" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="12" cy="19" r="1.5" />
    </svg>
  ),
  ExternalLink: () => (
    <svg className="w-3.5 h-3.5 text-neutral-400 hover:text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6m4-3h6v6m-11 5L21 3" />
    </svg>
  ),
  AlertCircle: () => (
    <svg className="w-4 h-4 text-amber-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  ArrowUp: () => (
    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  ),
  Attachment: () => (
    <svg className="w-4 h-4 text-neutral-500 hover:text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
    </svg>
  ),
};

// Starter questions by detected document type. They are only suggestions; any question can be asked.
const SUGGESTIONS = {
  rental: ["How much is the security deposit?", "What is the notice period?", "Is there a lock-in period?", "Who pays for repairs?"],
  employment: ["What is the notice period?", "Is there a service bond?", "How long is probation?", "Is there a non-compete?"],
  msa: ["When must the client pay?", "Who owns the work?", "How can either side end the agreement?", "Is liability capped?"],
  legal_notice: ["What is being demanded?", "How much is claimed?", "What is the deadline?", "What happens if I do not respond?"],
  unknown: ["What is this document about?", "What are the main obligations?", "What deadlines does it set?", "What amounts does it mention?"],
};

export default function LexiShieldApp() {
  // Page mode: "landing" (Empty State) vs "document" (4-column active document)
  const [viewMode, setViewMode] = useState("landing");

  // Document state (all real: nothing is shown until a document is uploaded)
  const [documentId, setDocumentId] = useState(null);
  const [docDetail, setDocDetail] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [privacyStatus, setPrivacyStatus] = useState(null);
  const [sessionDocs, setSessionDocs] = useState([]); // documents uploaded in this session: {document_id, filename}
  const [health, setHealth] = useState(null); // GET /health: is Ollama up and is Gemma pulled?
  const [conversationId, setConversationId] = useState(null);
  const [sourceFocus, setSourceFocus] = useState(0); // bumps when a citation is opened, so the viewer comes forward

  // Collapsible Sidebars & Dynamic Chat Sizing State
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showDocNav, setShowDocNav] = useState(true);
  const [showRightSidebar, setShowRightSidebar] = useState(true);
  const [chatWidth, setChatWidth] = useState(720); // range 480px to 1100px
  const [chatFontSize, setChatFontSize] = useState(13); // range 11px to 22px
  const [showDisplaySettings, setShowDisplaySettings] = useState(false);

  // Layout & Navigation State
  const [activeTab, setActiveTab] = useState("Pages");
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Active highlighted citation (a real citation from an answer, or a clause the user picked)
  const [activeCitation, setActiveCitation] = useState(null);

  // Modals for the 26 endpoints
  const [isTrustOpen, setIsTrustOpen] = useState(false);
  const [trustInitialTab, setTrustInitialTab] = useState("privacy");
  const [isPasteTextOpen, setIsPasteTextOpen] = useState(false);
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);
  const [isScenariosOpen, setIsScenariosOpen] = useState(false);
  const [isLegalLibraryOpen, setIsLegalLibraryOpen] = useState(false);
  const [showDocMenu, setShowDocMenu] = useState(false);

  // Chat messages (AskResponse per assistant turn)
  const [messages, setMessages] = useState([]);

  const [inputValue, setInputValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  const docType = reportData?.classification?.doc_type || docDetail?.summary?.quick_detect?.doc_type || "unknown";
  const suggestions = SUGGESTIONS[docType] || SUGGESTIONS.unknown;

  // Telemetry and model readiness on mount, and again whenever a document is opened
  const refreshHealth = () => {
    ApiClient.getHealth().then(setHealth).catch(() => setHealth({ ollama: "unreachable", models_ready: false }));
  };
  useEffect(() => {
    ApiClient.getPrivacyStatus().then(setPrivacyStatus).catch(console.error);
    refreshHealth();
  }, []);

  // GET /documents/{id} and GET /documents/{id}/report (the report exists only after analysis)
  const loadDocument = (id, filename = null) => {
    setDocumentId(id);
    setDocDetail(null);
    setReportData(null);
    setMessages([]);
    setConversationId(null);
    setActiveCitation(null);
    setCurrentPage(1);
    if (filename) {
      setSessionDocs((prev) => (prev.some((d) => d.document_id === id) ? prev : [...prev, { document_id: id, filename }]));
    }
    refreshHealth();
    ApiClient.getDocument(id)
      .then((data) => {
        setDocDetail(data);
        if (data?.pages?.length > 0) setCurrentPage(data.pages[0].page);
        setViewMode("document");
      })
      .catch((err) => {
        console.error(err);
        window.alert(`Could not open the document: ${err.message}`);
      });
    ApiClient.getReport(id)
      .then(setReportData)
      .catch(() => setReportData(null)); // 404 until the analysis has run
  };

  // POST /documents (file upload)
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-uploading the same file
    if (!file) return;
    try {
      const summary = await ApiClient.uploadDocument(file);
      loadDocument(summary.document_id, summary.filename);
    } catch (err) {
      window.alert(`Upload failed: ${err.message}`);
    }
  };

  // POST /documents/text (pasted text)
  const handleDocumentCreated = (summary, initialQuestion = null) => {
    loadDocument(summary.document_id, summary.filename);
    if (initialQuestion) {
      handleSendMessage(initialQuestion, summary.document_id);
    }
  };

  // DELETE /documents/{id}
  const handleDeleteDocument = async () => {
    if (!documentId) return;
    if (!window.confirm("Close and cryptographically shred this document from memory?")) return;
    try {
      await ApiClient.deleteDocument(documentId);
    } catch (err) {
      console.error("Delete failed", err);
    }
    setSessionDocs((prev) => prev.filter((d) => d.document_id !== documentId));
    setDocumentId(null);
    setDocDetail(null);
    setReportData(null);
    setMessages([]);
    setActiveCitation(null);
    setShowDocMenu(false);
    setViewMode("landing");
  };

  // POST /documents/{id}/ask
  const handleSendMessage = async (textToSend, forDocumentId = null) => {
    const text = (typeof textToSend === "string" ? textToSend : null) || inputValue;
    const targetId = forDocumentId || documentId;
    if (!text.trim() || isSubmitting || !targetId) return;

    const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { id: `m_${Date.now()}`, sender: "user", timestamp: now(), text: text.trim() }]);
    setInputValue("");
    setIsSubmitting(true);

    try {
      const response = await ApiClient.askQuestion(targetId, {
        question: text.trim(),
        conversationId,
        userRole: null, // the backend uses the roles it detected; no role is assumed
      });
      setConversationId(response.conversation_id || conversationId);
      setMessages((prev) => [
        ...prev,
        {
          id: `m_ai_${Date.now()}`,
          sender: "assistant",
          timestamp: now(),
          status: response.status,
          message: response.message,
          claims: response.claims || [],
          relatedClauses: response.related_clauses || [],
          notFoundNote: response.not_found_note,
          clarifyingQuestion: response.clarifying_question,
          escalation: response.escalation,
          disclaimer: response.disclaimer || "Preliminary information, not legal advice.",
        },
      ]);
      const firstCite = response.claims?.[0]?.citations?.[0];
      if (firstCite) openCitation(firstCite);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `m_err_${Date.now()}`,
          sender: "assistant",
          timestamp: now(),
          status: "ERROR",
          message:
            err.code === "MODEL_UNAVAILABLE" || err.code === "NETWORK_ERROR"
              ? `${err.message} Start Ollama and the LexiShield server, then try again.`
              : `The question could not be answered: ${err.message}`,
          claims: [],
          disclaimer: "Preliminary information, not legal advice.",
        },
      ]);
      refreshHealth();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open a citation (or a clause) in the source viewer, highlighting exactly the cited characters.
  const openCitation = (cite) => {
    setActiveCitation(cite);
    setCurrentPage(cite.page || 1);
    setSourceFocus((n) => n + 1);
    setShowRightSidebar(true);
  };

  const handleSelectClause = (clauseOrCite) => {
    if (clauseOrCite?.quote !== undefined) {
      openCitation(clauseOrCite); // a citation: keep its exact span
      return;
    }
    // a clause from the clause list: highlight the whole clause
    openCitation({
      page: clauseOrCite.page_start || 1,
      char_start: clauseOrCite.char_start,
      char_end: clauseOrCite.char_end,
      clause_id: clauseOrCite.id,
      quote: clauseOrCite.text,
    });
  };

  // DELETE /sessions (panic wipe, from the Trust modal)
  const handlePanicWipe = () => {
    setSessionDocs([]);
    setDocumentId(null);
    setDocDetail(null);
    setReportData(null);
    setMessages([]);
    setActiveCitation(null);
    setViewMode("landing");
  };

  const currentPageData = docDetail?.pages?.find((p) => p.page === currentPage);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FAF9F6] text-neutral-800 font-sans antialiased text-sm select-none relative">
      
      {/* Floating Restore Button for Left Sidebar when collapsed */}
      {!showLeftSidebar && (
        <button
          onClick={() => setShowLeftSidebar(true)}
          className="fixed top-3 left-3 z-50 p-2 bg-[#18191B] text-neutral-300 hover:text-white rounded-lg shadow-lg border border-neutral-700/80 transition flex items-center gap-2 text-xs"
          title="Expand Navigation Sidebar"
        >
          <Icons.SidebarToggle />
          <span className="font-medium text-[11px] hidden sm:inline">LexiShield</span>
        </button>
      )}

      {/* ── COLUMN 1: DARK SIDEBAR ─────────────────────────────────── */}
      {showLeftSidebar && (
        <aside className="w-64 bg-[#18191B] text-neutral-300 flex flex-col justify-between border-r border-neutral-800 flex-shrink-0 animate-fadeIn">
          <div>
            {/* Logo Header */}
            <div className="p-4 flex items-center justify-between border-b border-neutral-800/60">
              <div
                onClick={() => setViewMode("landing")}
                className="flex items-center gap-2.5 cursor-pointer"
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <Icons.Logo />
                </div>
                <div>
                  <h1 className="text-white font-semibold text-base leading-tight">LexiShield</h1>
                  <p className="text-[11px] text-neutral-400">Your private legal companion</p>
                </div>
              </div>
              <button
                onClick={() => setShowLeftSidebar(false)}
                className="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white transition"
                title="Collapse sidebar"
              >
                <Icons.SidebarToggle />
              </button>
            </div>

          {/* New Chat Button (Active/Highlighted on Landing State) */}
          <div className="p-3 space-y-2">
            <button
              onClick={() => setViewMode("landing")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition shadow-sm ${
                viewMode === "landing"
                  ? "bg-[#27292D] text-white border border-neutral-600/80 ring-1 ring-neutral-500/30"
                  : "bg-[#24262A] hover:bg-[#2C2E33] text-white border border-neutral-700/60"
              }`}
            >
              <Icons.Plus />
              <span>New chat</span>
            </button>
          </div>

          {/* Main Navigation */}
          <nav className="px-2 space-y-0.5">
            <button
              onClick={() => setIsPasteTextOpen(true)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-neutral-800/60 text-neutral-300 text-xs transition"
            >
              <Icons.FileText />
              <span>Documents</span>
            </button>
            <button
              onClick={() => setIsLegalLibraryOpen(true)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-neutral-800/60 text-neutral-300 text-xs transition"
            >
              <Icons.Library />
              <span>Legal Library</span>
            </button>
            <button
              onClick={() => {
                setTrustInitialTab("hardware");
                setIsTrustOpen(true);
              }}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-neutral-800/60 text-neutral-300 text-xs transition"
            >
              <Icons.Settings />
              <span>Settings</span>
            </button>
          </nav>

          {/* Folders Section */}
          <div className="mt-6 px-3">
            <div className="flex items-center justify-between text-[11px] font-medium text-neutral-400 px-2 mb-1.5 uppercase tracking-wider">
              <span>Folders</span>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="hover:text-white"
                title="Upload document"
              >
                <Icons.Plus />
              </button>
            </div>

            <div className="space-y-1">
              {sessionDocs.length === 0 && (
                <div className="px-3 py-2 text-[11px] text-neutral-500">
                  No documents yet. Upload a PDF, DOCX or TXT to start. Documents stay in memory on this machine.
                </div>
              )}
              {sessionDocs.map((d) => (
                <button
                  key={d.document_id}
                  onClick={() => loadDocument(d.document_id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition text-left ${
                    d.document_id === documentId && viewMode === "document"
                      ? "bg-[#27292D] text-white border border-neutral-700/60 font-medium"
                      : "hover:bg-neutral-800/50 text-neutral-300"
                  }`}
                  title={d.filename}
                >
                  <Icons.Folder />
                  <span className="truncate">{d.filename}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Footer: Privacy, Receipts & User Profile */}
        <div className="p-3 border-t border-neutral-800/80 space-y-2">
          {/* Endpoint 18: GET /privacy/status */}
          <div
            onClick={() => {
              setTrustInitialTab("privacy");
              setIsTrustOpen(true);
            }}
            className="p-2.5 rounded-lg bg-[#202226] border border-neutral-700/50 flex items-center justify-between hover:border-neutral-500 transition cursor-pointer"
          >
            <div className="flex items-start gap-2.5">
              <div className="w-2 h-2 rounded-full bg-emerald-400 mt-1 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <div>
                <p className="text-xs font-medium text-emerald-400 leading-none mb-1">Running locally</p>
                <p className="text-[10px] text-neutral-400">No data leaves your device.</p>
              </div>
            </div>
            <span className="text-neutral-500 text-xs">›</span>
          </div>

          {/* Endpoint 20 & 21: Privacy Receipts */}
          <div
            onClick={() => {
              setTrustInitialTab("receipt");
              setIsTrustOpen(true);
            }}
            className="flex items-center justify-between px-3 py-1.5 rounded-md hover:bg-neutral-800/50 cursor-pointer text-xs text-neutral-300"
          >
            <div className="flex items-center gap-2.5">
              <Icons.ShieldCheck />
              <span>Privacy Receipt</span>
            </div>
            <span className="text-[9px] font-mono text-emerald-400 bg-emerald-950 px-1 rounded">Ed25519</span>
          </div>

          {/* User Profile */}
          <div className="pt-2 border-t border-neutral-800 flex items-center justify-between px-2 cursor-pointer hover:bg-neutral-800/40 rounded p-1">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center font-medium text-xs">
                P
              </div>
              <span className="text-xs font-medium text-white">Prince</span>
            </div>
            <span className="text-neutral-500 text-xs">▾</span>
          </div>
        </div>
      </aside>
      )}

      {/* ── MAIN CONTENT AREA ────────────────────────────────────────── */}
      {viewMode === "landing" ? (
        /* Empty State / Upload Landing Page (Endpoints 1, 2, 18) */
        <EmptyStateLanding
          onDocumentLoaded={(summary, initialPrompt) => {
            loadDocument(summary.document_id, summary.filename);
            if (initialPrompt) handleSendMessage(initialPrompt, summary.document_id);
          }}
          onOpenTrustModal={() => {
            setTrustInitialTab("privacy");
            setIsTrustOpen(true);
          }}
          privacyStatus={privacyStatus}
        />
      ) : (
        /* 4-Column Active Document View (Endpoints 3, 4, 5, 6, 7, 8, 9, 10, 11) */
        <>
          {/* ── COLUMN 2: DOCUMENT THUMBNAILS & CLAUSES ──────────────── */}
          {showDocNav && (
            <section className="w-56 bg-[#F8F9FA] border-r border-neutral-200 flex flex-col flex-shrink-0 animate-fadeIn">
              <div className="p-3.5 border-b border-neutral-200 relative">
                <div className="flex items-start justify-between gap-1.5">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <Icons.PdfIcon />
                    <div className="truncate">
                      <p className="text-xs font-semibold text-neutral-800 truncate" title={docDetail?.summary?.filename || ""}>
                        {docDetail?.summary?.filename || "Loading…"}
                      </p>
                      <p className="text-[11px] text-neutral-400">
                        {docDetail
                          ? `${fileTypeLabel(docDetail.summary.mime)} · ${docDetail.summary.pages} pages · ${docDetail.summary.clause_count} clauses`
                          : ""}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-0.5">
                    <button
                      onClick={() => setShowDocNav(false)}
                      className="p-1 hover:bg-neutral-200 rounded text-neutral-400 hover:text-neutral-700 transition"
                      title="Collapse Pages Sidebar"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                    <button
                      onClick={() => setShowDocMenu(!showDocMenu)}
                      className="p-1 hover:bg-neutral-200 rounded text-neutral-500"
                    >
                      <Icons.MoreVertical />
                    </button>
                  </div>
                </div>

              {/* Document Context Menu (Endpoints 5, 6, 12, 15) */}
              {showDocMenu && (
                <div className="absolute right-3 top-12 z-40 w-52 bg-white border border-neutral-200 rounded-lg shadow-xl p-1 text-xs space-y-0.5">
                  <button
                    onClick={() => {
                      setShowDocMenu(false);
                      setIsAnalysisOpen(true);
                    }}
                    className="w-full text-left px-2.5 py-1.5 rounded hover:bg-neutral-100 text-neutral-800 font-medium flex items-center gap-2"
                  >
                    <span>⚡</span> Run Full Pipeline (POST /analyze)
                  </button>
                  <button
                    onClick={() => {
                      setShowDocMenu(false);
                      setIsScenariosOpen(true);
                    }}
                    className="w-full text-left px-2.5 py-1.5 rounded hover:bg-neutral-100 text-neutral-800 flex items-center gap-2"
                  >
                    <span>⚖️</span> Life Scenarios (POST /run)
                  </button>
                  <button
                    onClick={() => {
                      setShowDocMenu(false);
                      setIsLegalLibraryOpen(true);
                    }}
                    className="w-full text-left px-2.5 py-1.5 rounded hover:bg-neutral-100 text-neutral-800 flex items-center gap-2"
                  >
                    <span>📄</span> Export Brief (GET /brief)
                  </button>
                  <div className="border-t border-neutral-100 my-1" />
                  <button
                    onClick={handleDeleteDocument}
                    className="w-full text-left px-2.5 py-1.5 rounded hover:bg-rose-50 text-rose-600 font-medium flex items-center gap-2"
                  >
                    <span>🗑️</span> Close & Shred (DELETE /id)
                  </button>
                </div>
              )}

              {/* Tabs */}
              <div className="flex items-center gap-4 mt-3 pt-1 border-t border-neutral-200/80 text-xs font-medium">
                <button
                  onClick={() => setActiveTab("Pages")}
                  className={`pb-1.5 transition relative ${
                    activeTab === "Pages"
                      ? "text-neutral-900 border-b-2 border-emerald-800 font-semibold"
                      : "text-neutral-400 hover:text-neutral-700"
                  }`}
                >
                  Pages
                </button>
                <button
                  onClick={() => setActiveTab("Clauses")}
                  className={`pb-1.5 transition relative ${
                    activeTab === "Clauses"
                      ? "text-neutral-900 border-b-2 border-emerald-800 font-semibold"
                      : "text-neutral-400 hover:text-neutral-700"
                  }`}
                >
                  Clauses & Checklist
                </button>
              </div>
            </div>

            {/* Tab 1: Pages Thumbnail Strip */}
            {activeTab === "Pages" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-3.5">
                {(docDetail?.pages || []).map(({ page }) => (
                  <div
                    key={page}
                    onClick={() => {
                      setCurrentPage(page);
                      setSourceFocus((n) => n + 1);
                    }}
                    className="flex items-start gap-2.5 cursor-pointer group"
                  >
                    <span className={`text-[11px] w-3 text-right pt-1 font-mono ${
                      currentPage === page ? "text-amber-600 font-bold" : "text-neutral-400"
                    }`}>
                      {page}
                    </span>

                    <div
                      className={`w-28 h-36 bg-white rounded shadow-xs p-2 border transition flex flex-col justify-between ${
                        currentPage === page
                          ? "border-amber-400 ring-2 ring-amber-300/40 shadow-sm"
                          : "border-neutral-200 group-hover:border-neutral-300"
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="h-1 bg-neutral-300 rounded w-4/5 mb-1.5" />
                        <div className="h-0.5 bg-neutral-200 rounded w-full" />
                        <div className="h-0.5 bg-neutral-200 rounded w-11/12" />
                        <div className="h-0.5 bg-neutral-200 rounded w-full" />
                        <div className="h-0.5 bg-neutral-200 rounded w-4/6" />
                        {activeCitation?.page === page && (
                          <div className="my-1.5 p-1 bg-amber-50 rounded border border-amber-200">
                            <div className="h-0.5 bg-amber-400 rounded w-full mb-0.5" />
                            <div className="h-0.5 bg-amber-300 rounded w-5/6" />
                          </div>
                        )}
                        <div className="h-0.5 bg-neutral-200 rounded w-full" />
                        <div className="h-0.5 bg-neutral-200 rounded w-5/6" />
                      </div>
                      <div className="text-[8px] text-center text-neutral-300 font-mono">{page}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 2: Clauses Panel (Endpoint 4 & 10) */}
            {activeTab === "Clauses" && (
              <ClausesPanel
                clauses={docDetail?.clauses || []}
                cards={reportData?.cards || []}
                checklist={reportData?.checklist || []}
                onSelectClause={handleSelectClause}
              />
            )}
          </section>
          )}

          {/* ── COLUMN 3: CHAT & LEGAL AI INTERFACE ─────────────────── */}
          <section className="flex-1 flex flex-col bg-[#FAF9F6] border-r border-neutral-200 min-w-[380px] overflow-hidden">
            {/* Header */}
            <div className="h-14 border-b border-neutral-200/80 px-6 flex items-center justify-between bg-white/70 backdrop-blur-sm flex-shrink-0">
              <div className="flex items-center gap-3">
                {/* Restore Pages/Clauses Button if collapsed */}
                {!showDocNav && (
                  <button
                    onClick={() => setShowDocNav(true)}
                    className="px-2.5 py-1 rounded-md bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium flex items-center gap-1.5 transition border border-neutral-300"
                    title="Show document pages & clauses"
                  >
                    <Icons.PdfIcon />
                    <span>Pages</span>
                  </button>
                )}

                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xs font-semibold text-neutral-800 capitalize">
                      {docType === "unknown" ? "Document" : docType.replace("_", " ")}
                      {(reportData?.jurisdiction?.state || reportData?.jurisdiction?.country) &&
                        ` · ${reportData.jurisdiction.state || reportData.jurisdiction.country}`}
                      {!reportData && <span className="ml-2 text-[10px] font-normal text-neutral-400 normal-case">not analysed yet</span>}
                    </h2>
                  </div>
                  <p className="text-[11px] text-neutral-400">{docDetail?.summary?.filename || ""}</p>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                {/* Sliders / Display Controls Toggle */}
                <button
                  onClick={() => setShowDisplaySettings(!showDisplaySettings)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition flex items-center gap-1.5 border shadow-2xs ${
                    showDisplaySettings
                      ? "bg-amber-100 text-amber-900 border-amber-300 ring-2 ring-amber-300/40"
                      : "bg-white hover:bg-neutral-100 text-neutral-700 border-neutral-300"
                  }`}
                  title="Adjust chat width and text font size"
                >
                  <span className="font-serif font-bold text-xs">Aa</span>
                  <span>Sliders</span>
                  <span className="text-[10px] text-neutral-500 font-mono hidden md:inline">
                    ({chatFontSize}px / {chatWidth}px)
                  </span>
                </button>

                <button
                  onClick={() => setIsAnalysisOpen(true)}
                  className="px-2.5 py-1 rounded-md bg-neutral-900 hover:bg-neutral-800 text-white text-[11px] font-medium transition flex items-center gap-1 shadow-2xs"
                >
                  <span>⚡</span>
                  <span>Analyze</span>
                </button>

                <button
                  onClick={() => {
                    setTrustInitialTab("privacy");
                    setIsTrustOpen(true);
                  }}
                  className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-medium hover:bg-emerald-100 transition cursor-pointer"
                >
                  <Icons.Lock />
                  <span>Offline</span>
                </button>

                {/* Restore Right Metadata Sidebar Button if collapsed */}
                {!showRightSidebar && (
                  <button
                    onClick={() => setShowRightSidebar(true)}
                    className="px-2.5 py-1 rounded-md bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-900 text-xs font-medium flex items-center gap-1.5 transition"
                    title="Show Document Metadata & Ingestion Intelligence"
                  >
                    <span>ℹ️</span>
                    <span>Metadata</span>
                  </button>
                )}

                <button
                  onClick={() => setShowDocMenu(!showDocMenu)}
                  className="p-1 hover:bg-neutral-100 rounded text-neutral-500"
                >
                  <Icons.MoreVertical />
                </button>
              </div>
            </div>

            {/* ── INTERACTIVE SLIDERS TOOLBAR (CHAT WIDTH & FONT SIZE) ── */}
            {showDisplaySettings && (
              <div className="bg-[#F6F4EE] border-b border-neutral-300/80 px-6 py-3 transition-all animate-fadeIn flex-shrink-0">
                <div className="flex flex-wrap items-center justify-between gap-4 max-w-5xl mx-auto">
                  {/* Font Size Slider */}
                  <div className="flex items-center gap-2.5">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-700 min-w-[110px]">
                      <span className="font-serif text-sm font-bold">Aa</span>
                      <span>Font Size:</span>
                      <span className="font-mono text-emerald-700 font-bold bg-white px-1.5 py-0.5 rounded border border-neutral-300 text-[11px]">
                        {chatFontSize}px
                      </span>
                    </div>

                    <span className="text-[10px] text-neutral-400">11</span>
                    <input
                      type="range"
                      min="11"
                      max="22"
                      step="1"
                      value={chatFontSize}
                      onChange={(e) => setChatFontSize(Number(e.target.value))}
                      className="w-28 sm:w-36 accent-emerald-700 cursor-pointer"
                    />
                    <span className="text-[10px] text-neutral-400">22</span>

                    {/* Presets */}
                    <div className="hidden sm:flex items-center gap-1 ml-1">
                      {[12, 14, 16, 18].map((size) => (
                        <button
                          key={size}
                          onClick={() => setChatFontSize(size)}
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition ${
                            chatFontSize === size
                              ? "bg-neutral-900 text-white font-bold"
                              : "bg-white hover:bg-neutral-200 text-neutral-700 border border-neutral-300"
                          }`}
                        >
                          {size}px
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Chat Width Slider */}
                  <div className="flex items-center gap-2.5">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-700 min-w-[110px]">
                      <span>↔️</span>
                      <span>Chat Width:</span>
                      <span className="font-mono text-indigo-700 font-bold bg-white px-1.5 py-0.5 rounded border border-neutral-300 text-[11px]">
                        {chatWidth}px
                      </span>
                    </div>

                    <span className="text-[10px] text-neutral-400">480</span>
                    <input
                      type="range"
                      min="480"
                      max="1100"
                      step="20"
                      value={chatWidth}
                      onChange={(e) => setChatWidth(Number(e.target.value))}
                      className="w-28 sm:w-40 accent-indigo-600 cursor-pointer"
                    />
                    <span className="text-[10px] text-neutral-400">1100</span>

                    {/* Presets */}
                    <div className="hidden sm:flex items-center gap-1 ml-1">
                      {[
                        { label: "Compact", width: 560 },
                        { label: "Standard", width: 720 },
                        { label: "Wide", width: 960 },
                        { label: "Full", width: 1100 },
                      ].map((preset) => (
                        <button
                          key={preset.label}
                          onClick={() => setChatWidth(preset.width)}
                          className={`px-1.5 py-0.5 rounded text-[10px] transition ${
                            chatWidth === preset.width
                              ? "bg-neutral-900 text-white font-bold"
                              : "bg-white hover:bg-neutral-200 text-neutral-700 border border-neutral-300"
                          }`}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center gap-2 ml-auto">
                    <button
                      onClick={() => {
                        setChatFontSize(13);
                        setChatWidth(720);
                      }}
                      className="text-[11px] text-neutral-500 hover:text-neutral-800 underline cursor-pointer"
                    >
                      Reset
                    </button>
                    <button
                      onClick={() => setShowDisplaySettings(false)}
                      className="p-1 hover:bg-neutral-200 rounded text-neutral-500 text-xs"
                      title="Close sliders"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Model readiness: answers need Gemma running in Ollama on this machine */}
            {health && (health.ollama !== "up" || !health.models_ready) && (
              <div className="mx-6 mt-3 p-2.5 rounded-lg border border-rose-300 bg-rose-50 text-[11px] text-rose-800">
                {health.ollama === "up"
                  ? `Gemma is not ready: missing ${(health.missing_models || []).join(", ") || "model"}. Run the installer, or "ollama pull" the missing model.`
                  : "Gemma is not running. Start Ollama (\"ollama serve\"), then ask again."}
                <button onClick={refreshHealth} className="ml-2 underline">Check again</button>
              </div>
            )}

            {/* Message Thread */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
              <div
                className="mx-auto space-y-5 transition-all duration-150"
                style={{ maxWidth: `${chatWidth}px` }}
              >
                {messages.map((msg) => (
                  <div key={msg.id} className="flex gap-3">
                    {msg.sender === "user" ? (
                      <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center font-medium text-xs flex-shrink-0 mt-0.5">
                        P
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-amber-100 border border-amber-300 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs">🛡️</span>
                      </div>
                    )}

                    <div className="flex-1">
                      {msg.sender === "user" ? (
                        <div>
                          <div
                            className="bg-[#EFECE6] text-neutral-900 rounded-2xl rounded-tl-sm px-4 py-3 inline-block leading-relaxed"
                            style={{
                              fontSize: `${chatFontSize}px`,
                              lineHeight: `${Math.round(chatFontSize * 1.55)}px`,
                              maxWidth: `${Math.min(chatWidth - 60, 680)}px`,
                            }}
                          >
                            {msg.text}
                          </div>
                          <div className="text-[10px] text-neutral-400 mt-1 pl-1">{msg.timestamp}</div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {msg.message && (
                            <p
                              className="text-neutral-800 font-medium"
                              style={{
                                fontSize: `${chatFontSize}px`,
                                lineHeight: `${Math.round(chatFontSize * 1.55)}px`,
                              }}
                            >
                              {msg.message}
                            </p>
                          )}

                          {/* Claims rendering with Tier & Distortion Badges */}
                          {msg.claims && msg.claims.map((claim, ci) => (
                            <div key={ci} className="space-y-2">
                              <div className="flex items-center gap-2">
                                <TierBadge tier={claim.kind} />
                                {claim.distortion && <DistortionBadge distortion={claim.distortion} />}
                              </div>
                              <p
                                className="text-neutral-700 leading-relaxed"
                                style={{
                                  fontSize: `${chatFontSize}px`,
                                  lineHeight: `${Math.round(chatFontSize * 1.55)}px`,
                                }}
                              >
                                {claim.text}
                              </p>

                              {/* Citation Snippets - Rule 2 exact source quote */}
                              {claim.citations && claim.citations.map((cite, k) => (
                                <div
                                  key={k}
                                  onClick={() => handleSelectClause(cite)}
                                  className="bg-white rounded-lg border border-neutral-200 hover:border-amber-400 p-3 shadow-xs transition cursor-pointer group"
                                >
                                  <div className="flex items-center justify-between text-xs font-medium text-neutral-800 mb-1">
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-rose-500 font-bold text-[10px]">
                                        {fileTypeLabel(docDetail?.summary?.mime)}
                                      </span>
                                      <span className="underline decoration-neutral-300 group-hover:decoration-neutral-800">
                                        {docDetail?.summary?.filename || "document"}
                                      </span>
                                      <span className="text-neutral-400">
                                        · {citationLocation(cite)} · {cite.clause_id}
                                      </span>
                                    </div>
                                    <span title="Open in the document"><Icons.ExternalLink /></span>
                                  </div>
                                  <div
                                    className="text-neutral-600 bg-neutral-50 border-l-2 border-amber-400 pl-2.5 py-1.5 italic font-serif"
                                    style={{
                                      fontSize: `${Math.max(11, chatFontSize - 1)}px`,
                                      lineHeight: `${Math.round(chatFontSize * 1.45)}px`,
                                    }}
                                  >
                                    Quote: "{cite.quote}"
                                  </div>
                                </div>
                              ))}
                            </div>
                          ))}

                          {/* Not in the document: say so, then show the closest clauses (never as an answer) */}
                          {msg.notFoundNote && (
                            <p className="text-[11px] text-neutral-500 italic">{msg.notFoundNote}</p>
                          )}
                          {msg.clarifyingQuestion && (
                            <p className="text-xs text-neutral-800 font-medium">{msg.clarifyingQuestion}</p>
                          )}
                          {msg.relatedClauses && msg.relatedClauses.length > 0 && (
                            <div className="space-y-1.5">
                              <div className="text-[10px] uppercase tracking-wide text-neutral-400">
                                {msg.status === "NOT_IN_DOCUMENT" ? "Closest clauses (they do not answer it)" : "Related clauses"}
                              </div>
                              {msg.relatedClauses.map((cite, k) => (
                                <button
                                  key={k}
                                  onClick={() => handleSelectClause(cite)}
                                  className="w-full text-left bg-white rounded-md border border-neutral-200 hover:border-amber-400 px-2.5 py-1.5 text-[11px] text-neutral-600 transition"
                                >
                                  <span className="text-neutral-400">{citationLocation(cite)} · {cite.clause_id} · </span>
                                  <span className="italic font-serif">{cite.quote.length > 160 ? `${cite.quote.slice(0, 160)}…` : cite.quote}</span>
                                </button>
                              ))}
                            </div>
                          )}
                          {msg.status === "ERROR" && (
                            <div className="p-2.5 rounded-md border border-rose-300 bg-rose-50 text-[11px] text-rose-800">
                              No answer was produced, so nothing is shown from the document.
                            </div>
                          )}

                          {/* Ethical Refusal / Escalation Card */}
                          {msg.escalation && (
                            <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg space-y-1 text-xs text-amber-900">
                              <div className="font-bold flex items-center gap-1.5">
                                <span>⚖️</span>
                                <span>Consultation Escalation: {msg.escalation.who}</span>
                              </div>
                              <p className="text-[11px] text-amber-800">{msg.escalation.why}</p>
                              {msg.escalation.free_help && (
                                <p className="text-[10px] text-amber-700 italic">Free Help: {msg.escalation.free_help}</p>
                              )}
                            </div>
                          )}

                          {/* Rule 5: Persistent Disclaimer Footer */}
                          <div className="flex items-center gap-2 text-[11px] text-neutral-500 pt-1">
                            <Icons.AlertCircle />
                            <span>{msg.disclaimer}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isSubmitting && (
                  <div className="flex items-center gap-2 text-xs text-neutral-500 pl-10">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Gemma is reading the document and checking every quote…
                  </div>
                )}

                {/* Starter questions for the detected document type */}
                <div className="pt-2 space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map((prompt, i) => (
                      <button
                        key={i}
                        onClick={() => handleSendMessage(prompt)}
                        disabled={isSubmitting}
                        className="px-3 py-1.5 rounded-full bg-white hover:bg-neutral-100 border border-neutral-200 text-neutral-700 text-xs transition flex items-center gap-1.5 shadow-2xs"
                      >
                        <span>{prompt}</span>
                        <span className="text-neutral-400 text-xs">→</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Input Box */}
            <div className="p-4 bg-white/60 border-t border-neutral-200 flex-shrink-0">
              <div
                className="mx-auto bg-white rounded-2xl border border-neutral-300 p-2 shadow-xs focus-within:border-emerald-600 focus-within:ring-1 focus-within:ring-emerald-600 transition"
                style={{ maxWidth: `${chatWidth}px` }}
              >
                <div className="flex items-center gap-2 px-1">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-neutral-100"
                    title="Upload document (POST /documents)"
                  >
                    <Icons.Attachment />
                  </button>
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                    placeholder="Ask anything about this document. Answers cite the exact lines."
                    disabled={isSubmitting}
                    className="flex-1 bg-transparent border-none text-xs focus:outline-none text-neutral-800 placeholder-neutral-400"
                  />
                  <button
                    onClick={() => handleSendMessage()}
                    disabled={isSubmitting}
                    className="w-7 h-7 rounded-full bg-[#1C4D2E] hover:bg-[#153a23] text-white flex items-center justify-center transition shadow-xs flex-shrink-0 disabled:opacity-50"
                  >
                    <Icons.ArrowUp />
                  </button>
                </div>

                <div className="mt-2 pt-2 border-t border-neutral-100 flex items-center justify-between text-[11px] text-neutral-600 px-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-rose-500 font-bold text-[9px]">{fileTypeLabel(docDetail?.summary?.mime)}</span>
                    <span>{docDetail?.summary?.filename || ""}</span>
                    {docDetail && <span className="text-neutral-400">· {docDetail.summary.pages} pages</span>}
                  </div>
                  <button
                    onClick={handleDeleteDocument}
                    title="Purge Document"
                    className="text-neutral-400 hover:text-rose-600 text-sm"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* ── COLUMN 4: DOCUMENT METADATA & INGESTION INTELLIGENCE ── */}
          {showRightSidebar && (
            <DocumentMetadataPanel
              documentId={documentId}
              sourceFocus={sourceFocus}
              docDetail={docDetail}
              reportData={reportData}
              currentPage={currentPage}
              activeCitation={activeCitation}
              zoomLevel={zoomLevel}
              onPageChange={setCurrentPage}
              onZoomChange={setZoomLevel}
              onRunAnalysis={() => setIsAnalysisOpen(true)}
              onOpenScenarios={() => setIsScenariosOpen(true)}
              onOpenBrief={() => setIsLegalLibraryOpen(true)}
              onDeleteDocument={handleDeleteDocument}
              onCollapse={() => setShowRightSidebar(false)}
            />
          )}
        </>
      )}

      {/* ── SHARED MODALS FOR ALL 26 ENDPOINTS ──────────────────────── */}
      <PasteTextModal
        isOpen={isPasteTextOpen}
        onClose={() => setIsPasteTextOpen(false)}
        onDocumentCreated={handleDocumentCreated}
      />

      <AnalysisProgressModal
        isOpen={isAnalysisOpen}
        onClose={() => setIsAnalysisOpen(false)}
        documentId={documentId}
        onAnalysisComplete={(rep) => setReportData(rep)}
      />

      <ScenariosModal
        isOpen={isScenariosOpen}
        onClose={() => setIsScenariosOpen(false)}
        documentId={documentId}
        docType={docType}
      />

      <LegalLibraryModal
        isOpen={isLegalLibraryOpen}
        onClose={() => setIsLegalLibraryOpen(false)}
        documentId={documentId}
      />

      <TrustModal
        isOpen={isTrustOpen}
        initialTab={trustInitialTab}
        onClose={() => setIsTrustOpen(false)}
        onPanicWipe={handlePanicWipe}
      />

      {/* Hidden File Input for Sidebar and Upload Actions */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf,.txt,.docx"
      />

    </div>
  );
}
