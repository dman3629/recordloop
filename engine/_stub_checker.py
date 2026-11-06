"""Brute-force stand-in for checker/mindist (k <= 12 only). Same CLI and JSON as the real one.
Only for local tests; never used when checker/mindist exists (unless RECORDLOOP_CHECKER says so)."""
import json, sys, time


def rank_of(rows):
    basis, r = [], 0
    for v in rows:
        for b in basis:
            v = min(v, v ^ b)
        if v:
            basis.append(v); r += 1
    return r


def main(path):
    t0 = time.time()
    lines = open(path).read().split()
    n, k = int(lines[0]), int(lines[1])
    rows = [int(s, 2) for s in lines[2:2 + k]]
    if len(rows) != k or any(len(s) != n for s in lines[2:2 + k]) or k > 12:
        print(json.dumps({"error": "bad_input"})); return 1
    rk = rank_of(rows)
    if rk < k:
        print(json.dumps({"error": "rank_deficient", "rank": rk})); return 2
    best, bw, cnt = n + 1, 0, 0
    for m in range(1, 1 << k):
        w, i, c = 0, 0, m
        while c:
            if c & 1: w ^= rows[i]
            c >>= 1; i += 1
        cnt += 1
        p = bin(w).count("1")
        if p < best: best, bw = p, w
    pad = (-n) % 4
    hexs = format(bw << pad, "0{}x".format((n + pad) // 4))
    print(json.dumps({"n": n, "k": k, "rank": rk, "d": best, "min_codeword": hexs,
                      "codewords_enumerated": cnt, "elapsed_s": round(time.time() - t0, 3),
                      "checker_version": "stub-0"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
