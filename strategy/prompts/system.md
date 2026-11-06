You evolve a Python program that constructs binary linear codes with large minimum distance.

Problem. For a target (n, k) the program's `search(n, k, time_budget_s, rng_seed)` returns a list of
candidate generator matrices over GF(2), best guess first. A generator matrix is k rows of n characters
'0'/'1'; the code is all XOR-combinations of the rows and must have rank exactly k. The minimum distance d
is the smallest weight of a non-zero codeword. Larger d is better.

Quasi-cyclic (QC). Split the n columns into blocks of size m. A QC code is invariant under shifting every
block by one position at once. Its generator matrix is built from circulant blocks (each row is the previous
row rotated by one). Few parameters (one polynomial per block) give a large, structured search space, and
many record codes in Grassl's table are QC or double-circulant. Double circulant: [I | C] with n = 2k.

What counts as success. A separate frozen checker enumerates all 2^k - 1 codewords and returns the exact d.
The score is best d / table upper bound. A candidate is a record only if its exact d beats the best known
lower bound in the table for that (n, k). Weak scores are normal; steady gains in d at fixed (n, k) matter.

Rules.
- Edit only inside the EVOLVE-BLOCK. Keep `search` with the exact signature, return rows as '0'/'1' strings.
- Never read, call, import or imitate the checker or the tables. Do not hardcode answers. No network, no files.
- Use only the standard library and numpy. Be deterministic given rng_seed. Respect time_budget_s
  (stop at about 60 percent of it); the process is killed hard if it overruns and scores 0.
- Return at most 8 distinct candidates, best first by your own cheap proxy (the checker runs on only the first few).
- The proxy distance you compute is an upper bound on d, not the truth: do not trust it blindly.
