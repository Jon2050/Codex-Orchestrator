from codexor.models import FinalSignal
from codexor.signals import parse_final_signal


def test_parse_signal_all_done() -> None:
    assert parse_final_signal("ALL DONE") == FinalSignal.ALL_DONE


def test_parse_signal_break_on_error() -> None:
    assert parse_final_signal("BREAK ON ERROR") == FinalSignal.BREAK_ON_ERROR


def test_parse_signal_invalid() -> None:
    assert parse_final_signal("done") == FinalSignal.INVALID
