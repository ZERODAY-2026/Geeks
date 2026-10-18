"""Privacy status and receipts (Phases 1 and 4), checklist packs (Phase 2), evaluation summary (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter

from ...models import EvalSummary, PackInfo, PrivacyEvent, PrivacyReceipt, PrivacyStatus, ReceiptRequest
from ..errors import NotImplementedYet, problem_responses

router = APIRouter()


@router.get("/privacy/status", response_model=PrivacyStatus, tags=["privacy"])
async def privacy_status() -> PrivacyStatus:
    raise NotImplementedYet("Phase 1")


@router.get("/privacy/events", response_model=list[PrivacyEvent], tags=["privacy"])
async def privacy_events() -> list[PrivacyEvent]:
    raise NotImplementedYet("Phase 1")


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
