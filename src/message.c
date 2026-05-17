#include "mldsa44_internal.h"
#include "mldsa_shake.h"

void mldsa44_representative(uint8_t mu[64], const uint8_t tr[64],
                            const uint8_t *msg, size_t mlen,
                            const uint8_t *ctx, size_t clen)
{
    mldsa_shake s;
    uint8_t prefix[2] = {0, (uint8_t)clen};
    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, tr, 64);
    mldsa_shake_absorb(&s, prefix, 2);
    mldsa_shake_absorb(&s, ctx, clen);
    mldsa_shake_absorb(&s, msg, mlen);
    mldsa_shake_squeeze(&s, mu, 64);
}
