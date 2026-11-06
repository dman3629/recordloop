/* mindist: exact minimum distance of a binary linear code (full Gray-code enumeration). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define VERSION "1.0.0"
#define MAXN 256
#define MAXK 26
#define W 4

typedef struct { uint64_t w[W]; } vec;

static int fail(int code, const char *msg) {
    printf("{\"error\":\"%s\",\"checker_version\":\"" VERSION "\"}\n", msg);
    return code;
}

static int rank_of(const vec *rows, int k, int nw) {
    vec m[MAXK];
    memcpy(m, rows, sizeof(vec) * k);
    int r = 0;
    for (int bit = 0; bit < nw * 64 && r < k; bit++) {
        int wi = bit / 64;
        uint64_t mask = 1ULL << (63 - bit % 64);
        int p = -1;
        for (int i = r; i < k; i++) if (m[i].w[wi] & mask) { p = i; break; }
        if (p < 0) continue;
        vec t = m[p]; m[p] = m[r]; m[r] = t;
        for (int i = 0; i < k; i++)
            if (i != r && (m[i].w[wi] & mask))
                for (int j = 0; j < W; j++) m[i].w[j] ^= m[r].w[j];
        r++;
    }
    return r;
}

static double now(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    if (argc != 2) return fail(1, "usage: mindist <matrix.txt>");
    FILE *f = fopen(argv[1], "r");
    if (!f) return fail(1, "cannot_open_file");
    int n, k;
    if (fscanf(f, "%d %d", &n, &k) != 2) return fail(1, "bad_header");
    if (n < 1 || n > MAXN || k < 1 || k > MAXK) return fail(1, "n_or_k_out_of_range");
    vec rows[MAXK];
    memset(rows, 0, sizeof rows);
    char buf[1024];
    for (int i = 0; i < k; i++) {
        if (fscanf(f, "%1023s", buf) != 1) return fail(1, "missing_row");
        if ((int)strlen(buf) != n) return fail(1, "bad_row_length");
        for (int j = 0; j < n; j++) {
            if (buf[j] == '1') rows[i].w[j / 64] |= 1ULL << (63 - j % 64);
            else if (buf[j] != '0') return fail(1, "bad_character");
        }
    }
    fclose(f);
    double t0 = now();
    int nw = (n + 63) / 64;
    int rk = rank_of(rows, k, nw);
    if (rk < k) {
        printf("{\"error\":\"rank_deficient\",\"n\":%d,\"k\":%d,\"rank\":%d,\"checker_version\":\"" VERSION "\"}\n", n, k, rk);
        return 2;
    }
    vec best;
    memset(&best, 0, sizeof best);
    int d = 1 << 30;
    uint64_t total = (1ULL << k) - 1, count = 0;
    uint64_t c0 = 0, c1 = 0, c2 = 0, c3 = 0;
    /* Gray code: step i flips generator ctz(i); visits all 2^k - 1 non-zero codewords. */
    for (uint64_t i = 1; i <= total; i++) {
        const vec *g = &rows[__builtin_ctzll(i)];
        c0 ^= g->w[0]; c1 ^= g->w[1]; c2 ^= g->w[2]; c3 ^= g->w[3];
        int pc = __builtin_popcountll(c0) + __builtin_popcountll(c1)
               + __builtin_popcountll(c2) + __builtin_popcountll(c3);
        if (pc < d) { d = pc; best.w[0] = c0; best.w[1] = c1; best.w[2] = c2; best.w[3] = c3; }
        count++;
    }
    double el = now() - t0;
    char hex[MAXN / 4 + 2];
    int nh = (n + 3) / 4;
    for (int h = 0; h < nh; h++) {
        int v = 0;
        for (int b = 0; b < 4; b++) {
            int j = h * 4 + b;
            int bit = (j < n) ? (int)((best.w[j / 64] >> (63 - j % 64)) & 1) : 0;
            v = (v << 1) | bit;
        }
        hex[h] = "0123456789abcdef"[v];
    }
    hex[nh] = 0;
    printf("{\"n\":%d,\"k\":%d,\"rank\":%d,\"d\":%d,\"min_codeword\":\"%s\",\"codewords_enumerated\":%llu,\"elapsed_s\":%.3f,\"checker_version\":\"" VERSION "\"}\n",
           n, k, rk, d, hex, (unsigned long long)count, el);
    return 0;
}
