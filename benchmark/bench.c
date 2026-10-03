#include "board.h"
#include "mldsa44.h"
#include "mldsa44_internal.h"

static uint8_t pk[MLDSA44_PUBLICKEY_BYTES];
static uint8_t sk[MLDSA44_SECRETKEY_BYTES];
static uint8_t sig[MLDSA44_SIGNATURE_BYTES];
static uint8_t seed[MLDSA44_SEED_BYTES];
static const uint8_t rnd[MLDSA44_RANDOM_BYTES] =
{
    0x5a, 0xa2, 0xb0, 0x57, 0xde, 0xc2, 0x55, 0x24,
    0x25, 0xf9, 0xc3, 0xa1, 0xdf, 0x14, 0x29, 0x0a,
    0xa6, 0xb1, 0x84, 0x4b, 0xa9, 0x6b, 0x16, 0xd5,
    0x72, 0x64, 0x2b, 0xdc, 0x85, 0x6c, 0xb4, 0xe3
};
static const uint8_t msg[] = "benchmark";
static mldsa_poly poly;
static mldsa_ntt out, expected;

// prepare fixed inputs then measure the ntt wrapper and signer
int main(void)
{
    board_init();

    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        poly.c[i] = i;
    }
    for (unsigned i = 0; i < sizeof seed; i++)
    {
        seed[i] = (uint8_t)i;
    }

    // use the plain transform as a reference for the wrapper output
    mldsa_ntt_forward(&expected, &poly);
    // repeat the wrapper 32 times and keep any checker failure
    board_sync();
    uint32_t start = board_cycles();
    int ntt_error = 0;
    for (unsigned i = 0; i < 32; i++)
    {
        ntt_error |= mldsa44_ntt(&out, &poly);
    }
    board_sync();
    uint32_t ntt_cycles = (board_cycles() - start) / 32U;

    for (unsigned i = 0; i < MLDSA_N; i++)
    {
        ntt_error |= out.c[i] != expected.c[i];
    }
    if (ntt_error)
    {
        board_error("NTT failed");
    }

    if (mldsa44_keygen(pk, sk, seed))
    {
        board_error("Key generation failed");
    }

    // sign msg with sk and fixed rnd using an empty context
    board_sync();
    start = board_cycles();
    int sign_rc = mldsa44_sign(sig, sk, sizeof sk, msg, sizeof msg - 1,
                               0, 0, rnd);
    board_sync();
    uint32_t sign_cycles = board_cycles() - start;

    // reject a failed sign or a signature that pk cannot verify
    if (sign_rc != 0 ||
            mldsa44_verify(pk, sizeof pk, msg, sizeof msg - 1,
                           0, 0, sig, sizeof sig) != 0)
    {
        board_error("Signing failed");
    }

    board_print_header();
    board_print_cycles("ntt", ntt_cycles);
    board_print_cycles("sign", sign_cycles);
    board_finish();

    while (1)
    {
    }
}
