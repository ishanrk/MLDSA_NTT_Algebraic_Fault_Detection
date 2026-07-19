#include "range_ops.h"

void forward_memory(void)
{
    mldsa_poly a;
    mldsa_ntt r;
    for (unsigned i = 0; i < MLDSA_N; i++)
        __CPROVER_assume(a.c[i] < MLDSA_Q);
    mldsa_ntt_forward(&r, &a);
    for (unsigned i = 0; i < MLDSA_N; i++)
        assert(r.c[i] < MLDSA_Q);
}

void inverse_memory(void)
{
    mldsa_ntt a;
    mldsa_poly r;
    for (unsigned i = 0; i < MLDSA_N; i++)
        __CPROVER_assume(a.c[i] < MLDSA_Q);
    mldsa_ntt_inverse(&r, &a);
    for (unsigned i = 0; i < MLDSA_N; i++)
        assert(r.c[i] < MLDSA_Q);
}

void pointwise_memory(void)
{
    mldsa_ntt a, b, r;
    for (unsigned i = 0; i < MLDSA_N; i++) {
        __CPROVER_assume(a.c[i] < MLDSA_Q);
        __CPROVER_assume(b.c[i] < MLDSA_Q);
    }
    mldsa_ntt_mul(&r, &a, &b);
    for (unsigned i = 0; i < MLDSA_N; i++)
        assert(r.c[i] < MLDSA_Q);
}
