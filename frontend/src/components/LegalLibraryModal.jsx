import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";

/**
 * Maps to Endpoints 14, 15, 16, 17:
 * - 14: GET /api/v1/documents/{id}/statutes
 * - 15: GET /api/v1/documents/{id}/brief
 * - 16: GET /api/v1/packs
 * - 17: GET /api/v1/packs/{pack_id}
 */
export default function LegalLibraryModal({ isOpen, onClose, documentId }) {
  const [tab, setTab] = useState("brief");
  const [brief, setBrief] = useState(null);
  const [statutes, setStatutes] = useState([]);
  const [packs, setPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    if (tab === "brief" && documentId) {
      setLoading(true);
      // Endpoint 15: GET /api/v1/documents/{id}/brief
      ApiClient.getBrief(documentId, "json")
        .then(setBrief)
        .catch(console.error)
        .finally(() => setLoading(false));
    } else if (tab === "statutes" && documentId) {
      setLoading(true);
      // Endpoint 14: GET /api/v1/documents/{id}/statutes
      ApiClient.getStatutes(documentId)
        .then(setStatutes)
        .catch(console.error)
        .finally(() => setLoading(false));
    } else if (tab === "packs") {
      setLoading(true);
      // Endpoint 16: GET /api/v1/packs
      ApiClient.getPacks()
        .then((res) => {
          setPacks(res || []);
          if (res && res.length > 0) {
            // Endpoint 17: GET /api/v1/packs/{pack_id}
            ApiClient.getPack(res[0].pack_id).then(setSelectedPack);
          }
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [isOpen, tab, documentId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="bg-[#1C1E22] border border-neutral-700/80 rounded-xl shadow-2xl max-w-2xl w-full text-neutral-200 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-neutral-800 flex items-center justify-between bg-[#16181B]">
          <div>
            <h3 className="font-semibold text-white text-sm">Legal Library & Consultation Brief</h3>
            <p className="text-[11px] text-neutral-400">Endpoints 14–17: Briefs, Indian Statutes, and Checklist Packs</p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-6 px-5 border-b border-neutral-800 text-xs font-medium bg-[#18191D]">
          <button
            onClick={() => setTab("brief")}
            className={`py-3 border-b-2 transition ${
              tab === "brief" ? "border-emerald-500 text-white" : "border-transparent text-neutral-400 hover:text-neutral-200"
            }`}
          >
            Pre-Lawyer Brief (GET /brief)
          </button>
          <button
            onClick={() => setTab("statutes")}
            className={`py-3 border-b-2 transition ${
              tab === "statutes" ? "border-emerald-500 text-white" : "border-transparent text-neutral-400 hover:text-neutral-200"
            }`}
          >
            Indian Statutes (GET /statutes)
          </button>
          <button
            onClick={() => setTab("packs")}
            className={`py-3 border-b-2 transition ${
              tab === "packs" ? "border-emerald-500 text-white" : "border-transparent text-neutral-400 hover:text-neutral-200"
            }`}
          >
            Checklist Packs (GET /packs)
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs">
          {loading && <div className="text-neutral-500 text-center py-6">Loading from local database...</div>}

          {/* TAB 1: Pre-Lawyer Consultation Brief */}
          {tab === "brief" && !loading && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-white">1-Page Pre-Lawyer Consultation Summary</h4>
                  <p className="text-[11px] text-neutral-400">Designed to reduce consultation billable hours</p>
                </div>
                <button
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(brief, null, 2)], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `LexiShield_Brief_${documentId}.json`;
                    a.click();
                  }}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition"
                >
                  Export Brief (JSON)
                </button>
              </div>

              {brief ? (
                <div className="bg-[#16181B] border border-neutral-800 rounded-lg p-4 space-y-3 font-sans">
                  <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
                    <span className="font-bold text-white uppercase">{brief.doc_type} Agreement Summary</span>
                    <span className="text-[10px] text-emerald-400 font-mono">
                      {brief.jurisdiction?.state}, {brief.jurisdiction?.country}
                    </span>
                  </div>

                  {/* Top Issues */}
                  <div>
                    <h5 className="font-semibold text-amber-400 mb-1">Key Escalations & Ambiguities</h5>
                    <div className="space-y-1.5">
                      {brief.top_issues?.map((issue, idx) => (
                        <div key={idx} className="p-2 bg-neutral-900 rounded border border-neutral-800 text-[11px]">
                          <span className="font-semibold text-white">{issue.title}: </span>
                          <span className="text-neutral-300">{issue.plain_explanation?.text || issue.explanation_withheld_reason}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Questions for Lawyer */}
                  {brief.questions_for_lawyer?.length > 0 && (
                    <div>
                      <h5 className="font-semibold text-emerald-400 mb-1">Recommended Questions to Ask Your Lawyer</h5>
                      <ul className="list-disc pl-4 space-y-1 text-neutral-300 text-[11px]">
                        {brief.questions_for_lawyer.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-neutral-500 text-center py-6">No brief generated yet.</div>
              )}
            </div>
          )}

          {/* TAB 2: Indian Statutes Excerpts */}
          {tab === "statutes" && !loading && (
            <div className="space-y-3">
              <h4 className="font-semibold text-white">Relevant Statutory Provisions (Open India Law)</h4>
              <div className="space-y-2">
                {statutes.map((st, i) => (
                  <div key={i} className="p-3 bg-[#16181B] border border-neutral-800 rounded-lg space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-amber-300">{st.title || st.act}</span>
                      <span className="text-[10px] text-neutral-500 font-mono">{st.section}</span>
                    </div>
                    <p className="text-neutral-300 text-[11px] leading-relaxed italic">{st.excerpt || st.summary}</p>
                    <p className="text-[10px] text-neutral-500">Applicable jurisdiction: {st.jurisdiction || "India (Central)"}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: Checklist Packs */}
          {tab === "packs" && !loading && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                {packs.map((p) => (
                  <button
                    key={p.pack_id}
                    onClick={() => ApiClient.getPack(p.pack_id).then(setSelectedPack)}
                    className={`p-3 rounded-lg border text-left transition ${
                      selectedPack?.pack_id === p.pack_id
                        ? "bg-emerald-950/40 border-emerald-500 text-white"
                        : "bg-[#222429] border-neutral-800 text-neutral-300 hover:border-neutral-700"
                    }`}
                  >
                    <p className="font-bold text-white capitalize">{p.pack_id}</p>
                    <p className="text-[10px] text-neutral-400">Depth: {p.depth} · Version: {p.version}</p>
                  </button>
                ))}
              </div>

              {selectedPack && (
                <div className="p-3.5 bg-[#16181B] border border-neutral-800 rounded-lg space-y-2">
                  <h5 className="font-semibold text-white text-xs">Included Hypotheses ({selectedPack.pack_id})</h5>
                  <div className="space-y-1">
                    {selectedPack.topics?.map((topic, i) => (
                      <div key={i} className="p-1.5 rounded bg-neutral-900 border border-neutral-800 text-[11px] text-neutral-300">
                        {topic.title}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#16181B] border-t border-neutral-800 flex justify-between items-center text-[11px] text-neutral-400">
          <span>Preliminary information, not legal advice.</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
