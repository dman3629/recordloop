#!/usr/bin/env python3
"""Independent re-check of a certificate: rank and minimum distance via numpy.
Does not call mindist. Exit 0 if d agrees, 3 if not, 1 on bad input."""
import json
import sys

import numpy as np

CHUNK_BITS = 14  # enumerate 2^14 combinations per numpy batch


def rank_gf2(m):
    m = m.copy() % 2
    r = 0
    for c in range(m.shape[1]):
        piv = np.nonzero(m[r:, c])[0]
        if piv.size == 0:
            continue
        p = piv[0] + r
        m[[r, p]] = m[[p, r]]
        rows = np.nonzero(m[:, c])[0]
        rows = rows[rows != r]
        m[rows] ^= m[r]
        r += 1
        if r == m.shape[0]:
            break
    return r


def min_distance(rows):
    """Exact d by full enumeration: low bits of the message in a table, high bits looped."""
    g = np.array([[int(c) for c in row] for row in rows], dtype=np.uint8)
    k, n = g.shape
    lo = min(k, CHUNK_BITS)
    hi = k - lo
    # all combinations of the first `lo` rows
    idx = np.arange(1 << lo, dtype=np.uint32)
    bits = ((idx[:, None] >> np.arange(lo)) & 1).astype(np.uint8)
    table = (bits @ g[:lo]) % 2  # (2^lo, n)
    table = table.astype(np.uint8)
    best = n + 1
    for h in range(1 << hi):
        shift = np.zeros(n, dtype=np.uint8)
        for b in range(hi):
            if (h >> b) & 1:
                shift ^= g[lo + b]
        w = (table ^ shift).sum(axis=1)
        if h == 0:
            w = w[1:]  # drop the zero codeword
        best = min(best, int(w.min()))
    return best


def main(argv):
    if len(argv) != 2:
        print("usage: verify.py <certificate.json>")
        return 1
    try:
        cert = json.load(open(argv[1]))
        rows = cert["generator_rows"]
        n, k, claimed = int(cert["n"]), int(cert["k"]), int(cert["d"])
        assert len(rows) == k and all(len(r) == n for r in rows)
        g = np.array([[int(c) for c in r] for r in rows], dtype=np.uint8)
    except Exception as e:  # noqa: BLE001
        print(f"VERIFY BAD_INPUT {e}")
        return 1
    rk = rank_gf2(g)
    if rk < k:
        print(f"VERIFY DISAGREE rank {rk} < k {k}")
        return 3
    d = min_distance(rows)
    if d == claimed:
        print(f"VERIFY OK n={n} k={k} d={d}")
        return 0
    print(f"VERIFY DISAGREE n={n} k={k} claimed d={claimed} recomputed d={d}")
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
