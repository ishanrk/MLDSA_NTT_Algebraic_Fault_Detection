#include "mldsa_checker.h"

#include "our_tables.inc"

int mldsa_ntt_forward_our(mldsa_ntt *r, const mldsa_poly *a)
{
    uint32_t x = 0, y = 0, u = 0, v = 0;

    for (unsigned i = 0; i < MLDSA_N; i++) {
        x = mldsa_add(x, a->c[i]);
        y = mldsa_add(y, mldsa_mul(our_beta[i], a->c[i]));
    }
    mldsa_ntt_forward(r, a);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        u = mldsa_add(u, mldsa_mul(our_a[i], r->c[i]));
        v = mldsa_add(v, mldsa_mul(our_alpha[i], r->c[i]));
    }
    return ((x ^ u) | (y ^ v)) ? -1 : 0;
}
