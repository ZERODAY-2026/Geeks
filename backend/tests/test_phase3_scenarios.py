"""Phase 3 gate (scenarios): arithmetic only on verified amounts; a missing input means computable=false."""

from __future__ import annotations

import pytest

from lexishield.agents.scenarios import ScenarioNotApplicable, ScenarioNotFound, run_scenario
from reports import employment_report, rental_report

pytestmark = pytest.mark.phase3


def test_a_missing_input_is_not_computable() -> None:
    _, report = employment_report()
    result = run_scenario("bond_exit", report, {})
    assert result.exposure is not None and result.exposure.computable is False
    assert result.exposure.missing_inputs == ["months_served"]
    assert result.exposure.total is None


def test_leaving_inside_the_bond_shows_the_stated_repayment() -> None:
    ing, report = employment_report()
    result = run_scenario("bond_exit", report, {"months_served": 10})
    exp = result.exposure
    assert exp is not None and exp.computable and exp.total == 200000
    comp = exp.components[0]
    assert ing.text[comp.citation.char_start : comp.citation.char_end] == comp.citation.quote
    assert "2,00,000" in comp.citation.quote


def test_leaving_after_the_bond_adds_nothing() -> None:
    _, report = employment_report()
    result = run_scenario("bond_exit", report, {"months_served": 30})
    assert result.exposure is not None and result.exposure.computable and result.exposure.total == 0


def test_leaving_inside_a_lock_in_with_no_stated_charge_is_not_computed() -> None:
    _, report = rental_report()
    result = run_scenario("rental_early_exit", report, {"months_stayed": 3})
    exp = result.exposure
    assert exp is not None and exp.computable is False
    assert any("lock-in" in m for m in exp.missing_inputs)
    # the notice-period rent is still shown as a component, from verified amounts
    assert exp.components and exp.components[0].amount == 40000


def test_leaving_after_the_lock_in_uses_only_stated_amounts() -> None:
    _, report = rental_report()
    result = run_scenario("rental_early_exit", report, {"months_stayed": 8})
    assert result.exposure is not None and result.exposure.computable and result.exposure.total == 40000


def test_deposit_refund_reports_the_silent_timeline() -> None:
    _, report = rental_report(refund_silent=True)
    result = run_scenario("deposit_refund", report, {})
    assert "in_rental.deposit_refund_deductions" in result.silences
    assert result.exposure is not None and result.exposure.total == 60000


def test_a_scenario_for_another_document_type_is_refused() -> None:
    _, report = rental_report()
    with pytest.raises(ScenarioNotApplicable):
        run_scenario("bond_exit", report, {"months_served": 3})


def test_an_unknown_scenario_is_not_found() -> None:
    _, report = rental_report()
    with pytest.raises(ScenarioNotFound):
        run_scenario("nope", report, {})
