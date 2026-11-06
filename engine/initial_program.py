"""Seed program evolved by OpenEvolve. search() must return candidate generator matrices.

Contract: search(n, k, time_budget_s, rng_seed) -> list of matrices, best first; each matrix is
k row strings of n characters '0'/'1' with rank k. The frozen checker computes the exact distance;
nothing here may call or modify it. The proxy below is only a cheap guide, not the truth.
"""
import itertools
import random
import time

import numpy as np

# EVOLVE-BLOCK-START


def circulant_rows(m, poly, k):
    """First k rows of the m x m circulant whose first row is `poly` (list of 0/1 of length m)."""
    return np.array([np.roll(poly, i) for i in range(k)], dtype=np.uint8)


def build_qc(n, k, m, rng):
    """Systematic quasi-cyclic generator [I_k | C1 | C2 | ...] cut to n columns.
    Each Ci is a (k x m) slice of a random circulant of size m >= k, so rank is always k.
    With n = 2k and one block this is a double-circulant code."""
    blocks = []
    need = n - k
    if need <= 0:
        return np.eye(k, dtype=np.uint8)[:, :n]
    while sum(b.shape[1] for b in blocks) < need:
        poly = [rng.randint(0, 1) for _ in range(m)]
        poly[0] = 1
        blocks.append(circulant_rows(m, poly, k))
    A = np.hstack(blocks)[:, :need]
    return np.hstack([np.eye(k, dtype=np.uint8), A])


def proxy(G, rng, samples=2048):
    """Cheap estimate of minimum distance: min weight over row sums of size 1-3 and random words.
    Always >= the true d, so higher means 'fewer low-weight words found'."""
    k, n = G.shape
    best = n
    for r in (1, 2, 3):
        combos = list(itertools.combinations(range(k), r))[:3000]
        if combos:
            idx = np.array(combos)
            w = (G[idx].sum(axis=1) % 2).sum(axis=1)
            best = min(best, int(w.min()))
    msgs = np.array([[rng.getrandbits(1) for _ in range(k)] for _ in range(samples)], dtype=np.uint8)
    w = ((msgs @ G) % 2).sum(axis=1)
    return min(best, int(w[w > 0].min())) if (w > 0).any() else best


def improve(G, rng, deadline):
    """Local search: flip a few bits in the non-identity part, keep the change if proxy does not drop."""
    k, n = G.shape
    cur, score = G.copy(), proxy(G, rng)
    while time.time() < deadline and n > k:
        trial = cur.copy()
        for _ in range(rng.randint(1, 3)):
            trial[rng.randrange(k), rng.randrange(k, n)] ^= 1
        s = proxy(trial, rng)
        if s >= score:
            cur, score = trial, s
    return cur, score


def to_rows(G):
    return ["".join(str(int(b)) for b in row) for row in G]


def search(n, k, time_budget_s, rng_seed):
    rng = random.Random(rng_seed)
    deadline = time.time() + 0.6 * time_budget_s
    pool = []
    sizes = [m for m in range(k, k + 4)]
    while time.time() < deadline - 0.3 * time_budget_s:
        m = rng.choice(sizes)
        G = build_qc(n, k, m, rng)
        pool.append((proxy(G, rng), G))
        if len(pool) >= 40:
            break
    pool.sort(key=lambda t: -t[0])
    out = []
    for _, G in pool[:6]:
        G2, s = improve(G, rng, min(deadline, time.time() + 0.05 * time_budget_s))
        out.append((s, G2))
    out.sort(key=lambda t: -t[0])
    return [to_rows(G) for _, G in out]


# EVOLVE-BLOCK-END
