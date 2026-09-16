from __future__ import annotations

import pytest

from liasse.cli import main


def test_doctor_reports_a_healthy_environment(capsys):
    assert main(["doctor"]) == 0
    assert "environment OK" in capsys.readouterr().out


def test_unknown_command_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["nonsense"])
