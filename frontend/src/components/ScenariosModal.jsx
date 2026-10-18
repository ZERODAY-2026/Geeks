import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";

/**
 * Maps to Endpoints 12 & 13:
 * - 12: GET /api/v1/scenarios
 * - 13: POST /api/v1/documents/{id}/scenarios/{sid}/run
 */
export default function ScenariosModal({ isOpen, onClose, documentId, docType = null }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [months, setMonths] = useState(3);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // The scenario's own params_schema names its one numeric input (months_stayed or months_served), if any.
  const paramName = Object.keys(selectedScenario?.params_schema?.properties || {})[0] || null;
  const paramLabel = paramName ? selectedScenario.params_schema.properties[paramName].description || paramName : null;

  useEffect(() => {
    if (isOpen) {
      setResult(null);
      setError(null);
      ApiClient.getScenarios(docType && docType !== "unknown" ? docType : null)
        .then((data) => {
          setScenarios(data || []);
          setSelectedScenario(data && data.length > 0 ? data[0] : null);
        })
        .catch((e) => setError(e.message));
    }
  }, [isOpen, docType]);

  const handleRunScenario = async () => {
    if (!selectedScenario || !documentId) return;
    setIsRunning(true);
    setResult(null);
    setError(null);
    try {
      const params = paramName ? { [paramName]: Number(months) } : {};
      setResult(await ApiClient.runScenario(documentId, selectedScenario.scenario_id, params));
    } catch (e) {
      setError(e.code === "CONFLICT" ? `${e.message} (Run the full analysis first.)` : e.message);
    } finally {
      setIsRunning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="bg-[#1C1E22] border border-neutral-700/80 rounded-xl shadow-2xl max-w-2xl w-full text-neutral-200 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-neutral-800 flex items-center justify-between bg-[#16181B]">
          <div>
            <h3 className="font-semibold text-white text-sm">
              "What-If" Life Crisis Simulator
            </h3>
            <p className="text-[11px] text-neutral-400">
              Deterministic financial exposure & penalty calculation (Endpoints 12 & 13)
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
        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs">
          {/* Select Scenario */}
          <div>
            <label className="block text-neutral-300 font-medium mb-1.5">
              Select Scenario Template (GET /api/v1/scenarios)
            </label>
            <div className="grid grid-cols-2 gap-2">
              {scenarios.map((sc) => (
                <button
                  key={sc.scenario_id}
                  onClick={() => {
                    setSelectedScenario(sc);
                    setResult(null);
                  }}
                  className={`p-2.5 rounded-lg border text-left transition ${
                    selectedScenario?.scenario_id === sc.scenario_id
                      ? "bg-emerald-950/40 border-emerald-500 text-white"
                      : "bg-[#222429] border-neutral-800 hover:border-neutral-700 text-neutral-300"
                  }`}
                >
                  <p className="font-semibold text-xs text-white">{sc.title}</p>
                  <p className="text-[10px] text-neutral-400 line-clamp-1">{sc.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic Parameter Input */}
          <div className="p-3.5 rounded-lg bg-[#222429] border border-neutral-800 space-y-2">
            <h4 className="text-white font-medium">Scenario Parameters</h4>
            <div className="flex items-center gap-3">
              {paramName ? (
                <>
                  <label className="text-neutral-300">{paramLabel}</label>
                  <input
                    type="number"
                    min={0}
                    max={240}
                    value={months}
                    onChange={(e) => setMonths(e.target.value)}
                    className="w-20 bg-[#131417] border border-neutral-700 rounded px-2 py-1 text-white font-mono text-center"
                  />
                </>
              ) : (
                <span className="text-neutral-400">No input needed.</span>
              )}
              <button
                onClick={handleRunScenario}
                disabled={isRunning}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50 ml-auto"
              >
                {isRunning ? "Calculating..." : "Run Exposure Engine (POST /run)"}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-2.5 rounded-md border border-rose-800 bg-rose-950/60 text-rose-200 text-xs">{error}</div>
          )}
          {result?.exposure && !result.exposure.computable && (
            <div className="p-2.5 rounded-md border border-amber-800 bg-amber-950/50 text-amber-200 text-xs">
              No total is given, because the document does not state:{" "}
              {(result.exposure.missing_inputs || []).join("; ")}
            </div>
          )}

          {/* Results Display */}
          {result && (
            <div className="space-y-3 pt-2 border-t border-neutral-800 animate-in fade-in">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-white text-xs">{result.title} Result</h4>
                {result.exposure?.computable && (
                  <span className="px-2.5 py-1 rounded bg-amber-950 border border-amber-800 text-amber-300 font-mono font-bold">
                    From stated amounts: {result.exposure.currency || "INR"} {(result.exposure.total ?? 0).toLocaleString("en-IN")}
                  </span>
                )}
              </div>

              {/* Steps / Breakdown */}
              <div className="space-y-2">
                {result.steps?.map((step, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-[#16181B] border border-neutral-800 space-y-1">
                    <p className="text-neutral-300">{step.text}</p>
                    {step.citations?.map((c, ci) => (
                      <div key={ci} className="text-[10px] text-amber-400 font-mono bg-neutral-900/60 p-1.5 rounded border border-neutral-800">
                        Clause {c.clause_id} (Page {c.page}): "{c.quote}"
                      </div>
                    ))}
                  </div>
                ))}
              </div>

              {/* Silences / Missing Inputs */}
              {result.silences && result.silences.length > 0 && (
                <div className="p-2.5 rounded bg-amber-950/30 border border-amber-800 text-[11px] text-amber-300">
                  <span className="font-semibold">Document Silences Identified: </span>
                  {result.silences.join("; ")}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#16181B] border-t border-neutral-800 flex justify-between items-center text-[11px] text-neutral-400">
          <span>Preliminary calculations, not legal advice.</span>
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
