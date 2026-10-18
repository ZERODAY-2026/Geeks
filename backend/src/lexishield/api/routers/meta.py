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
)
from ...trust import egress_guard
from ..errors import NotImplementedYet, problem_responses

router = APIRouter()


@router.get("/privacy/status", response_model=PrivacyStatus, tags=["privacy"])
async def privacy_status(request: Request) -> PrivacyStatus:
    st = egress_guard.status()
    return PrivacyStatus(
        egress_guard=EgressGuardStatus(
            active=st["active"], allowed_hosts=st["allowed_hosts"], blocked_attempts=st["blocked_attempts"]
        ),
        network_mode="host-loopback",
        # Placeholder: the temp-file sentinel is not built yet, so this is not a measurement.
        temp_files_created=0,
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


@router.get("/packs", response_model=list[PackInfo], tags=["packs"])
async def list_packs() -> list[PackInfo]:
    raise NotImplementedYet("Phase 2")


@router.get("/packs/{pack_id}", response_model=PackInfo, tags=["packs"], responses=problem_responses(404))
async def get_pack(pack_id: str) -> PackInfo:
    raise NotImplementedYet("Phase 2")


@router.get("/eval/summary", response_model=EvalSummary, tags=["eval"])
async def eval_summary() -> EvalSummary:
    raise NotImplementedYet("Phase 4")
