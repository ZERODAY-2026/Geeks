import React from "react";

/**
 * Contract Rule 3:
 * Show the tier badge (STATED / INTERPRETATION / NOT_FOUND / ASK_A_LAWYER)
 * and the distortion badge (PASS / FAIL / NA) on every card and claim.
 */

export function TierBadge({ tier }) {
  const styles = {
    STATED: "bg-emerald-100 text-emerald-800 border-emerald-300",
    INTERPRETATION: "bg-blue-100 text-blue-800 border-blue-300",
    NOT_FOUND: "bg-neutral-100 text-neutral-700 border-neutral-300",
    ASK_A_LAWYER: "bg-amber-100 text-amber-800 border-amber-300",
    CONCERN: "bg-rose-100 text-rose-800 border-rose-300",
  };

  const style = styles[tier] || "bg-neutral-100 text-neutral-600 border-neutral-200";

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border tracking-wide uppercase ${style}`}
    >
      {tier}
    </span>
  );
}

export function DistortionBadge({ distortion }) {
  if (!distortion || distortion === "NA") return null;

  if (distortion === "PASS") {
    return (
      <span
        title="Distortion check passed: verbatim verified against document"
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200"
      >
        <svg className="w-2.5 h-2.5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
        <span>VERIFIED</span>
      </span>
    );
  }

  return (
    <span
      title="Distortion check failed: possible misgrounding or mismatch"
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-200"
    >
      <svg className="w-2.5 h-2.5 text-rose-600" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
      <span>DISTORTION</span>
    </span>
  );
}
