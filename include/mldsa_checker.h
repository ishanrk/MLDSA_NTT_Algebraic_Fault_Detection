#ifndef MLDSA_CHECKER_H
#define MLDSA_CHECKER_H

#include "mldsa_poly.h"

int mldsa_ntt_forward_prior(mldsa_ntt *r, const mldsa_poly *a);
int mldsa_ntt_forward_our(mldsa_ntt *r, const mldsa_poly *a);

#endif
