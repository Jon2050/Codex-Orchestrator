from codexor.models import FinalSignal
from codexor.signals import parse_final_signal, parse_summary


def test_parse_signal_all_done() -> None:
    assert parse_final_signal("ALL DONE") == FinalSignal.ALL_DONE


def test_parse_signal_break_on_error() -> None:
    assert parse_final_signal("BREAK ON ERROR") == FinalSignal.BREAK_ON_ERROR


def test_parse_signal_invalid() -> None:
    assert parse_final_signal("done") == FinalSignal.INVALID


def test_parse_summary_success() -> None:
    output = "Some random text\n<summary>\nThis is a test summary.\nIt has multiple lines.\n</summary>\nALL DONE"
    assert parse_summary(output) == "This is a test summary.\nIt has multiple lines."


def test_parse_summary_empty() -> None:
    output = "Some random text\nALL DONE"
    assert parse_summary(output) == ""
