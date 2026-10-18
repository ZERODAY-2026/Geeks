import React, { useState } from "react";
import { ApiClient } from "../api/client";

/**
 * Maps to Endpoint 2: POST /api/v1/documents/text
 */
export default function PasteTextModal({ isOpen, onClose, onDocumentCreated }) {
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("draft_agreement.txt");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const summary = await ApiClient.uploadText(text, filename);
      onDocumentCreated(summary);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to parse text document");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="bg-[#1C1E22] border border-neutral-700/80 rounded-xl shadow-2xl max-w-lg w-full text-neutral-200 overflow-hidden">
        <div className="p-4 border-b border-neutral-800 flex items-center justify-between bg-[#16181B]">
          <div>
            <h3 className="font-semibold text-white text-sm">Paste Document Text</h3>
            <p className="text-[11px] text-neutral-400">Endpoint: POST /api/v1/documents/text</p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-2.5 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
              {error}
            </div>
          )}

          <div>
            <label className="block text-neutral-300 font-medium mb-1">Document Identifier</label>
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full bg-[#131417] border border-neutral-700 rounded-lg px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-emerald-500"
              placeholder="filename.txt"
              required
            />
          </div>

          <div>
            <label className="block text-neutral-300 font-medium mb-1">
              Agreement Clauses / Plain Text
            </label>
            <textarea
              rows={8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste contract clauses here (e.g. 12. SECURITY DEPOSIT... 13. LOCK-IN PERIOD...)"
              className="w-full bg-[#131417] border border-neutral-700 rounded-lg p-3 text-white font-serif text-xs leading-relaxed focus:outline-none focus:border-emerald-500"
              required
            />
            <p className="text-[11px] text-neutral-400 mt-1">
              Encrypted in RAM only. Zero bytes leave your device.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-neutral-800">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !text.trim()}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
            >
              {isSubmitting ? "Ingesting..." : "Ingest & Segment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
