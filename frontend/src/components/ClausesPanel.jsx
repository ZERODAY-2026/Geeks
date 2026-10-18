import React from "react";
import { TierBadge, DistortionBadge } from "./Badges";

const STATUS_BADGE = {
  ENTAILED: { label: "Stated", cls: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  CONTRADICTED: { label: "States the opposite", cls: "bg-rose-100 text-rose-800 border-rose-300" },
  UNCLEAR: { label: "Unclear", cls: "bg-neutral-100 text-neutral-700 border-neutral-300" },
  NOT_MENTIONED: { label: "Document silent", cls: "bg-amber-200/70 text-amber-900 border-amber-300" },
};

/**
 * Contract Rule 4: Never hide NOT_MENTIONED checklist items.
 * Contract Rule 3: Display tier badges and distortion badges.
 */
export default function ClausesPanel({
  clauses = [],
  cards = [],
  checklist = [],
  onSelectClause,
}) {
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-4">
      {/* Checklist Section including NOT_MENTIONED items */}
      <div className="space-y-2">
        <h4 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
          Checklist Analysis
        </h4>
        <div className="space-y-1.5">
          {checklist.length === 0 && (
            <p className="text-[11px] text-neutral-500">Run the analysis to check this document against its checklist.</p>
          )}
          {checklist.map((item, idx) => {
            const isSilent = item.status === "NOT_MENTIONED";
            const badge = STATUS_BADGE[item.status] || STATUS_BADGE.UNCLEAR;
            const evidence = item.evidence?.[0];
            return (
              <div
                key={idx}
                onClick={() => evidence && onSelectClause(evidence)}
                className={`p-2.5 rounded-lg border text-xs transition ${evidence ? "cursor-pointer" : ""} ${
                  isSilent
                    ? "bg-amber-50/70 border-amber-200 text-neutral-800"
                    : "bg-white border-neutral-200 hover:border-neutral-300"
                }`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="font-medium text-neutral-900 truncate">{item.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border uppercase ${badge.cls}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-[11px] text-neutral-600 leading-snug">
                  {item.note || item.hypothesis}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Extracted Document Clauses */}
      <div className="space-y-2 pt-2 border-t border-neutral-200">
        <h4 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
          Identified Clauses ({clauses.length})
        </h4>
        <div className="space-y-1.5">
          {clauses.map((clause) => (
            <div
              key={clause.id}
              onClick={() => onSelectClause(clause)}
              className="p-2.5 rounded-lg bg-white border border-neutral-200 hover:border-amber-400 hover:shadow-xs transition cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-neutral-900 group-hover:text-amber-800 text-xs">
                  {clause.number ? `Clause ${clause.number}` : clause.id}
                </span>
                <span className="text-[10px] text-neutral-400 font-mono">
                  Page {clause.page_start}
                </span>
              </div>
              <p className="font-medium text-[11px] text-neutral-700 mb-1">
                {clause.heading}
              </p>
              <p className="text-[11px] text-neutral-500 line-clamp-2 leading-relaxed">
                {clause.text}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Cards from Triage */}
      {cards.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-neutral-200">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
            Triage Cards ({cards.length})
          </h4>
          <div className="space-y-2">
            {cards.map((card) => (
              <div
                key={card.id}
                onClick={() => card.source && onSelectClause(card.source)}
                className={`p-2.5 rounded-lg bg-white border border-neutral-200 hover:border-amber-400 transition space-y-1.5 ${
                  card.source ? "cursor-pointer" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="font-semibold text-neutral-900 text-xs">{card.title}</span>
                  <div className="flex items-center gap-1">
                    <TierBadge tier={card.tier} />
                    {card.plain_explanation?.distortion && (
                      <DistortionBadge distortion={card.plain_explanation.distortion} />
                    )}
                  </div>
                </div>

                {card.plain_explanation ? (
                  <p className="text-[11px] text-neutral-600 leading-relaxed">
                    {card.plain_explanation.text}
                  </p>
                ) : (
                  <div className="p-1.5 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-800">
                    <span className="font-semibold">Explanation withheld: </span>
                    {card.explanation_withheld_reason || "Check source quote."}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
