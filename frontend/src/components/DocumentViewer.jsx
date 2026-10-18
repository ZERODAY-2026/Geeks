import React, { useRef, useEffect } from "react";
import { documentFileUrl } from "../api/client";
import { citationLocation, fileTypeLabel } from "../lib/format";

/**
 * Source viewer. Shows the extracted page text and highlights the cited characters exactly
 * (char_start/char_end are offsets into the whole document; subtract the page's char_start).
 * Quotes are rendered only from the document text itself, never from the model.
 *
 * "Open original" opens the uploaded file: a PDF opens in the browser's built-in viewer at the cited page
 * (#page=N, works offline); a DOCX or TXT downloads or opens as is.
 */
export default function DocumentViewer({
  documentId,
  mime,
  filename,
  currentPage,
  totalPages = 1,
  pageData,
  activeCitation,
  zoomLevel = 100,
  onPageChange,
  onZoomChange,
}) {
  const highlightRef = useRef(null);
  const citationOnPage = activeCitation && activeCitation.page === currentPage;

  useEffect(() => {
    if (citationOnPage && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeCitation, currentPage, citationOnPage]);

  const openOriginal = () => {
    if (!documentId) return;
    const page = mime === "application/pdf" ? currentPage : null;
    window.open(documentFileUrl(documentId, page), "_blank", "noopener");
  };

  const renderPageContent = () => {
    if (!pageData) {
      return <div className="text-neutral-400 font-sans text-xs text-center pt-10">No text on this page.</div>;
    }
    const { text, char_start: pageCharStart } = pageData;
    if (!citationOnPage) {
      return <div className="whitespace-pre-wrap font-serif text-[11px] leading-relaxed text-neutral-800">{text}</div>;
    }
    const localStart = Math.max(0, activeCitation.char_start - pageCharStart);
    const localEnd = Math.min(text.length, Math.max(localStart, activeCitation.char_end - pageCharStart));
    return (
      <div className="whitespace-pre-wrap font-serif text-[11px] leading-relaxed text-neutral-800">
        <span>{text.slice(0, localStart)}</span>
        <mark
          ref={highlightRef}
          className="bg-amber-100 text-amber-950 px-0.5 rounded border border-amber-300/80 font-medium inline"
        >
          {text.slice(localStart, localEnd)}
        </mark>
        <span>{text.slice(localEnd)}</span>
      </div>
    );
  };

  return (
    <section className="w-full bg-neutral-100 flex flex-col flex-1 overflow-hidden">
      {/* Toolbar */}
      <div className="h-12 border-b border-neutral-200 px-3 flex items-center justify-between bg-white text-xs text-neutral-600 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            className="p-1 hover:bg-neutral-100 rounded text-neutral-500"
            title="Previous page"
          >
            ‹
          </button>
          <span className="font-medium text-neutral-800 font-mono">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            className="p-1 hover:bg-neutral-100 rounded text-neutral-500"
            title="Next page"
          >
            ›
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button onClick={() => onZoomChange(Math.max(60, zoomLevel - 10))} className="px-1.5 hover:bg-neutral-100 rounded font-mono" title="Zoom out">
            -
          </button>
          <span className="text-[11px] font-mono text-neutral-700">{zoomLevel}%</span>
          <button onClick={() => onZoomChange(Math.min(180, zoomLevel + 10))} className="px-1.5 hover:bg-neutral-100 rounded font-mono" title="Zoom in">
            +
          </button>
        </div>

        <button
          onClick={openOriginal}
          disabled={!documentId}
          className="px-2 py-1 rounded border border-neutral-300 hover:bg-neutral-50 text-[11px] font-medium text-neutral-700 disabled:opacity-40"
          title={mime === "application/pdf" ? `Open the original PDF at page ${currentPage}` : `Open the original ${fileTypeLabel(mime)}`}
        >
          Open original {fileTypeLabel(mime)}
        </button>
      </div>

      {/* Where the highlighted citation is */}
      {activeCitation && (
        <div className="px-3 py-1.5 bg-amber-50 border-b border-amber-200 text-[11px] text-amber-900 flex items-center justify-between">
          <span>
            Cited: {citationLocation(activeCitation)}
            {activeCitation.clause_id ? ` · ${activeCitation.clause_id}` : ""}
          </span>
          {!citationOnPage && (
            <button onClick={() => onPageChange(activeCitation.page)} className="underline">
              Go to page {activeCitation.page}
            </button>
          )}
        </div>
      )}

      {/* Page */}
      <div className="flex-1 overflow-y-auto p-5 flex justify-center bg-neutral-200/50">
        <div
          className="w-full max-w-[390px] min-h-[500px] bg-white rounded shadow-md border border-neutral-200 p-6 text-neutral-900 flex flex-col justify-between font-serif text-[11px] leading-relaxed"
          style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
          title={filename || ""}
        >
          {renderPageContent()}
          <div className="text-center text-xs text-neutral-400 font-sans pt-6">{currentPage}</div>
        </div>
      </div>
    </section>
  );
}
