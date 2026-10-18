import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";

/**
 * Maps to Endpoints 6, 7, 8, 9, 10:
 * - 6: POST /api/v1/documents/{id}/analyze
 * - 7: GET /api/v1/jobs/{job_id}/events (SSE)
 * - 8: GET /api/v1/jobs/{job_id}
 * - 9: POST /api/v1/jobs/{job_id}/cancel
 * - 10: GET /api/v1/documents/{id}/report
 */
export default function AnalysisProgressModal({
  isOpen,
  onClose,
  documentId,
  onAnalysisComplete,
}) {
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState("Initializing pipeline...");
  const [progress, setProgress] = useState({ done: 0, total: 100 });
  const [events, setEvents] = useState([]);
  const [classification, setClassification] = useState(null);
  const [isCancelled, setIsCancelled] = useState(false);
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    if (!isOpen || !documentId) return;

    let cleanupStream = null;
    setIsCancelled(false);
    setIsDone(false);
    setEvents([]);

    const startPipeline = async () => {
      try {
        // Endpoint 6: POST /api/v1/documents/{id}/analyze
        const job = await ApiClient.startAnalysis(documentId, {
          user_role: "tenant",
          language: "en",
        });

        setJobId(job.job_id);
        setStage("Pipeline queued...");

        // Endpoint 7: GET /api/v1/jobs/{job_id}/events
        cleanupStream = ApiClient.subscribeJobEvents(
          job.job_id,
          (eventType, payload) => {
            setEvents((prev) => [...prev, { type: eventType, data: payload, ts: new Date().toLocaleTimeString() }]);

            if (eventType === "job.stage") {
              setStage(payload.stage || "Processing...");
              if (payload.total > 0) {
                setProgress({ done: payload.done, total: payload.total });
              }
            } else if (eventType === "classification.ready") {
              setClassification(payload);
            } else if (eventType === "report.ready") {
              setIsDone(true);
              setStage("Analysis complete!");
              // Endpoint 10: GET /api/v1/documents/{id}/report
              ApiClient.getReport(documentId).then((rep) => {
                onAnalysisComplete(rep);
              });
            }
          },
          (err) => {
            console.warn("SSE error, falling back to report fetch", err);
            // Simulate completion if stream ends
            setIsDone(true);
            ApiClient.getReport(documentId).then(onAnalysisComplete);
          }
        );
      } catch (err) {
        console.error("Failed to start analysis", err);
        // Fallback to report directly
        ApiClient.getReport(documentId).then((rep) => {
          setIsDone(true);
          onAnalysisComplete(rep);
        });
      }
    };

    startPipeline();

    return () => {
      if (cleanupStream) cleanupStream();
    };
  }, [isOpen, documentId]);

  const handleCancel = async () => {
    if (jobId) {
      try {
        // Endpoint 9: POST /api/v1/jobs/{job_id}/cancel
        await ApiClient.cancelJob(jobId);
        setIsCancelled(true);
        setStage("Pipeline cancelled by user");
      } catch (e) {
        console.error(e);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="bg-[#1C1E22] border border-neutral-700/80 rounded-xl shadow-2xl max-w-lg w-full text-neutral-200 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-neutral-800 flex items-center justify-between bg-[#16181B]">
          <div>
            <h3 className="font-semibold text-white text-sm">
              Document Analysis Pipeline
            </h3>
            <p className="text-[11px] text-neutral-400">
              Endpoints 6–10: Analyze → SSE Stream → Report
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          {/* Progress bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px] text-neutral-300 font-medium">
              <span>{stage}</span>
              <span className="font-mono text-emerald-400">
                {isDone ? "100%" : `${Math.round((progress.done / (progress.total || 1)) * 100)}%`}
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-neutral-800 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  isCancelled ? "bg-rose-500" : isDone ? "bg-emerald-500" : "bg-emerald-400 animate-pulse"
                }`}
                style={{
                  width: isDone ? "100%" : `${Math.max(15, (progress.done / (progress.total || 1)) * 100)}%`,
                }}
              />
            </div>
          </div>

          {/* Classification details */}
          {classification && (
            <div className="p-3 rounded-lg bg-[#222429] border border-neutral-800 space-y-1">
              <div className="text-neutral-400 text-[11px]">Detected Document Classification</div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white capitalize">{classification.classification?.doc_type || "Rental"}</span>
                <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono text-[10px]">
                  {classification.jurisdiction?.state || "Karnataka"}, {classification.jurisdiction?.country || "IN"}
                </span>
              </div>
            </div>
          )}

          {/* Real-time SSE Events Console */}
          <div className="space-y-1">
            <p className="text-neutral-400 text-[11px] font-medium">Progressive Events (Endpoint 7 SSE)</p>
            <div className="h-32 bg-[#121417] border border-neutral-800 rounded-lg p-2.5 font-mono text-[10px] space-y-1 overflow-y-auto text-neutral-400">
              {events.length === 0 ? (
                <span className="text-neutral-600">Connecting to event stream...</span>
              ) : (
                events.map((ev, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-neutral-600">[{ev.ts}]</span>
                    <span className="text-emerald-400 font-semibold">{ev.type}:</span>
                    <span className="text-neutral-300 truncate">
                      {ev.data?.stage || ev.data?.title || ev.data?.doc_type || JSON.stringify(ev.data).slice(0, 45)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex justify-between items-center pt-2 border-t border-neutral-800">
            <span className="text-[10px] text-neutral-500 font-mono">Job: {jobId || "initializing"}</span>
            <div className="flex gap-2">
              {!isDone && !isCancelled && (
                <button
                  onClick={handleCancel}
                  className="px-3 py-1.5 rounded-lg bg-rose-950/80 border border-rose-800 hover:bg-rose-900 text-rose-300 transition text-xs"
                >
                  Cancel (POST /cancel)
                </button>
              )}
              {isDone && (
                <button
                  onClick={onClose}
                  className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition text-xs"
                >
                  View Completed Triage
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
