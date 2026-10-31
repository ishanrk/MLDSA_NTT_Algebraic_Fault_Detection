#ifndef MLDSA_CHECKER_H
#define MLDSA_CHECKER_H

#include "mldsa_poly.h"
#include <stddef.h>
#include <stdint.h>

int mldsa_ntt_forward_prior(mldsa_ntt *r, const mldsa_poly *a);
int mldsa_ntt_forward_our(mldsa_ntt *r, const mldsa_poly *a);
int mldsa_ntt_forward_encoded(mldsa_ntt *r, const mldsa_poly *a);
int mldsa_ntt_forward_encoded4(mldsa_ntt r[4], const mldsa_poly a[4]);

// The application supplies fresh random bytes or reports failure.
// This hook is required only by the encoded checker build.
int mldsa_encoded_random(uint8_t *out, size_t len);

#endif
