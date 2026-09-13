# Abdelmonem two checksum NTT checker

This implements the Dilithium construction in Abdelmonem, Holzbaur, Raddum, and Zeh, [ePrint 2025/170](https://eprint.iacr.org/2025/170.pdf), Sections 3.1 to 3.3 and 4.1 to 4.2. The implementation and generator were written from the equations, without using supplementary implementation code.

## Network and representation

Let `T` be the production forward transform with column inputs. Every coefficient is an ordinary canonical `uint32_t` field value in `[0,q)`, with `q=8380417`. There is no Montgomery factor, lazy representation, or final forward scaling. The production NTT evaluates at `1753^(2*BitRev8(i)+1)` in slot `i`. The paper's output slot `m` evaluates at `1753^(2*m+1)`, so `m=BitRev8(i)`.

Boundary `l` is the array after exactly `l` layers, including the copied input at boundary 0 and final output at boundary 8. Location `r=256*l+i` names array slot `i` at that boundary. There are `256*(8+1)=2304` locations, and `2304*2303/2=2653056` distinct pairs.

| Layer from boundary | Butterfly distance `len` | Blocks | Twiddle table indices |
| --- | ---: | ---: | --- |
| 0 | 128 | 1 | 1 |
| 1 | 64 | 2 | 2 to 3 |
| 2 | 32 | 4 | 4 to 7 |
| 3 | 16 | 8 | 8 to 15 |
| 4 | 8 | 16 | 16 to 31 |
| 5 | 4 | 32 | 32 to 63 |
| 6 | 2 | 64 | 64 to 127 |
| 7 | 1 | 128 | 128 to 255 |

Within block `g`, `off=2*len*g` and the pairs are `(j,j+len)` for `off<=j<off+len`. The twiddle is `1753^BitRev8(2^l+g)`. A butterfly sends `(u,v)` to `(u+z*v,u-z*v)` modulo `q`, reducing each product and sum immediately. Input and output slots retain their physical array indices within each layer; the bit reversal maps them to mathematical residue indices.

At boundary `l`, write `i=g*(256/2^l)+pos`. The corresponding paper wire is `w=BitRev_l(g)*(256/2^l)+pos`. Put `mu=BitRev_l(g)`. A unit deviation reaches natural output `m` exactly when `m mod 2^l=mu`, with coefficient `1753^((2*m+1)*pos)`. `tools/ntt_network.py` compares this formula against propagation through the exact butterfly graph for every modeled location. This also checks the output permutation, not just an end to end transform identity.

The summation printed in Equation (12) is inconsistent with its output specific propagation interpretation. The coefficient above follows from the residue decomposition in its proof and the weighted sum in Equation (17); the generator checks it against the entire actual network. No printed propagation expression is assumed without this check.

## Rows and construction

For output rows `a` and `alpha`, the input rows are `b=T^T*a` and `beta=T^T*alpha`. The paper uses row inputs in some places; the column notation used here expresses the same checksum equality for column inputs.

Section 4.1 sets `b[j]=1`. In natural output order, with `x_m=1753^(2*m+1)`, the independently derived row is

```
a[m] = (1/256) * sum(x_m^(-j) for j=0..255)
     = 2 / (256 * (1-x_m^(-1))) mod q
```

For each wire form `v_r`, compute `A_r=a^T*v_r`. All `A_r` are nonzero. Following the output coordinate recursion in Theorem 5 and Section 4.2, fix natural `alpha[128..255]=1`, then choose the remaining coordinates in descending order. For each pair form `v_r/A_r-v_s/A_s`, assign its constraint to the smallest output coordinate with a nonzero coefficient. At that coordinate all higher coordinates have been fixed, and the constraint excludes exactly one field value. Single response constraints also exclude values that make the second response zero. Pick the smallest legal value; the paper does not specify a tie break. This is its output coordinate construction, with no intermediate boundary assignment or random search.

The sufficient bound is `(2*256-1)*2304=1177344`, below `q`. The actual largest forbidden set is recorded in the generated certificate.

The printed Section 4.2 range ends at `N/2-1`, although it calls the fixed portion half the entries. Theorem 3 uses `N/2..N-1`. We use exactly that 128 entry half. Appendix A.1 prints a different placement of its 128 ones and different free coordinate choices. We generate an instance from the body construction rather than importing that appendix table. Every row identity and determinant is independently certified, so the particular permitted choices are explicit.

Finally, compute `beta[j]=sum(alpha[m]*x_m^j)` and permute the two output rows into production order. Natural `alpha[128..255]=1` becomes all odd physical output slots. The C tables therefore store `a[256]`, `beta[256]`, and only `alpha[128]` for even slots. The input row `b` and odd output weights are implicit ones. All four full rows are included in the certificate digest in production order.

## Exact certificate

```sh
python3 tools/gen_prior_checker.py
python3 tools/gen_prior_checker.py --check
```

The generator uses exact integer arithmetic modulo `q`. It checks the primitive root, all unit propagation vectors, both row identities by direct evaluation and a separate graph pullback, both response coordinates at every boundary, and every pair determinant `A_r*B_s-A_s*B_r`. The checked in [certificate](prior_certificate.json) records the counts and SHA256 digest. The coefficient digest concatenates full `b`, `a`, `beta`, and `alpha` rows as little endian 32 bit words. The network digest covers ordered butterfly triples for all eight layers.

The certificate checks all 2653056 pairs. Every first response, second response and pair determinant is nonzero. Runtime is excluded from the deterministic certificate.

## Scope

The claim concerns at most two additive field deviations at distinct modeled forward NTT boundary wires. Checker arithmetic, constants, comparison, and control flow are trusted. Two deviations at one wire combine into one; exact cancellation causes no result error. A shared twiddle corruption can affect many modeled wires and is outside this two deviation guarantee. Physical injection resistance and physical Cortex M4 cycle, flash, RAM, and stack measurements remain pending.

## C interface and selection

`mldsa_ntt_forward_prior(r,a)` snapshots both expected input checks, calls the original forward NTT once, and compares both output checks. It returns 0 on acceptance and -1 on a mismatch. Both arguments use the existing canonical polynomial/NTT types. On failure the caller must discard the output. The checksum computations reduce every term and accumulation through the existing arithmetic functions; the bounds in [arithmetic.md](arithmetic.md) apply without widening the representation.

Define `MLDSA_PRIOR_CHECKER` to select this function at the existing ML DSA forward transform call sites through the small internal `mldsa44_ntt` helper. The default build remains baseline. `make build/libmldsa_prior.so` builds the protected library separately. The signing algorithm and verification equations are unchanged; a transform mismatch returns an error before its result is used. `mldsa44_keygen` now returns an `int` status, 0 on success and -1 on invalid pointers or a checker mismatch, so its caller can also handle detected faults. Callers must check that status and discard key/signature output on failure.

The inverse NTT and matrix sampling are unprotected. The standalone baseline NTT and `mldsa_poly_mul` remain available. This is forward NTT coverage, not a claim that every ML DSA operation is fault protected.

The test only `MLDSA_TEST_FAULTS` build inserts a hook immediately after the input copy and after each complete forward layer. Production builds contain no injection state or callback. Hooks mutate canonical field values at exactly the boundaries used by the certificate.

## Targeted host validation

```sh
make prior build/libmldsa.so build/libmldsa_prior.so
python3 test/test_known_answers.py build/libmldsa.so build/nist
python3 test/test_known_answers.py build/libmldsa_prior.so build/nist
```

The checker suite compares eight no fault polynomials with the baseline: zero, `X`, all `q-1`, alternating `0`/`q-1`, and four successive fixed pseudorandom polynomials. It also checks inverse round trips and 36 arithmetic boundary pairs. Its 36 single injections cover first/middle/last wire regions at input, early, middle, late, and final boundaries with magnitudes `1`, `17`, and `q-1`.

Ten location pairs, each with three magnitudes, give 30 two fault cases. They include adjacent locations, far apart locations, equal layers, adjacent layers, and input/final or early/late combinations. The second magnitude is calculated to cancel the first checksum exactly using an independent evaluation formula. The test confirms that cancellation, confirms a nonzero NTT result error, and requires rejection by the second checksum. These are 66 runtime NTT injections, not an attempt to replace the exhaustive certificate. Three additional scheme level injections require key generation, signing, and verification to propagate a transform error.

The shared compact entry point also checks the NIST SHAKE case, official key generation digest, fixed host signature digest, valid verification, and modified message/signature rejection. The Python official known answer test compares complete key and signature bytes for keyGen `tcId 1` and sigGen `tcId 1`, then checks sigVer cases `3` (valid) and `1` (invalid), from the existing pinned NIST data.

GCC 11.4.0 debug and optimized builds, Clang 14.0.0, AddressSanitizer, and UndefinedBehaviorSanitizer passed the targeted checker suite. Both baseline and protected libraries passed official known answer vectors; the Clang protected library also passed them.

To repeat the sanitizer and alternate compiler checks, force rebuilding this small target when changing flags:

```sh
make -B prior CC=gcc OPT='-O0 -g'
make -B prior CC=clang
make -B prior CC=gcc OPT='-O1 -g' SAN='-fsanitize=address'
make -B prior CC=gcc OPT='-O1 -g' SAN='-fsanitize=undefined -fno-sanitize-recover=all'
```

## ARM validation and provisional costs

```sh
make arm-mps2 arm-mps2-prior arm-mps2-bench arm-mps2-prior-bench build/count_prior
python3 tools/run_mps2.py
python3 tools/run_mps2.py --prior
python3 tools/measure_checkers.py
```

Use the toolchain overrides in [cortexm4.md](cortexm4.md) when the compiler and QEMU are outside `PATH`. `tools/measure_checkers.py` accepts `ARM_CC` and `ARM_SIZE` for the same reason.

Both compact QEMU suites passed with `arm-none-eabi-gcc` 10.3.1, Cortex M4 Thumb soft ABI, and QEMU 6.2.0 `mps2-an386`. The protected firmware runs the same targeted C tests as the host, including the single/pair injections and scheme error propagation. No thousands case ARM campaign was run.

The [generated comparison](comparison.md) come from [raw JSON](../bench/comparison.json). A host counter intercepts the actual addition, subtraction, and multiplication functions while preserving their original bodies. For one protected forward transform there are 640 additional modular multiplications, 1024 additional modular additions, and no additional modular subtractions. The 256 input beta products, 256 output a products, and 128 nonunity output alpha products explain the multiplication count. Four 256 term checksum accumulations explain the addition count. Stored constants occupy 2560 bytes for 640 coefficients; the 384 unity coefficients are implicit.

The matched benchmark ELF images contain no test injection code. The protected image adds 2832 text bytes, including readonly constants, with no `.data` or BSS increase. These are emulator layout link sizes, not physical flash/RAM observations. Both benchmark images exit on the unavailable QEMU DWT counter without producing cycle or stack data. Real Cortex M4 performance and physical memory measurements remain pending.

The baseline compact host suite also passed with combined ASan/UBSan. The complete exact certificate was regenerated at completion and matched the checked in coefficients and certificate byte for byte.
