#include "mldsa_checker.h"
#include "range_ops.h"

static mldsa_ntt expected, *want_r;
static const mldsa_poly *want_a;
static unsigned calls;

void mldsa_ntt_forward(mldsa_ntt *r, const mldsa_poly *a)
{
    assert(r == want_r && a == want_a);
    calls++;
    for (unsigned i = 0; i < MLDSA_N; i++)
        r->c[i] = expected.c[i];
}

void memory(void)
{
    mldsa_poly a, before;
    mldsa_ntt r;
    for (unsigned i = 0; i < MLDSA_N; i++) {
        __CPROVER_assume(a.c[i] < MLDSA_Q);
        before.c[i] = a.c[i];
        expected.c[i] = nondet_u32();
        __CPROVER_assume(expected.c[i] < MLDSA_Q);
    }
    want_a = &a;
    want_r = &r;
#ifdef PRIOR
    int rc = mldsa_ntt_forward_prior(&r, &a);
#else
    int rc = mldsa_ntt_forward_our(&r, &a);
#endif
    assert(rc == 0 || rc == -1);
    assert(calls == 1);
    for (unsigned i = 0; i < MLDSA_N; i++) {
        assert(r.c[i] == expected.c[i]);
        assert(a.c[i] == before.c[i]);
    }
}
