#include "mldsa_checker.h"

#ifdef MLDSA_ENCODED_CHECKER
#include "encoded_tables.inc"
#include <string.h>

static int draw(uint32_t r[5])
{
    uint8_t bytes[20];
    if (mldsa_encoded_random(bytes, sizeof bytes))
        return -1;
    for (unsigned j = 0; j < 5; j++) {
        uint8_t *b = bytes + 4U * j;
        uint32_t x;
        do {
            x = (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
                ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
            x &= 0x7fffffU;
            if (x >= MLDSA_Q && mldsa_encoded_random(b, 4))
                return -1;
        } while (x >= MLDSA_Q);
        r[j] = x;
    }
    return 0;
}

static int check_one(mldsa_ntt *out, const mldsa_poly *a,
                     const uint32_t in[MLDSA_N], const uint32_t remove[MLDSA_N])
{
    uint32_t want[6] = {0};
    uint64_t sums[6] = {0};
    uint32_t tmp[MLDSA_N];
    static const uint8_t choose[6][6] = {
        {1, 0, 0, 0, 0, 0},
        {1, 1, 0, 0, 0, 0},
        {1, 2, 1, 0, 0, 0},
        {1, 3, 3, 1, 0, 0},
        {1, 4, 6, 4, 1, 0},
        {1, 5, 10, 10, 5, 1}
    };
    mldsa_poly z;
    mldsa_ntt b;
    uint32_t bad = 0;

    for (unsigned t = 0; t < MLDSA_N; t++)
        tmp[t] = a->c[enc_invpi[t]];
    // Repeated suffix sums produce binomial moments without field products.
    for (unsigned k = 0; k < 6; k++) {
        for (unsigned t = MLDSA_N - 1; t > 0; t--)
            tmp[t - 1] = mldsa_add(tmp[t - 1], tmp[t]);
        want[k] = tmp[0];
        for (unsigned j = 0; j < k; j++)
            want[k] = mldsa_sub(want[k], mldsa_mul(choose[k][j], want[j]));
    }
    for (unsigned i = 0; i < MLDSA_N; i++)
        z.c[i] = mldsa_add(a->c[i], in[i]);
    mldsa_ntt_forward(&b, &z);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        out->c[i] = mldsa_sub(b.c[i], remove[i]);
        for (unsigned k = 0; k < 6; k++)
            sums[k] += (uint64_t)enc_h[k][i] * out->c[i];
    }
    for (unsigned k = 0; k < 6; k++)
        bad |= want[k] ^ mldsa_reduce(sums[k]);
    return bad ? -1 : 0;
}

static int run(mldsa_ntt *out, const mldsa_poly *a, unsigned count)
{
    uint32_t r[5], diff[6], in[MLDSA_N], remove[MLDSA_N];
    if (draw(r)) {
        memset(out, 0, (size_t)count * sizeof *out);
        return -1;
    }
    diff[0] = r[0];
    for (unsigned j = 1; j < 5; j++)
        diff[j] = mldsa_add(r[j - 1], r[j]);
    diff[5] = r[4];
    // Newton forward differences evaluate the mask at permutation index t.
    for (unsigned t = 0; t < MLDSA_N; t++) {
        in[enc_invpi[t]] = diff[0];
        for (unsigned j = 0; j < 5; j++)
            diff[j] = mldsa_add(diff[j], diff[j + 1]);
    }
    for (unsigned i = 0; i < MLDSA_N; i++) {
        uint64_t sum = 0;
        for (unsigned j = 0; j < 5; j++)
            sum += (uint64_t)enc_v[j][i] * r[j];
        remove[i] = mldsa_reduce(sum);
    }
    for (unsigned i = 0; i < count; i++) {
        if (check_one(&out[i], &a[i], in, remove)) {
            memset(out, 0, (size_t)count * sizeof *out);
            return -1;
        }
    }
    return 0;
}

int mldsa_ntt_forward_encoded(mldsa_ntt *out, const mldsa_poly *a)
{
    return run(out, a, 1);
}

int mldsa_ntt_forward_encoded4(mldsa_ntt out[4], const mldsa_poly a[4])
{
    return run(out, a, 4);
}
#endif
