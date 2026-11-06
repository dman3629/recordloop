# checker/

`mindist.c` computes the exact minimum distance of a binary linear code from a generator matrix.

1. Rows are packed MSB-first into 4 x uint64 words (n <= 256, k <= 26).
2. Rank is computed by Gaussian elimination over GF(2); rank < k exits 2 with a JSON error.
3. All 2^k - 1 non-zero codewords are visited in Gray-code order: one generator is XORed in per step.
4. The minimum popcount is tracked with `__builtin_popcountll`; the minimising codeword is stored (hex, bit 0 first).
5. Exactness: the loop has no early exit and no sampling. `codewords_enumerated` must equal 2^k - 1.
6. Because the rows are independent (rank = k), distinct messages give distinct non-zero codewords, so the minimum is d.
7. `verify.py` re-derives rank and d with numpy (different method, does not call mindist) and exits 3 on disagreement.
8. `known_codes.py` holds Hamming, Golay, BCH and simplex fixtures with known d.
9. Build: `make -C checker` (gcc -O2). k=26, n=256 takes about 0.6 s on one core.
10. sha256 of `mindist.c`: 83c1fb00a888a782e68061ca3cc7791370f2c922c0ae0fc2ff8fd01e83b8a776
