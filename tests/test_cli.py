"""CLI argument handling: --help / -h and unknown-option behavior."""

import agent4nao.cli as cli


class _ExplodingProvider:
    def __init__(self, *args, **kwargs):
        raise AssertionError("OllamaProvider must not be constructed for --help")


class _ExplodingSession:
    def __init__(self, *args, **kwargs):
        raise AssertionError("ConversationSession must not be constructed for --help")


def test_help_long(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "OllamaProvider", _ExplodingProvider)
    monkeypatch.setattr(cli, "ConversationSession", _ExplodingSession)
    code = cli.main(["--help"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Phase 1" in out
    assert "qwen2.5:7b-instruct-q4_K_M" in out
    assert "AGENT4NAO_" in out
    assert "No robot tools" in out


def test_help_short(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "OllamaProvider", _ExplodingProvider)
    monkeypatch.setattr(cli, "ConversationSession", _ExplodingSession)
    code = cli.main(["-h"])
    assert code == 0
    assert "Phase 1" in capsys.readouterr().out


def test_unknown_option_fails(monkeypatch) -> None:
    monkeypatch.setattr(cli, "OllamaProvider", _ExplodingProvider)
    monkeypatch.setattr(cli, "ConversationSession", _ExplodingSession)
    code = cli.main(["--unknown-option"])
    assert code != 0
