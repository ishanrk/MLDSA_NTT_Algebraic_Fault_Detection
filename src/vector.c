#include "mldsa44_internal.h"

void mldsa44_matvec(mldsa_poly out[4], mldsa_ntt a[4][4], const mldsa_ntt v[4])
{
    for (unsigned r = 0; r < 4; r++) {
        mldsa_ntt sum = {{0}}, p;
        for (unsigned c = 0; c < 4; c++) {
            mldsa_ntt_mul(&p, &a[r][c], &v[c]);
            for (unsigned j = 0; j < MLDSA_N; j++)
                sum.c[j] = mldsa_add(sum.c[j], p.c[j]);
        }
        mldsa_ntt_inverse(&out[r], &sum);
    }
}

void mldsa44_mul_ntt(mldsa_poly *out, const mldsa_ntt *a, const mldsa_ntt *b)
{
    mldsa_ntt p;
    mldsa_ntt_mul(&p, a, b);
    mldsa_ntt_inverse(out, &p);
}
