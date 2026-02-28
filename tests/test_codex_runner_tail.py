from codexor.codex_runner import _OutputTailTracker


def test_output_tail_tracker_uses_last_non_empty_line() -> None:
    tracker = _OutputTailTracker()
    tracker.feed("line one\rline two\n")
    tracker.feed("\n")
    tracker.feed("ALL DONE")
    tracker.finalize()
    assert tracker.last_non_empty == "ALL DONE"
