Construction ideas to draw on (pick one per mutation, do not mix everything at once):
1. Double circulant [I | C], n = 2k, with C circulant from a random or structured polynomial; try
   bordered double circulant (add a parity column and row).
2. Quasi-cyclic with 2 to 4 circulant blocks of size m, [C1 | C2 | ... ], m near n / blocks; pad or puncture
   to hit exactly n; pick m dividing n when possible, else shorten the last block.
3. Systematic QC [I | C1 | C2 ...] with polynomials of odd weight; choose weights near m/2 or sample weights
   in a narrow band.
4. Shortening, puncturing and extending: build a longer or higher-rate good code, then shorten (drop
   information positions) or puncture (drop columns) to reach (n, k); extend with an overall parity column
   when all weights are odd.
5. BCH-like seeds: cyclic codes of length 2^m - 1 or 2^m + 1 from cyclotomic cosets, then shorten or puncture
   to (n, k). Goppa-like or Reed-Muller-like seeds followed by column swaps.
6. Construction X: take C1 contained in C2 with larger distance, append a short tail code on the cosets.
7. Search over polynomials with symmetry (reciprocal polynomials, polynomials fixed under a multiplier).
8. Better local search: swap columns, flip bits in one circulant defining row only (keeps QC structure),
   keep when a stronger proxy (more row combinations of size 4, information-set low-weight search) improves.
9. Spend the time budget well: many cheap candidates first, then refine the top few.
