#include "mldsa44.h"
#include "mldsa_poly.h"
#include <stdint.h>
#include <string.h>

extern volatile uint32_t emu_forward_calls;

// archie redirects the twiddle pointer to this zero table
__attribute__((used)) const uint32_t emu_zero_zetas[MLDSA_N] = {0};


// keep the signing results where archie can read them
struct emu_record
{
    uint32_t magic;
    int32_t sign_rc;
    int32_t verify_rc;
    uint32_t forward_calls;
    uint32_t zero_table_addr;
    uint8_t pk[MLDSA44_PUBLICKEY_BYTES];
    uint8_t sig[MLDSA44_SIGNATURE_BYTES];
};


// keep this record in memory for archie
__attribute__((used)) struct emu_record emu_result;
// case 191 supplies the original secret and fixed signing inputs
// its public key was reconstructed from that secret
#include "fips_case.h"

extern void emu_done(void);

// run one signing and leave its result in ram for archie
int main(void)
{
    // mark the record so the reader can check it was initialized
    emu_result.magic = 0x41524348U;
    emu_result.zero_table_addr = (uint32_t)(uintptr_t)emu_zero_zetas;
    emu_result.sign_rc = -2;
    emu_result.verify_rc = -2;
    // fill the signature buffer so an aborted signer is easy to spot
    memset(emu_result.sig, 0xa5, sizeof emu_result.sig);

    // the clean and faulted runs use this same public key
    memcpy(emu_result.pk, fips_pk, sizeof fips_pk);
    // the first 12 ntt calls transform s1 s2 and t0
    // calls 13 through 16 transform the four nonce rows
    emu_forward_calls = 0;
    emu_result.sign_rc = mldsa44_sign(emu_result.sig, fips_sk,
                                      sizeof fips_sk, fips_message, sizeof fips_message,
                                      fips_context, sizeof fips_context, fips_rnd);
    emu_result.forward_calls = emu_forward_calls;
    // verify only after signing returns a complete signature
    if (emu_result.sign_rc == 0)
    {
        emu_result.verify_rc = mldsa44_verify(emu_result.pk,
                                               sizeof emu_result.pk,
                                               fips_message, sizeof fips_message,
                                               fips_context, sizeof fips_context,
                                               emu_result.sig,
                                               sizeof emu_result.sig);
    }

    // archie stops here and dumps the record from ram
    emu_done();
    return 0;
}
