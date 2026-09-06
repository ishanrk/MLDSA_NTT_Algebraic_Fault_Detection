# Focused implementation verification

The proofs use CBMC 6.10.0 and Z3 4.8.12 (the QF_AUFBV backend) for portable C implementation properties. It uses a 32 bit little endian integer and pointer model with i386 preprocessing, whose fixed width types and `unsigned` widths match this crypto core's Cortex M4 C types. It does not verify ARM machine code, startup code, ABI behavior, SHAKE, or the full ML DSA standard. The production arithmetic and generated checksum constants are the subjects of the proofs.

The proof harnesses are in [verify/](../verify). The [arithmetic record](../verify/results_arithmetic.json) and [checker record](../verify/results_checkers.json) contain full commands, results, per job wall times, unwind bounds, tool versions, and SHA256 digests of production sources, harnesses, and generated proof views. Raw solver logs are in ignored `build/verify` and are identified by digest in the records. Passing a proof refers to all input values admitted by its documented preconditions, rather than random samples.

## Reproduction

Use CBMC 6 and Z3 on the executable path, or select CBMC explicitly:

```sh
CBMC=/path/to/cbmc python3 verify/run.py --group arithmetic
CBMC=/path/to/cbmc python3 verify/run.py --group checkers
```

The records identify CBMC 6.10.0 and Z3 4.8.12. Other versions require a new run. The runner rejects CBMC 5.

On hosts without 32-bit libc development headers, install them or extract the preprocessing headers locally:

```sh
mkdir -p build/verify/headers
cd build/verify/headers
apt-get download libc6-dev-i386
dpkg-deb -x libc6-dev-i386_*.deb root
```

The runner detects the extracted include root and adds it along with `/usr/include/x86_64-linux-gnu`. An installation with ordinary 32 bit development headers needs no extraction. Additional platform include flags can be supplied through `CBMC_INCLUDES`; every used flag is saved in the result command.

Every job has a 45 second wall time limit. On timeout the runner kills the entire CBMC and solver process group and records a timeout, rather than success. It checks that sources stayed unchanged during the run. Generated source views are written atomically. A failed proof, timeout, parsing error, missing verification success marker, or failed unwinding assertion makes the group fail.

All recorded CBMC commands use these common checks:

```sh
$CBMC SOURCES -Iinclude -Ibuild/verify --arch i386 --32 --little-endian \
  --bounds-check --pointer-check --pointer-overflow-check \
  --signed-overflow-check --unsigned-overflow-check --conversion-check \
  --undefined-shift-check --unwinding-assertions --drop-unused-functions --z3 \
  --function ENTRY --unwind BOUND
```

`SOURCES`, `ENTRY`, extra defines, and `BOUND` are given below. Include flags for the local preprocessing headers appear in the JSON commands. Unwinding assertions are enabled in every job. All loop checks passed, including their unwinding assertions; scalar jobs contain no reachable loops. See the [CBMC documentation](https://github.com/diffblue/cbmc/blob/develop/doc/cprover-manual/cbmc-tutorial.md) for bounded checking and the role of unwinding assertions. No partial loop option or assertion to assumption conversion is used.

## Arithmetic properties

| Property and entry | Production function | Preconditions | Sources | Unwind | Result |
| --- | --- | --- | --- | ---: | --- |
| `reduce` | `mldsa_reduce` | Any `uint64_t` | `verify/arithmetic.c src/poly.c` | 1 | Passed |
| `add` | `mldsa_add` | Both operands in `[0,q)` | Same | 1 | Passed |
| `sub` | `mldsa_sub` | Both operands in `[0,q)` | Same | 1 | Passed |
| `mul` | `mldsa_mul` | Both operands in `[0,q)` | Same | 1 | Passed |
| `center` | `mldsa_center`, `mldsa_uncenter` | Input in `[0,q)` | Same | 1 | Passed |
| `uncenter` | `mldsa_uncenter`, `mldsa_center` | Input in `[-4190208,4190208]` | Same | 1 | Passed |

These jobs call the actual production bodies. They prove agreement with ordinary 64 bit modular specifications, canonical result bounds, safe narrowing, and both centered/canonical round trips. The multiplication job additionally verifies the documented maximum unreduced product, `70231372333056`. All enabled signed/unsigned overflow and conversion checks passed. There are no Montgomery or lazy representation conversions in these functions.

## Butterflies and layer composition

The [source view tool](../verify/source_views.py) extracts the exact innermost butterfly and full layer loop text from `src/ntt.c`, with no arithmetic rewrites. It also extracts checker loop bodies and decisions. These generated views stay in ignored `build/verify`; production source and view hashes tie the records to the text actually compiled. The extraction tool and its structural guards are trusted tooling and are not themselves formally verified.

| Property | Production region | Entry and sources | Extra define | Unwind | Result |
| --- | --- | --- | --- | ---: | --- |
| Forward butterfly | Inner loop in `mldsa_ntt_forward` | `butterfly`, `verify/butterfly.c` | None | 1 | Passed |
| Inverse butterfly | Inner loop in `mldsa_ntt_inverse` | Same | `-DINVERSE` | 1 | Passed |
| Each complete forward layer 0 through 7 | Block and butterfly loops in `mldsa_ntt_forward` | `layer`, `verify/layer.c` | `-DLAYER=0` through `-DLAYER=7`, separate jobs | 257 | All eight passed |

The forward specification is `(u+t mod q, u-t mod q)` for `t=z*v mod q`. The unscaled production inverse specification is `(u+v mod q, z*(u-v) mod q)`, using the inverse loop's twiddle `z`. Neither assertion claims that one unscaled inverse butterfly alone reverses the corresponding forward butterfly.

The butterfly harness allows all canonical `u,v,z`, all eight butterfly distances, every valid block and pair position, and an arbitrary canonical multiplication result. It checks that the multiply receives the right operands and that actual production addition and subtraction implement the two specified updates. The multiplication implementation was separately proved; its return is substituted by an arbitrary canonical value. Thus the proof covers the concrete product as well as every other value admitted by that overapproximation.

Each full layer harness starts with 256 arbitrary canonical coefficients, the correct layer distance, and the correct starting twiddle index. It executes the actual extracted production input copy loop, then independently enumerates the 128 specification pairs. Contract operations assert the exact expected twiddle and original coefficient arguments and return arbitrary canonical products, sums, and differences. It verifies every final coefficient, all 128 pairs, and the final twiddle index. Combining this routing proof with the scalar arithmetic proofs gives the mathematical layer update. All eight concrete layers are checked; this is not a single end to end transform equivalence query.

## Full loop safety

| Entry | Production function | Sources | Unwind | Result |
| --- | --- | --- | ---: | --- |
| `forward_memory` | `mldsa_ntt_forward` | `verify/ntt_memory.c src/ntt.c` | 257 | Passed |
| `inverse_memory` | `mldsa_ntt_inverse` | Same | 257 | Passed |
| `pointwise_memory` | `mldsa_ntt_mul` | Same | 257 | Passed |

These harnesses execute all production loops on full 256 coefficient objects. They assume canonical input coefficients and use distinct live input/output objects. Arithmetic calls assert canonical operands, then return arbitrary canonical results under the proved arithmetic contracts. All array/pointer checks, twiddle table indices, loop/index arithmetic, conversions, shifts, and result range assertions passed. The inverse scaling constant is also checked as a valid multiplication operand. The contracts deliberately overapproximate numerical behavior, so these are safety proofs and not transform round trip proofs.

## Assumptions and trusted components

All explicit assumptions are either documented caller ranges or established compositional postconditions:

1. Canonical scalar and coefficient inputs satisfy `0<=x<8380417`, as required by [arithmetic.md](arithmetic.md).
2. Centered input lies in `[-4190208,4190208]`, the documented `mldsa_uncenter` range.
3. Symbolic butterfly indices select an actual layer, block, and pair. These assumptions name the region being verified, without excluding any production pair.
4. Arbitrary checksum prefix accumulators are canonical. The zero initialization and preservation of this invariant are checked separately.
5. Replacement arithmetic results and baseline NTT output coefficients are canonical. Arithmetic range is proved on the production scalar functions and propagated through full loop safety. Replacements are side effect free. Layer and checksum replacements additionally check the exact operands.
6. The harnesses construct valid full sized, live, disjoint objects. The baseline NTT and checker jobs follow their documented nonoverlap contract. The pointwise safety job covers disjoint objects; permitted in place pointwise aliasing is outside its scope. Null, dangling, and too short pointers violate the valid object contract. There is no assumed arbitrary pointer validity predicate hiding such cases.

There are no assumptions about selected input vectors, zero coefficients, small fault magnitudes, successful checker return codes, or already equal checksum values. No assumption is added merely to avoid a timeout. CBMC, Z3, their frontend/library models, the source view extractor, and the exact arithmetic certificate generators are trusted tools. Physical hardware behavior is outside these proofs.

The arithmetic, layer, and NTT memory jobs passed, with no individual job exceeding the recorded per job limit and no timeouts. The current count and summed per job wall times are in the [arithmetic record](../verify/results_arithmetic.json); they are not overall stage elapsed time or hardware cycles.

## Algebraic checker specifications

For input column `p` and returned NTT column `r`, the specification of the four local accumulators is

```
x = sum(p[i]) mod q
y = sum(beta[i]*p[i]) mod q
u = sum(a[i]*r[i]) mod q
v = sum(alpha[i]*r[i]) mod q
accept exactly when x == u and y == v
```

The prior output row uses `alpha[i]=1` at odd physical indices and its stored `prior_alpha[i/2]` at even indices. Our checker uses the full `our_alpha[i]` table. The specification uses the exact generated production rows whose identities are established in their certificates. An individual product is formed in 64 bits and reduced modulo `q`. The summation specification is a fold starting at zero: `S_next=(S+term) mod q`.

| Property and entry | Production region | Sources | Extra define | Unwind | Result |
| --- | --- | --- | --- | ---: | --- |
| `base` | Accumulator initialization in `mldsa_ntt_forward_prior` | `verify/checker_step.c` | `-DPRIOR` | 1 | Passed |
| `input_step` | Prior input checksum loop body | Same | `-DPRIOR` | 1 | Passed |
| `output_step` | Prior output checksum loop body | Same | `-DPRIOR` | 1 | Passed |
| `decide` | Prior final return expression | Same | `-DPRIOR` | 1 | Passed |
| `memory` | Entire `mldsa_ntt_forward_prior` | `verify/checker_memory.c src/prior.c` | `-DPRIOR` | 257 | Passed |
| `base` | Accumulator initialization in `mldsa_ntt_forward_our` | `verify/checker_step.c` | None | 1 | Passed |
| `input_step` | Our input checksum loop body | Same | None | 1 | Passed |
| `output_step` | Our output checksum loop body | Same | None | 1 | Passed |
| `decide` | Our final return expression | Same | None | 1 | Passed |
| `memory` | Entire `mldsa_ntt_forward_our` | `verify/checker_memory.c src/our.c` | None | 257 | Passed |

The initialization proofs use the actual extracted declaration. Step proofs allow every physical coefficient index and every canonical prefix accumulator. They verify the correct table weight and coefficient operands, then verify the actual production addition against the modular fold specification. Multiplication is replaced by an arbitrary canonical result of a call with those checked operands, using the separately proved multiplication contract. This verifies weighted and ordinary sums, the prior odd/even layout, all generated array accesses, canonical result bounds, and safe index/representation conversions. There is no additional Montgomery conversion.

Induction on the unchanged `i=0; i<256; i++` loop headers combines the proved zero base case and arbitrary index step with the arithmetic contract. It establishes that all four C accumulators equal the fold specification. This composition argument is explicit; CBMC does not automatically prove a 256 term dot product identity with a single nonlinear solver query. The source view tool checks the original checker function structure, including its initialization, both complete loop headers, the intervening baseline call, and the final return.

The decision proofs cover every four `uint32_t` words, so they also cover all canonical checksum values. They prove exact equivalence to the two equality tests and prove acceptance when called with `(x,y,x,y)`, without assuming a successful return value.

The full wrapper safety proofs execute both complete checksum loops and their final decision from the actual production files. Their NTT contract writes an arbitrary canonical output to the supplied result object. CBMC verifies that the wrapper calls the baseline exactly once with the original arguments, never changes the input, preserves every returned NTT coefficient, and returns only 0 or -1. Output preservation holds even for rejected outputs. This contract is an overapproximation of all baseline results, not an assumption that the NTT is the identity.

## No fault acceptance and scope

When the baseline produces the mathematical result `r=T*p`, the concrete certificate identities `b=T^T*a` and `beta=T^T*alpha`, with `b` all ones, give `x=u` and `y=v`. The verified accumulator folds and decision then give acceptance. The verified layer updates, their input copy, and the production layer schedule support this compositional use of the forward transform. Both checker variants preserve the baseline output under the stronger arbitrary-output wrapper proof.

The no fault acceptance result therefore combines CBMC implementation lemmas with the exact network/row certificate. There is no end to end CBMC job containing the complete numerical NTT and both complete numerical checksum computations. The layer schedule and the assembly of the component lemmas are inspected reasoning, rather than an automatically checked global refinement proof. An independently machine checked assembly of that global proof remains outside this result.

The general two fault determinant theorem and the greedy construction theorem are not CBMC targets. The unchanged exact generators certify the concrete coefficient conditions for all 2304 locations and 2653056 pairs for each checker. Mathematical field properties and those certificates are part of the compositional argument. The proofs do not cover the generator algorithms themselves, inverse transform functional equivalence or round trips, polynomial ring multiplication end to end, ML DSA key/signature logic, SHAKE, constant time behavior, physical faults, or ARM machine instructions.

## Validation records

The checker proof jobs passed under the recorded unwind bounds with no timeouts or failed unwinding assertions. Current counts and summed per job wall times are in the [checker record](../verify/results_checkers.json) and the [generated comparison](comparison.md). Reproduction updates the JSON evidence without requiring hand edits to timing statements.

Two [negative controls](../verify/negative_controls.json) introduced deliberate mistakes only in temporary proof views: replacing our input beta weight with our output first weight, and loading a forward layer's low wire as its high input. Both produced the expected assertion counterexample and CBMC exit status 10. To reproduce a control, copy its named view into `build/verify/negative`, apply the recorded textual substitution, execute its saved command, and remove that temporary view. The original generated views and production files stay intact.

The corresponding correctness commands are

```sh
make -B baseline prior our CC=gcc
make -B baseline prior our CC=clang
make -B baseline prior our CC=gcc OPT='-O1 -g' SAN='-fsanitize=address'
make -B baseline prior our CC=gcc OPT='-O1 -g' SAN='-fsanitize=undefined -fno-sanitize-recover=all'
python3 tools/gen_prior_checker.py --check
python3 tools/gen_our_checker.py --check
make arm-mps2 arm-mps2-prior arm-mps2-our
python3 tools/run_mps2.py
python3 tools/run_mps2.py --prior
python3 tools/run_mps2.py --our
```

GCC, Clang, ASan, UBSan and the three QEMU correctness suites passed in the recorded runs. Both exact certificates matched the checked-in coefficient data and had zero failures. The [comprehensive regression record](../bench/thesis.json) also embeds both formal groups; [generated tables](thesis_results.md) report every job and runtime.

These records describe portable C component proofs with inspected composition. They do not add a global refinement proof or formal verification of the hardware drivers. Physical DWT/stack measurements remain unmeasured.
