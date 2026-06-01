#include "mldsa44.h"
#include "mldsa44_internal.h"
#include "mldsa_shake.h"

size_t mldsa44_digest_len(unsigned hash)
{
    switch (hash) {
    case MLDSA44_SHA2_224:
    case MLDSA44_SHA2_512_224:
    case MLDSA44_SHA3_224: return 28;
    case MLDSA44_SHA2_256:
    case MLDSA44_SHA2_512_256:
    case MLDSA44_SHA3_256:
    case MLDSA44_SHAKE128: return 32;
    case MLDSA44_SHA2_384:
    case MLDSA44_SHA3_384: return 48;
    case MLDSA44_SHA2_512:
    case MLDSA44_SHA3_512:
    case MLDSA44_SHAKE256: return 64;
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
