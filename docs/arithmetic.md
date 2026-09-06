# Arithmetic core

The arithmetic follows [FIPS 204](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.204.pdf), Sections 2.4.1, 2.5, 4, 7.5, and 7.6. The [NIST potential updates sheet](https://csrc.nist.gov/files/pubs/fips/204/final/docs/fips-204-potential-updates.xlsx), updated July 31, 2026, corrects the evaluation point notation in Sections 2.5 and 7.5: the NTT evaluates a polynomial once at each `zeta^(2*BitRev8(i)+1)`. Its Appendix A note concerns Montgomery reduction, which this implementation does not use.

## Representation

The ring is `Z_q[X]/(X^256+1)` with `q = 8380417`. `mldsa_poly` holds coefficients by ascending degree. `mldsa_ntt` holds evaluations in FIPS bit reversed order. Both use `uint32_t` canonical residues in `[0, q-1]` at every public function boundary and after every butterfly. There are no lazy or Montgomery residues. Arithmetic functions require canonical operands except `mldsa_reduce`, which accepts any `uint64_t`. `mldsa_center` maps a canonical residue into `[-4190208, 4190208]`; `mldsa_uncenter` accepts that centered interval and restores the canonical residue. The two conversion functions are for later coefficient handling and are not needed by the NTT.

The C code uses `uint32_t` for stored coefficients and modular sums, `uint64_t` for unreduced products, and `int32_t` only for centered representatives. The test oracle uses `int64_t` for unreduced negacyclic sums. Loop indices are `unsigned` and do not approach their type limit. The public functions assume valid ranges and nonoverlapping input and output objects, except coefficientwise additions, subtractions, and NTT pointwise multiplication, which also work in place. The standalone polynomial multiplication writes its result only after both inputs have been transformed, so its output can alias an input.

## Bounds

For canonical `a,b,z,u`, each is at most `q-1 = 8380416`.

| Intermediate | Bound | Width |
| --- | ---: | --- |
| `a+b`, butterfly `u+t` | `2(q-1) = 16760832 < 2^24` | `uint32_t` |
| `a+q-b` in subtraction branch | `2q-1 = 16760833 < 2^24` | `uint32_t` |
| `a*b`, `z*v` before reduction | `(q-1)^2 = 70231372333056 < 2^46` | `uint64_t` |
| inverse scale before reduction | `8347681(q-1) = 69957039415296 < 2^46` | `uint64_t` |
| schoolbook sum magnitude | `256(q-1)^2 = 17979231317262336 < 2^54` | `int64_t` |

Each schoolbook output receives exactly 256 signed products, and the magnitude bound holds even if all signs agree. The centered conversion first casts a canonical value below `2^23` to `int32_t`, then subtracts `q`; its result is in the documented interval. All modular products are reduced before the next butterfly. There are no signed shifts, signed overflowing operations, or implementation defined conversions.

## Roots and ordering

FIPS 204 fixes `zeta = 1753`. The generator verifies `zeta^256 = -1` and `zeta^512 = 1` modulo `q`, so it has order 512. It derives twiddle `zetas[k] = zeta^BitRev8(k) mod q` for `k = 1..255` and verifies all 256 evaluation points are distinct roots of `X^256+1`. It also transforms the monomial `X` and checks that the output order is `zeta^(2*BitRev8(i)+1)`.

The forward transform takes block lengths `128,64,...,1`, consuming twiddles in ascending table order. The inverse takes `1,2,...,128`, consumes the same twiddles in reverse with a negative sign, then multiplies each coefficient by `256^-1 mod q = 8347681`. This is ordinary modular scaling, with no Montgomery factor. Pointwise multiplication uses the canonical evaluations directly.

Regenerate the checked in table with `python3 tools/gen_zetas.py`; verify it with `python3 tools/gen_zetas.py --check`. The C build does not run Python. `make test` runs the C oracle and `make model` loads the C library from an independent Python ring model. The direct modular division used here is simple but may be expensive on Cortex M4; a later target specific reduction will need its own range proof and representation checks. Polynomial multiplication currently uses three 256 coefficient NTT objects on the stack, another measurement point for Cortex M4.
