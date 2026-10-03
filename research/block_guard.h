#ifndef MLDSA_BLOCK_GUARD_H
#define MLDSA_BLOCK_GUARD_H

#include "mldsa_poly.h"

int mldsa_ntt_forward_block(mldsa_ntt *out, const mldsa_poly *a);

#endif
