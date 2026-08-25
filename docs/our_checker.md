# Deterministic intermediate boundary checker

Our construction uses boundary `k=4` of the existing forward NTT. The baseline and published checker keep their original transforms and constants. All rows here use physical production array indices and canonical field values modulo `q=8380417`.

## Model and criterion

Write the column transform as `T`. Boundary `l` is the array after `l` complete layers, including input boundary 0 and output boundary 8. Location `r=256*l+i` denotes slot `i`. A unit additive deviation there propagates to output vector `v_r`. For output rows `a` and `alpha`, define `A_r=a^T v_r` and `B_r=alpha^T v_r`. The corresponding input rows are `b=T^T a` and `beta=T^T alpha`.

The first expected checksum is the ordinary input sum, so `b` is all ones. The generator obtains `a=T^(-T)b` by inverse transpose butterflies. It checks this row against direct evaluation at `1753^(2*BitRev8(i)+1)` and against a separate graph pullback. Every modeled first response is nonzero.

For distinct locations `r,s`, the determinant `A_r B_s-A_s B_r` must be nonzero. This means the two response columns are independent. Consequently two additive magnitudes cannot cancel both checks unless both are zero. With nonzero first responses, the same condition says that all `B_r/A_r` are distinct. A single nonzero deviation is detected by the first check.

Coverage concerns at most two additive field deviations at modeled forward NTT boundary wires. Checker arithmetic, constants, comparisons, and control flow are trusted. Deviations at the same wire combine; exact cancellation leaves no result error. Shared corruptions that affect more than two modeled wires are outside this guarantee. The inverse NTT and matrix sampling are outside this protection. Physical injection resistance remains unmeasured.

## Intermediate variables

Let `P_l` map input to boundary `l`, and `S_k` map boundary `k` to output, so `T=S_k P_k`. The variable vector `u` is the checksum row at boundary `k`. A unit fault at boundary `l` is represented there by

```
w_r = P_k P_l^(-1) e_i
alpha = S_k^(-T) u
beta = P_k^T u
W_r(u) = w_r^T u / A_r
```

For `l<=k`, propagate the unit wire forward from `l` to `k`. For `l>k`, run inverse butterflies from `l` back to `k`. Every resulting intermediate vector is checked by propagating it to the final output and comparing with the independently derived unit wire formula used by the prior network model. This shares network modeling code, without reading prior checker constants or invoking its construction.

A wire before the intermediate boundary has `2^(k-l)` nonzero intermediate coordinates; a wire after it has `2^(l-k)`. At each intermediate coordinate the number of incident modeled wires is

```
K(k) = 2^(k+1) + 2^(h-k+1) - 3
M = n*(h+1)
D(k) = K(k)*M - K(k)*(K(k)+1)/2
```

There are at most `D(k)` pairs with at least one incident wire: subtract the pairs among the `M-K(k)` nonincident wires from all `M*(M-1)/2` pairs. Any pair difference with a nonzero coefficient at this coordinate belongs to that set. In particular its assigned constraint group has at most `D(k)` entries.

For `n=256`, `h=8`, and `k=4`, the generator verifies `M=2304`, `K=61`, and `D=138653`. The sufficient condition `8380417>138653` holds. It also verifies the exact incidence of 61 at every coordinate and the group bound. The largest group has exactly 138653 constraints.

## Greedy construction

For each pair form `H_rs=W_r-W_s`, verify that it is nonzero and assign it to its greatest nonzero coordinate `j`. Process coordinates in increasing physical index order. Maintain each form's evaluation on the already chosen prefix through the partial values of `W_r`. A constraint assigned to `j` forbids

```
u_j = -(H_rs evaluated on the prefix) / H_rs[j] mod q
```

Collect those values in a set and choose the smallest nonnegative value absent from it. At most `D(k)<q` choices are forbidden, so a choice exists. The search stops after at most the set size plus one membership checks and does not scan the whole field. Later coordinates cannot change already satisfied constraints.

After the assignment, compute all normalized responses. To make every second response nonzero, choose the smallest `t` outside `{ -W_r(u) }`. Replace the intermediate row by `u+t*c`, where `c=S_k^T a` is the first checksum row at boundary `k`. This adds `t` to every normalized response and preserves every pair determinant. The generated instance uses `t=1`. Only after this shift are the final output and input rows emitted.

The construction groups `M*(M-1)/2` constraints. With at most `s=max(2^k,2^(h-k))` nonzero coefficients per intermediate form, grouping takes `O(M^2*(s+log q))` field arithmetic work including modular inverses. Greedy evaluation takes `O(M^2+n*K)` further work. Constraint arrays occupy `O(M^2)` memory; sparse forms and incidence lists occupy `O(n*K)`. Network verification and the direct determinant certificate add polynomial work. These describe this exact integer implementation, rather than an optimized construction algorithm.

The improvement over the prior output coordinate recursion is the sufficient field bound obtained from intermediate support. The prior implementation uses `(2*n-1)*M=1177344` as its sufficient bound and fixes half its output weights to one. This construction uses `D=138653` and assigns every intermediate variable greedily. A smaller existence bound does not establish lower execution cost.

## Reproduction and certificate

```sh
python3 tools/gen_our_checker.py
python3 tools/gen_our_checker.py --check
```

The [certificate](our_certificate.json) records the unshifted intermediate assignment, smallest shift, group sizes, forbidden counts, and the exact network and coefficient digests. Runtime is printed separately so it does not affect deterministic artifacts. The coefficient digest covers full `b`, `a`, `beta`, and `alpha` in production order, serialized as little endian 32 bit words. The C tables store `a`, `beta`, and `alpha`; the all one input row is implicit.

The generator verifies both row identities by direct evaluation and graph pullback, both responses for every modeled wire, intermediate propagation, nonzero first and second responses, distinct normalized responses, and all 2653056 pair determinants independently of the greedy test. All failure counts are zero. A generation on this host took 6.642 seconds including certification. Regeneration is checked byte for byte against the emitted tables and certificate.

## C selection and correctness

`mldsa_ntt_forward_our(r,a)` computes expected checks from the input, calls the baseline NTT once, then computes and compares both output checks. It returns 0 on acceptance and -1 on a mismatch; discard its output on failure. There is no intermediate checksum during execution. Boundary 4 is used to construct the rows offline.

Define `MLDSA_OUR_CHECKER` to select this function through the existing internal `mldsa44_ntt` helper. Define `MLDSA_PRIOR_CHECKER` for the published defense, or neither for baseline. Selecting both is a compile error. Key generation, signing, and verification share their original algorithms and propagate a transform failure through their existing status returns.

The implementation uses three full 256 coefficient tables, including any zero or unity entries. The first input row is implicit ones. Every product and sum uses the existing canonical modular arithmetic, so the established [arithmetic bounds](arithmetic.md) apply. The reduction, division, and timing concerns in [ct.md](ct.md) also apply; this checker has no constant time claim.

```sh
make our prior build/libmldsa.so build/libmldsa_prior.so build/libmldsa_our.so
python3 test/test_smoke.py build/libmldsa_our.so build/nist
make -B our CC=clang
make -B our CC=gcc OPT='-O1 -g' SAN='-fsanitize=address'
make -B our CC=gcc OPT='-O1 -g' SAN='-fsanitize=undefined -fno-sanitize-recover=all'
make arm-mps2 arm-mps2-prior arm-mps2-our
python3 tools/run_mps2.py --our
```

The compact suite compares ten protected outputs against baseline: zero, unit vectors at positions 0, 127, and 255, all `q-1`, alternating `0`/`q-1`, and four fixed pseudorandom polynomials. Each inverse round trip must recover its entire input. Test hooks are the existing `MLDSA_TEST_FAULTS` boundaries, with no changes to the production transform.

Forty five single injections cover slots 0, 127, and 255 at boundaries 0, 1, 4, 7, and 8 with magnitudes 1, 17, and `q-1`. Ten pair selections with those three first magnitudes cover nearby and distant wires in one layer, adjacent layers, boundaries 1 and 7, boundaries 4 and 7, and input/output pairs. Each second magnitude is derived independently to cancel the first checksum. The test verifies that this cancellation occurs, that the final output differs from baseline, and that the protected transform rejects it. These 75 selected injections check the C implementation; the exhaustive algebraic certificate supplies complete modeled pair coverage.

The common entry point checks the NIST SHAKE case, deterministic key and signature digests, valid verification, modified message rejection, and modified signature rejection. Our variant additionally rejects a malformed signature with a hint count above 80, and checks that key generation, signing, and verification propagate an injected NTT failure. The official smoke tests compare complete NIST keyGen and sigGen outputs and check one valid and one invalid sigVer case for all three variants.

GCC 11.4.0, Clang 14.0.0, AddressSanitizer, and UndefinedBehaviorSanitizer passed the targeted suite without diagnostics. Baseline, prior, and our compact suites also passed QEMU 6.2.0 `mps2-an386`, built with ARM GCC 10.3.1. The existing prior checker source, constants, generator, certificate, and selected injections are unchanged. No large random campaigns were repeated.

The ARM toolchain overrides in [cortexm4.md](cortexm4.md) apply. This session restored extracted packages under ignored `build/toolchain/root`; use that absolute directory in place of the earlier `/tmp/mldsa-arm-toolchain/root` when repeating the recorded configuration.

## Measured provisional costs

```sh
make build/count_checkers arm-mps2-bench arm-mps2-prior-bench arm-mps2-our-bench
python3 tools/measure_checkers.py
```

The [comparison table](checker_costs.md) and [raw measurements](../bench/checker_costs.json) include all three variants. Per forward transform the prior checker adds 640 modular products and 1024 additions; our implementation adds 768 products and 1024 additions. There are no additional subtractions. Our three 256 term weighted rows account for the products and 3072 constant bytes. The four accumulated checksum rows account for the additions.

Matched benchmark images have ARM text sizes 11248, 14080, and 14576 bytes for baseline, prior, and our checker. Readonly tables are included in text. All have zero `.data` and 14876 bytes BSS. Our checker adds 3328 linked text bytes over baseline, or 496 over prior. Test injection code is absent from these images. All three benchmark counter availability paths report `DWT UNAVAILABLE` under this QEMU target and emit no observations.

The [our checker QEMU record](../test/qemu-mps2-an386-our.json) contains compact correctness results with the toolchain and emulator versions. These are functional validation and emulator layout sizes. Real DWT cycles and measured stack remain pending; [physical-stage software](../hardware/README.md) supplies reference targets and linked size reporting. [Focused formal verification](verification.md) is available with its documented component scope.
