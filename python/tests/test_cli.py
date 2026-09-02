"""CLI smoke tests -- no hardware, no serial port."""

import pytest

from erdi_lrf.cli import main


def test_models_lists_the_whole_catalogue(capsys):
    assert main(["models"]) == 0
    out = capsys.readouterr().out
    assert "LRF3000A1" in out
    assert "LRF10VB" in out and "no published protocol" in out


def test_models_json(capsys):
    import json
    assert main(["models", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["published"]) == 22
    assert len(data["unpublished"]) == 2


@pytest.mark.parametrize("argv", [
    ["info", "--model", "LRF1500H"],
    ["--model", "LRF1500H", "info"],
])
def test_connection_options_work_on_both_sides_of_the_subcommand(argv, capsys):
    assert main(argv) == 0
    assert "460800" in capsys.readouterr().out


def test_info_reports_the_spd1200d03_baud_conflict(capsys):
    assert main(["info", "--model", "SPD1200D03"]) == 0
    out = capsys.readouterr().out
    assert "must be given explicitly" in out
    assert "BAUD CONFLICT" in out


def test_info_on_an_unpublished_model_fails_loudly(capsys):
    assert main(["info", "--model", "LRF10VB"]) == 1
    assert "not published" in capsys.readouterr().err


def test_model_is_required(capsys):
    assert main(["info"]) == 2
