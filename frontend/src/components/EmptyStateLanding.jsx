import React, { useState, useRef } from "react";
import { ApiClient } from "../api/client";

/**
 * Empty State / Upload Landing Page
 * Maps to Endpoints:
 * - 1: POST /api/v1/documents (File Upload via Choose a file or Drag & Drop)
 * - 2: POST /api/v1/documents/text (Text Prompt / Raw Clause Input)
 * - 18: GET /api/v1/privacy/status (Top-right Offline Mode Pill)
 */
export default function EmptyStateLanding({
  onDocumentLoaded,
  onOpenTrustModal,
  privacyStatus,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [promptText, setPromptText] = useState("");
  const fileInputRef = useRef(null);

  // Endpoint 1: POST /api/v1/documents
  const handleFile = async (file) => {
    if (!file) return;
    setIsUploading(true);
    try {
      const summary = await ApiClient.uploadDocument(file);
      onDocumentLoaded(summary);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload document: " + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  // Endpoint 2: POST /api/v1/documents/text when user submits a prompt directly
  const handlePromptSubmit = async (e) => {
    e?.preventDefault();
    if (!promptText.trim() || isUploading) return;

    setIsUploading(true);
    try {
      const summary = await ApiClient.uploadText(
        promptText.trim(),
        "query_document.txt"
      );
      onDocumentLoaded(summary, promptText.trim());
    } catch (err) {
      console.error("Failed to ingest prompt", err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-between bg-[#F7F5F0] relative overflow-hidden select-none">
      
      {/* ── TOP HEADER (Offline Badge) ──────────────────────────────── */}
      <div className="h-16 px-8 flex items-center justify-end gap-3 z-10">
        <button
          onClick={onOpenTrustModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/80 border border-neutral-300 text-neutral-800 text-xs font-medium hover:bg-white shadow-2xs transition cursor-pointer"
        >
          <svg className="w-3.5 h-3.5 text-emerald-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 018 0v4" />
          </svg>
          <span className="font-semibold text-neutral-800">Offline Mode</span>
          <span className="text-neutral-500 text-[11px]">· No internet access</span>
        </button>

        <button
          onClick={onOpenTrustModal}
          className="p-1.5 hover:bg-neutral-200/60 rounded text-neutral-500 transition"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="5" r="1.5" />
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </div>

      {/* ── CENTER HERO & UPLOAD BOX ───────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 max-w-3xl mx-auto w-full -mt-4">
        
        {/* Eyebrow badge */}
        <div className="flex items-center gap-2 mb-4">
          <span className="w-2 h-2 rounded-full bg-emerald-600 shadow-[0_0_8px_rgba(5,150,105,0.6)]" />
          <span className="text-[11px] font-semibold tracking-widest uppercase text-neutral-600 font-mono">
            Zero-Egress Private Legal Triage Agent
          </span>
        </div>

        {/* Main Title (DM Serif Display style) */}
        <h1 className="text-5xl md:text-6xl text-center text-neutral-900 font-serif leading-[1.1] mb-5">
          Your document,
          <br />
          <em className="italic font-normal text-neutral-800">made simple.</em>
        </h1>

        {/* Subtitle */}
        <p className="text-center text-neutral-600 text-sm md:text-base max-w-lg mb-8 leading-relaxed font-sans font-light">
          Upload a legal document to get a clear, grounded analysis.
          <br />
          All answers are based only on your document with exact sources.
        </p>

        {/* Upload Container (Dashed Card) */}
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={`w-full max-w-2xl rounded-2xl border-2 border-dashed p-8 md:p-10 transition-all duration-200 flex flex-col items-center justify-center text-center ${
            isDragging
              ? "border-emerald-600 bg-emerald-50/50 scale-[1.01]"
              : "border-neutral-300 hover:border-neutral-400 bg-white/40"
          }`}
        >
          {/* File Icon */}
          <div className="w-12 h-12 rounded-full bg-neutral-200/80 flex items-center justify-center text-neutral-600 mb-3 shadow-2xs">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>

          <h3 className="font-serif font-bold text-neutral-900 text-lg mb-1">
            Upload a document
          </h3>

          <p className="text-xs text-neutral-500 mb-1">
            Supports PDF, DOCX, TXT <span className="mx-1">·</span> Encrypted in-memory only
          </p>

          <p className="text-[11px] text-neutral-400 mb-5">
            No files leave your device
          </p>

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFile(e.target.files?.[0])}
            className="hidden"
            accept=".pdf,.docx,.txt"
          />

          {/* Choose File Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#1C4D2E] hover:bg-[#153a23] text-white font-medium text-xs transition shadow-sm hover:shadow"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
            <span>{isUploading ? "Encrypting & Ingesting..." : "Choose a file"}</span>
          </button>
        </div>

        {/* Divider "or" */}
        <div className="w-full max-w-2xl flex items-center my-6">
          <div className="flex-1 h-px bg-neutral-300/80" />
          <span className="px-3 text-xs text-neutral-400 font-sans">or</span>
          <div className="flex-1 h-px bg-neutral-300/80" />
        </div>

        {/* Bottom Chat Prompt Pill */}
        <form
          onSubmit={handlePromptSubmit}
          className="w-full max-w-2xl bg-white rounded-full border border-neutral-300/90 shadow-sm p-1.5 pl-3 flex items-center gap-2 focus-within:border-emerald-700 focus-within:ring-1 focus-within:ring-emerald-700 transition"
        >
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-full hover:bg-neutral-100 transition"
            title="Attach document"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>

          <input
            type="text"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Ask anything about this document..."
            className="flex-1 bg-transparent border-none text-xs focus:outline-none text-neutral-800 placeholder-neutral-400"
          />

          <button
            type="submit"
            disabled={!promptText.trim() || isUploading}
            className="w-8 h-8 rounded-full bg-[#1C4D2E] hover:bg-[#153a23] text-white flex items-center justify-center transition shadow-xs disabled:opacity-40"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </form>

      </div>

      {/* Bottom spacer */}
      <div className="h-6" />

    </div>
  );
}
