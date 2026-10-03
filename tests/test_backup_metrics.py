import copy
import importlib.machinery
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("backup_metrics", str(ROOT / "image/bin/backup-metrics"))
spec = importlib.util.spec_from_loader("backup_metrics", loader)
bm = importlib.util.module_from_spec(spec)
sys.modules["backup_metrics"] = bm
loader.exec_module(bm)

FIXTURE = ROOT / "tests/fixtures/info-one-full.json"


def info():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def metrics(data):
    out = {}
    for line in bm.to_metrics(data).splitlines():
        if line and not line.startswith("#"):
            name, value = line.rsplit(" ", 1)
            out[name] = float(value)
    return out


def test_real_pgbackrest_output_is_parsed():
    m = metrics(info())
    assert m["pgbackrest_stanza_status_code"] == 0
    assert m['pgbackrest_backup_count{type="full"}'] == 1
    assert m['pgbackrest_backup_count{type="incr"}'] == 0
    assert m['pgbackrest_backup_last_timestamp_seconds{type="full"}'] == 1790993370
    assert m['pgbackrest_backup_last_duration_seconds{type="full"}'] == 2
    assert m['pgbackrest_backup_last_size_bytes{type="full"}'] == 31657007
    assert m["pgbackrest_repo_backup_bytes"] == 3829560


def test_types_without_backups_have_no_timestamp_series():
    m = metrics(info())
    assert 'pgbackrest_backup_last_timestamp_seconds{type="diff"}' not in m


def test_newest_backup_of_each_type_wins():
    data = info()
    newer = copy.deepcopy(data[0]["backup"][0])
    newer["label"] = "later"
    newer["timestamp"] = {"start": 1790999990, "stop": 1791000000}
    data[0]["backup"].append(newer)
    m = metrics(data)
    assert m['pgbackrest_backup_last_timestamp_seconds{type="full"}'] == 1791000000
    assert m['pgbackrest_backup_count{type="full"}'] == 2


def test_wal_segment_number_is_exact():
    assert bm.wal_segment_number("000000010000000000000005") == 5
    assert bm.wal_segment_number("00000002000000020000000A") == 2 * 256 + 10
    assert bm.wal_segment_number("garbage") == 0
    assert metrics(info())["pgbackrest_wal_archive_max_segment"] == 5


def test_unreadable_repository_reports_a_problem():
    m = metrics([])
    assert m["pgbackrest_stanza_status_code"] == 99
    assert m['pgbackrest_backup_count{type="full"}'] == 0


def test_large_numbers_are_written_without_exponent():
    text = bm.to_metrics(info())
    assert "1790993370" in text
    assert "e+" not in text


def test_cli_prints_metrics_for_a_file(capsys):
    assert bm.main([str(FIXTURE)]) == 0
    assert "pgbackrest_stanza_status_code 0" in capsys.readouterr().out
