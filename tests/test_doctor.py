"""Tests for rlh.doctor and the `rlh doctor` command.

Checks that every check reports a name and detail, that a missing tool is
reported instead of crashing, and that the CLI exits non-zero only when a
required check fails. External tools are faked with monkeypatch where needed.
"""

from typer.testing import CliRunner

from rlh import doctor
from rlh.cli import app
from rlh.doctor import Check


def test_python_check_passes():
    assert doctor.check_python().ok


def test_missing_tool_is_reported(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    check = doctor.check_tool("definitely-not-installed")
    assert not check.ok
    assert "not found" in check.detail


def test_every_check_has_name_and_detail():
    for check in doctor.run_checks():
        assert check.name
        assert isinstance(check.detail, str)


def test_cli_fails_only_on_required(monkeypatch):
    runner = CliRunner()
    optional_fail = [Check("ok", True, ""), Check("gpu", False, "none", required=False)]
    monkeypatch.setattr("rlh.cli.run_checks", lambda: optional_fail)
    assert runner.invoke(app, ["doctor"]).exit_code == 0

    required_fail = [Check("node", False, "missing")]
    monkeypatch.setattr("rlh.cli.run_checks", lambda: required_fail)
    assert runner.invoke(app, ["doctor"]).exit_code == 1
