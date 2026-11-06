"""Classic binary codes with known minimum distance, used as sanity fixtures."""


def _cyclic_rows(n, k, poly_exps):
    """Rows are shifts of the generator polynomial; char j = coeff of x^j."""
    rows = []
    for s in range(k):
        r = ["0"] * n
        for e in poly_exps:
            r[e + s] = "1"
        rows.append("".join(r))
    return rows


def _parity_extend(rows):
    return [r + str(r.count("1") % 2) for r in rows]


def _from_columns(cols, nbits):
    """Generator matrix whose columns are the given integers (nbits rows)."""
    return ["".join(str((c >> b) & 1) for c in cols) for b in range(nbits)]


def hamming_7_4():
    # parity-check form: simplex [7,3] is the dual; build G in systematic form
    h = [[1, 1, 0, 1, 1, 0, 0], [1, 0, 1, 1, 0, 1, 0], [0, 1, 1, 1, 0, 0, 1]]
    # G = [I4 | A^T] where H = [A | I3]
    rows = []
    for i in range(4):
        parity = [h[r][i] for r in range(3)]
        rows.append("".join("1" if j == i else "0" for j in range(4)) + "".join(map(str, parity)))
    return rows


def golay_23():
    g = [0, 2, 4, 5, 6, 10, 11]  # x^11+x^10+x^6+x^5+x^4+x^2+1
    return _cyclic_rows(23, 12, g)


def bch_31_16():
    g = [0, 1, 2, 3, 5, 7, 8, 9, 10, 11, 15]
    return _cyclic_rows(31, 16, g)


def simplex_15_4():
    return _from_columns(range(1, 16), 4)


def all_known():
    """-> list of (name, n, k, d, rows)"""
    ham = hamming_7_4()
    gol = golay_23()
    return [
        ("hamming_7_4", 7, 4, 3, ham),
        ("ext_hamming_8_4", 8, 4, 4, _parity_extend(ham)),
        ("golay_23_12", 23, 12, 7, gol),
        ("ext_golay_24_12", 24, 12, 8, _parity_extend(gol)),
        ("bch_31_16", 31, 16, 7, bch_31_16()),
        ("simplex_15_4", 15, 4, 8, simplex_15_4()),
    ]


if __name__ == "__main__":
    for name, n, k, d, rows in all_known():
        print(name, n, k, d)
