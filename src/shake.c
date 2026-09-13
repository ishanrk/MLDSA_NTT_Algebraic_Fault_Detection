#include "mldsa_shake.h"

#include <string.h>

#include "keccak_tables.inc"

static uint64_t rot(uint64_t x, unsigned n)
{
    return n == 0U ? x : (x << n) | (x >> (64U - n));
}

// keccak perm here; citation: https://csrc.nist.gov/pubs/fips/202/final
static void permute(uint64_t a[25])
{
    uint64_t b[25], c[5], d[5];

    for (unsigned i = 0; i < 24; i++) {
        for (unsigned x = 0; x < 5; x++) {
            c[x] = 0;
            for (unsigned y = 0; y < 5; y++)
                c[x] ^= a[x + 5U * y];
        }
        for (unsigned x = 0; x < 5; x++)
            d[x] = c[(x + 4U) % 5U] ^ rot(c[(x + 1U) % 5U], 1);
        for (unsigned y = 0; y < 5; y++) {
            for (unsigned x = 0; x < 5; x++) {
                unsigned nx = y;
                unsigned ny = (2U * x + 3U * y) % 5U;
                unsigned pos = x + 5U * y;
                b[nx + 5U * ny] = rot(a[pos] ^ d[x], rho[pos]);
            }
        }
        for (unsigned y = 0; y < 5; y++) {
            for (unsigned x = 0; x < 5; x++) {
                a[x + 5U * y] = b[x + 5U * y] ^
                    ((~b[(x + 1U) % 5U + 5U * y]) & b[(x + 2U) % 5U + 5U * y]);
            }
        }
        a[0] ^= rc[i];
    }
}

void mldsa_shake_init(mldsa_shake *s, unsigned strength)
{
    memset(s, 0, sizeof *s);
    s->rate = strength == 128U ? 168U : 136U;
}

void mldsa_shake_absorb(mldsa_shake *s, const uint8_t *in, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        s->a[s->pos / 8U] ^= (uint64_t)in[i] << (8U * (s->pos % 8U));
        s->pos++;
        if (s->pos == s->rate) {
            permute(s->a);
            s->pos = 0;
        }
    }
}

void mldsa_shake_squeeze(mldsa_shake *s, uint8_t *out, size_t n)
{
    if (!s->squeezing) {
        s->a[s->pos / 8U] ^= UINT64_C(0x1f) << (8U * (s->pos % 8U));
        s->a[(s->rate - 1U) / 8U] ^= UINT64_C(0x80) << (8U * ((s->rate - 1U) % 8U));
        permute(s->a);
        s->pos = 0;
        s->squeezing = 1;
    }
    for (size_t i = 0; i < n; i++) {
        if (s->pos == s->rate) {
            permute(s->a);
            s->pos = 0;
        }
        out[i] = (uint8_t)(s->a[s->pos / 8U] >> (8U * (s->pos % 8U)));
        s->pos++;
    }
}

void mldsa_shake128(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen)
{
    mldsa_shake s;
    mldsa_shake_init(&s, 128);
    mldsa_shake_absorb(&s, in, inlen);
    mldsa_shake_squeeze(&s, out, outlen);
}

void mldsa_shake256(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen)
{
    mldsa_shake s;
    mldsa_shake_init(&s, 256);
    mldsa_shake_absorb(&s, in, inlen);
    mldsa_shake_squeeze(&s, out, outlen);
}
