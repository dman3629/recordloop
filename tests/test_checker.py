import json
import random
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHK = ROOT / "checker"
sys.path.insert(0, str(CHK))
from known_codes import all_known  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def build():
    subprocess.run(["make", "-C", str(CHK)], check=True, capture_output=True)


def write_matrix(path, n, rows):
    Path(path).write_text(f"{n} {len(rows)}\n" + "\n".join(rows) + "\n")


def run_mindist(path):
    p = subprocess.run([str(CHK / "mindist"), str(path)], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def rand_rows(rng, n, k):
    return ["".join(rng.choice("01") for _ in range(n)) for _ in range(k)]


@pytest.mark.parametrize("name,n,k,d,rows", all_known())
def test_known_code(tmp_path, name, n, k, d, rows):
    f = tmp_path / "m.txt"
    write_matrix(f, n, rows)
    rc, out = run_mindist(f)
    assert rc == 0
    assert out["d"] == d and out["rank"] == k
    assert out["codewords_enumerated"] == 2**k - 1
    assert out["checker_version"] == "1.0.0"
    cw = bin(int(out["min_codeword"], 16))[2:].zfill(len(out["min_codeword"]) * 4)[:n]
    assert cw.count("1") == d


def test_rank_deficient(tmp_path):
    f = tmp_path / "m.txt"
    write_matrix(f, 6, ["110000", "001100", "111100"])
    rc, out = run_mindist(f)
    assert rc == 2 and out["error"] == "rank_deficient" and out["rank"] == 2


def test_k27_rejected(tmp_path):
    f = tmp_path / "m.txt"
    rows = ["1" + "0" * 29] * 27
    write_matrix(f, 30, rows)
    rc, out = run_mindist(f)
    assert rc == 1 and "error" in out


def test_n257_rejected(tmp_path):
    f = tmp_path / "m.txt"
    write_matrix(f, 257, ["1" * 257])
    rc, _ = run_mindist(f)
    assert rc == 1


def test_bad_character(tmp_path):
    f = tmp_path / "m.txt"
    write_matrix(f, 4, ["10x1"])
    rc, _ = run_mindist(f)
    assert rc == 1


def test_verify_agrees_on_random_codes(tmp_path):
    rng = random.Random(7)
    checked = 0
    while checked < 20:
        k = rng.randint(1, 12)
        n = rng.randint(k, 60)
        rows = rand_rows(rng, n, k)
        f = tmp_path / "m.txt"
        write_matrix(f, n, rows)
        rc, out = run_mindist(f)
        if rc == 2:
            continue
        cert = tmp_path / "c.json"
        cert.write_text(json.dumps({"n": n, "k": k, "d": out["d"], "generator_rows": rows}))
        v = subprocess.run([sys.executable, str(CHK / "verify.py"), str(cert)], capture_output=True, text=True)
        assert v.returncode == 0, v.stdout
        cert.write_text(json.dumps({"n": n, "k": k, "d": out["d"] + 1, "generator_rows": rows}))
        v = subprocess.run([sys.executable, str(CHK / "verify.py"), str(cert)], capture_output=True, text=True)
        assert v.returncode == 3
        checked += 1


def test_timing_k24_n200(tmp_path):
    rng = random.Random(3)
    f = tmp_path / "m.txt"
    write_matrix(f, 200, rand_rows(rng, 200, 24))
    t = time.time()
    rc, out = run_mindist(f)
    assert rc == 0 and out["codewords_enumerated"] == 2**24 - 1
    assert time.time() - t < 2.0
