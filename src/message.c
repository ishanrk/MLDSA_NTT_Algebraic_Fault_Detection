#include "mldsa44_internal.h"
#include "mldsa_shake.h"

size_t mldsa44_digest_len(unsigned hash)
{
    switch (hash) {
    case 4: case 5: case 7: return 28;
    case 1: case 6: case 8: case 11: return 32;
    case 2: case 9: return 48;
    case 3: case 10: case 12: return 64;
    default: return 0;
    }
}

void mldsa44_representative(uint8_t mu[64], const uint8_t tr[64],
                            unsigned hash,
                            const uint8_t *msg, size_t mlen,
                            const uint8_t *ctx, size_t clen)
{
    mldsa_shake s;
    uint8_t prefix[2] = {(uint8_t)(hash != 0U), (uint8_t)clen};
    uint8_t oid[11] = {0x06, 0x09, 0x60, 0x86, 0x48, 0x01,
                       0x65, 0x03, 0x04, 0x02, (uint8_t)hash};
    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, tr, 64);
    mldsa_shake_absorb(&s, prefix, 2);
    mldsa_shake_absorb(&s, ctx, clen);
    if (hash != 0U)
        mldsa_shake_absorb(&s, oid, sizeof oid);
    mldsa_shake_absorb(&s, msg, mlen);
    mldsa_shake_squeeze(&s, mu, 64);
}
