# Focused implementation verification

This stage uses CBMC 6.10.0 and Z3 4.8.12 (the QF_AUFBV backend) for portable C implementation properties. It uses a 32 bit little endian integer and pointer model with i386 preprocessing, whose fixed width types and `unsigned` widths match this crypto core's Cortex M4 C types. It does not verify ARM machine code, startup code, ABI behavior, SHAKE, or the full ML DSA standard. No production C or generated crypto constants were changed.

The proof harnesses are in [verify/](../verify). The [arithmetic record](../verify/results_arithmetic.json) contains full commands, results, per job wall times, unwind bounds, tool versions, and SHA256 digests of production sources, harnesses, and generated proof views. Raw solver logs are in ignored `build/verify` and are identified by digest in the records. Passing a proof refers to all input values admitted by its documented preconditions, rather than random samples.

## Reproduction

The normal `cbmc` wrapper on this host selects version 5.12. The proofs explicitly use the installed 6.10.0 executable:

```sh
CBMC=/home/ishan/.local/toolchains/cbmc-6.10.0/usr/bin/cbmc \
  python3 verify/run.py --group arithmetic
CBMC=/home/ishan/.local/toolchains/cbmc-6.10.0/usr/bin/cbmc \
  python3 verify/run.py --group checkers
```

On another machine set `CBMC` to its version 6 executable. The runner rejects the older wrapper. `z3` must be on `PATH`. The version is pinned in the recorded evidence; a different version requires a new verification run.

This host lacks 32 bit libc development headers. Only the preprocessing headers were extracted locally; no system packages were installed:

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

`SOURCES`, `ENTRY`, extra defines, and `BOUND` are given below. Include flags for the local preprocessing headers appear in the JSON commands. Unwinding assertions are enabled in every job. All loop checks passed, including their unwinding assertions; scalar jobs contain no reachable loops. See the [CBMC documentation](https://diffblue.github.io/cbmc/cbmc-tutorial.html) for bounded checking and the role of unwinding assertions. No partial loop option or assertion to assumption conversion is used.

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
6. The harnesses construct valid full sized, live, disjoint objects. Null, dangling, too short, and overlapping pointers violate the documented interface; there is no assumed arbitrary pointer validity predicate hiding such cases.

There are no assumptions about selected input vectors, zero coefficients, small fault magnitudes, successful checker return codes, or already equal checksum values. No assumption is added merely to avoid a timeout. CBMC, Z3, their frontend/library models, the source view extractor, and the exact arithmetic certificate generators are trusted tools. No physical hardware behavior is an assumption or a result of this stage.

The 19 arithmetic, layer, and NTT memory jobs passed. Their recorded wall times total 65.023 seconds, with no individual job exceeding the 45 second limit and no timeouts. This is the sum of individual job times, rather than overall stage elapsed time.
