"""Privacy status and receipts (Phases 1 and 4), checklist packs (Phase 2), evaluation summary (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ...models import (
    EgressGuardStatus,
    EvalSummary,
    PackInfo,
    PrivacyEvent,
    PrivacyReceipt,
    PrivacyStatus,
    ReceiptRequest,
    TopicInfo,
)
from ...packs import Pack, all_packs
from ...trust import egress_guard, temp_sentinel
from ..errors import LexiError, NotImplementedYet, problem_responses

router = APIRouter()


@router.get("/privacy/status", response_model=PrivacyStatus, tags=["privacy"])
async def privacy_status(request: Request) -> PrivacyStatus:
    st = egress_guard.status()
    return PrivacyStatus(
        egress_guard=EgressGuardStatus(
            active=st["active"], allowed_hosts=st["allowed_hosts"], blocked_attempts=st["blocked_attempts"]
        ),
        network_mode="host-loopback",
        temp_files_created=temp_sentinel.count(),
        sessions=len(request.app.state.vault),
        retention_ttl_s=request.app.state.settings.privacy.session_ttl_s,
    )


@router.get("/privacy/events", response_model=list[PrivacyEvent], tags=["privacy"])
async def privacy_events() -> list[PrivacyEvent]:
    return [PrivacyEvent(**e) for e in egress_guard.events()]


@router.post("/privacy/receipts", response_model=PrivacyReceipt, status_code=201, tags=["privacy"])
async def create_receipt(body: ReceiptRequest) -> PrivacyReceipt:
    raise NotImplementedYet("Phase 4")


@router.get(
    "/privacy/receipts/{receipt_id}", response_model=PrivacyReceipt, tags=["privacy"], responses=problem_responses(404)
)
async def get_receipt(receipt_id: str) -> PrivacyReceipt:
    raise NotImplementedYet("Phase 4")


def _pack_info(p: Pack) -> PackInfo:
    return PackInfo(
        pack_id=p.pack_id,
        doc_type=p.doc_type,
        jurisdiction=p.jurisdiction,
        version=p.version,
        depth=p.depth,
        topics=[TopicInfo(id=t.id, title=t.title) for t in p.topics],
    )


@router.get("/packs", response_model=list[PackInfo], tags=["packs"])
async def list_packs(request: Request) -> list[PackInfo]:
    return [_pack_info(p) for p in sorted(all_packs(request.app.state.settings).values(), key=lambda p: p.pack_id)]


@router.get("/packs/{pack_id}", response_model=PackInfo, tags=["packs"], responses=problem_responses(404))
async def get_pack(request: Request, pack_id: str) -> PackInfo:
    pack = all_packs(request.app.state.settings).get(pack_id)
    if pack is None:
        raise LexiError(404, "NOT_FOUND", "Pack not found", f"No checklist pack named {pack_id!r}.")
    return _pack_info(pack)


@router.get("/eval/summary", response_model=EvalSummary, tags=["eval"])
async def eval_summary() -> EvalSummary:
    raise NotImplementedYet("Phase 4")
