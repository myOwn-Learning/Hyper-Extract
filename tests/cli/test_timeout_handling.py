"""Tests for CLI timeout handling."""

import pytest
import typer

from hyperextract.cli.cli import _feed_text_or_exit


class TimeoutKA:
    def feed_text(self, text: str) -> None:
        raise TimeoutError("request timed out")


class RuntimeFailureKA:
    def feed_text(self, text: str) -> None:
        raise RuntimeError("401 invalid api key")


def test_feed_text_timeout_exits_cleanly():
    with pytest.raises(typer.Exit) as exc:
        _feed_text_or_exit(TimeoutKA(), "input")

    assert exc.value.exit_code == 1


def test_feed_text_non_timeout_reraises():
    with pytest.raises(RuntimeError, match="401 invalid api key"):
        _feed_text_or_exit(RuntimeFailureKA(), "input")
