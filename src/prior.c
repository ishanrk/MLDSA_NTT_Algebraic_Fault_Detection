#include "mldsa_checker.h"

#include "prior_tables.inc"

int mldsa_ntt_forward_prior(mldsa_ntt *r, const mldsa_poly *a)
{
    uint32_t x = 0, y = 0, u = 0, v = 0;

    for (unsigned i = 0; i < MLDSA_N; i++) {
        x = mldsa_add(x, a->c[i]);
        y = mldsa_add(y, mldsa_mul(prior_beta[i], a->c[i]));
    }
    mldsa_ntt_forward(r, a);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        u = mldsa_add(u, mldsa_mul(prior_a[i], r->c[i]));
        // odd weights are one, so skip that product
        uint32_t t = i % 2U ? r->c[i] :
            mldsa_mul(prior_alpha[i / 2U], r->c[i]);
        v = mldsa_add(v, t);
    }
    return ((x ^ u) | (y ^ v)) ? -1 : 0;
}
