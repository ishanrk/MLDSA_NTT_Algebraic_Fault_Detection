#include "block_guard.h"
#include "block_tables.inc"

static void small_ntt(uint32_t a[8])
{
    unsigned k = 0;
    for (unsigned len = 4; len > 0; len /= 2)
    {
        for (unsigned off = 0; off < 8; off += 2 * len)
        {
            uint32_t z = block_zetas[++k];
            for (unsigned j = off; j < off + len; j++)
            {
                uint32_t t = mldsa_mul(z, a[j + len]);
                uint32_t u = a[j];
                a[j] = mldsa_add(u, t);
                a[j + len] = mldsa_sub(u, t);
            }
        }
    }
}

int mldsa_ntt_forward_block(mldsa_ntt *out, const mldsa_poly *a)
{
    mldsa_poly encoded;
    uint32_t remove[8], first_sum = 0, bad = 0;

    for (unsigned b = 0; b < 8; b++)
    {
        uint64_t sum = 0;
        for (unsigned j = 0; j < 32; j++)
        {
            unsigned i = 32U * b + j;
            encoded.c[i] = a->c[i];
            sum += a->c[i];
        }
        uint32_t s = mldsa_reduce(sum);
        remove[b] = mldsa_sub(1, s);
        if (b == 0)
        {
            first_sum = s;
            remove[b] = 0;
        }
        encoded.c[32U * b] = mldsa_add(encoded.c[32U * b], remove[b]);
    }

    small_ntt(remove);
    mldsa_ntt_forward(out, &encoded);

    uint32_t adjustment = mldsa_sub(first_sum, 1);
    for (unsigned b = 0; b < 8; b++)
    {
        uint64_t sum = 0;
        for (unsigned j = 0; j < 32; j++)
        {
            unsigned i = 32U * b + j;
            uint32_t value = out->c[i];
            bad |= (uint32_t)(value >= MLDSA_Q);
            sum += (uint64_t)block_weights[i] * value;
            out->c[i] = mldsa_sub(value, remove[b]);
        }
        uint32_t expected = mldsa_add(block_expected[b], adjustment);
        bad |= mldsa_reduce(sum) ^ expected;
    }
    uint32_t keep = 0U - (uint32_t)(bad == 0);
    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        out->c[i] &= keep;
    }
    return -(int)(bad != 0);
}
