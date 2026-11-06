# Submitting a record (human step)

Nothing here is automated. Only a person sends the email.

## Checklist

- [ ] `python checker/verify.py certs/verified/<file>.json` exits 0 (run it yourself, on your machine).
- [ ] Rebuilt the checker from source (`make -C checker`) and re-ran `checker/mindist` on the matrix: same `d`.
- [ ] Novelty re-checked against the live table on the day of sending (codetables.de, binary, n, k): the lower bound is still below `d`. Run `bash tables/refresh.sh` then `python tables/novelty.py n k d` and look at the website too.
- [ ] Not already claimed by someone else: the (n, k, d) is not in `tables/claims.json` (papers whose codes the table has not absorbed yet). If it is, the result is a reproduction, not a new record; say so if you write to anyone.
- [ ] Generator matrix attached as plain text (first line `n k`, then k rows of 0/1).
- [ ] Certificate JSON attached.
- [ ] Describe the construction honestly (quasi-cyclic generator polynomials if known; otherwise "found by program search, matrix attached").

## Email template

To: codes@codetables.de
Subject: New binary linear code [n,k,d] improving the lower bound

Dear Prof. Grassl,

I found a binary linear code with parameters [n,k,d]. The current lower bound in your table for n=.., k=.. is x (checked on <date>), so this improves the entry by d - x.

The generator matrix is attached (matrix.txt, k rows of n bits). The minimum distance was computed by exhaustive enumeration of all 2^k - 1 non-zero codewords and confirmed by an independent implementation. The certificate with checksums is attached (certificate.json). Source code: <repo link>.

Construction: <short description, or: found by an automated program search>.

Kind regards,
Derezar Master
