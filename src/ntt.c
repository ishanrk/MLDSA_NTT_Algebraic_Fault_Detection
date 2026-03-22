#include "mldsa_poly.h"

static const uint32_t zetas[MLDSA_N] = {
#include "zetas.inc"
};

void mldsa_ntt_forward(mldsa_ntt *r, const mldsa_poly *a)
{
    unsigned k = 0;

    for (unsigned i = 0; i < MLDSA_N; i++)
        r->c[i] = a->c[i];

    for (unsigned len = MLDSA_N / 2; len > 0; len /= 2) {
        for (unsigned off = 0; off < MLDSA_N; off += 2 * len) {
            uint32_t z = zetas[++k];
            for (unsigned j = off; j < off + len; j++) {
                uint32_t t = mldsa_mul(z, r->c[j + len]);
                uint32_t u = r->c[j];
                r->c[j] = mldsa_add(u, t);
                r->c[j + len] = mldsa_sub(u, t);
            }
        }
    }
}

void mldsa_ntt_inverse(mldsa_poly *r, const mldsa_ntt *a)
{
    unsigned k = MLDSA_N;

    for (unsigned i = 0; i < MLDSA_N; i++)
        r->c[i] = a->c[i];

    for (unsigned len = 1; len < MLDSA_N; len *= 2) {
        for (unsigned off = 0; off < MLDSA_N; off += 2 * len) {
            uint32_t z = MLDSA_Q - zetas[--k];
            for (unsigned j = off; j < off + len; j++) {
                uint32_t u = r->c[j];
                uint32_t v = r->c[j + len];
                r->c[j] = mldsa_add(u, v);
                r->c[j + len] = mldsa_mul(z, mldsa_sub(u, v));
            }
        }
    }

    for (unsigned i = 0; i < MLDSA_N; i++)
        r->c[i] = mldsa_mul(r->c[i], 8347681U);
}

void mldsa_ntt_mul(mldsa_ntt *r, const mldsa_ntt *a, const mldsa_ntt *b)
{
    for (unsigned i = 0; i < MLDSA_N; i++)
        r->c[i] = mldsa_mul(a->c[i], b->c[i]);
}
