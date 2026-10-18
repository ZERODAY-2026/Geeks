// Small display helpers shared by the chat and the source viewer.

const MIME_LABEL = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "text/plain": "TXT",
};

export function fileTypeLabel(mime) {
  return MIME_LABEL[mime] || "DOC";
}

/** "p. 3, lines 12-14" from a citation; lines are counted within the page. */
export function citationLocation(cite) {
  const parts = [`p. ${cite.page}`];
  if (cite.line_start) {
    parts.push(
      cite.line_end && cite.line_end !== cite.line_start ? `lines ${cite.line_start}-${cite.line_end}` : `line ${cite.line_start}`
    );
  }
  return parts.join(", ");
}
