# Provisional Cortex M4 target

The generic Cortex M4 build boots and passes a compact correctness suite under QEMU. QEMU is used only for functional validation. Physical Nucleo measurements are deferred until hardware is available; they are not a prerequisite for continuing implementation or research.

The complete current comparison is produced by `make comparison`; see the [reproduction guide](reproduction.md) and [generated tables](comparison.md). This command includes both certificates and focused formal checks, in addition to matched builds and QEMU correctness.

## Execution target

| Item | Validated configuration |
| --- | --- |
| Machine | QEMU `mps2-an386`, an Arm MPS2 Cortex M4 model |
| Emulator | QEMU 6.2.0, Debian package `1:6.2+dfsg-2ubuntu6.31` |
| Compiler | `arm-none-eabi-gcc` 10.3.1 20210621, package `15:10.3-2021.07-4` |
| Architecture | `-mcpu=cortex-m4 -mthumb -mfloat-abi=soft` |
| C flags | `-std=c11 -O2 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow` |
| Link flags | `-nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2.map -Tplatform/cortexm4/mps2.ld -lc -lgcc` |
| Output and exit | Arm semihosting `SYS_WRITE0` and `SYS_EXIT_EXTENDED` |

The linker layout follows the [QEMU MPS2 AN386 model](https://www.qemu.org/docs/master/system/arm/mps2.html): 4 MiB of code SRAM at `0x00000000` and 4 MiB of data SRAM at `0x20000000`. It reserves 256 KiB for the main stack. This is an emulator layout, not a Nucleo flash or RAM configuration. The soft ABI is provisional; the crypto uses no floating point.

With the ARM compiler, binutils, Newlib, and QEMU installed:

```sh
make arm-mps2
python3 tools/run_mps2.py
```

The Makefile accepts `ARM_CC`, `ARM_OBJCOPY`, `ARM_SIZE`, `ARM_INC`, and `ARM_LIB` overrides. The runner accepts `ARM_CC`, `QEMU`, and optional `QEMU_LIBDIR`. The validation used extracted Ubuntu packages under `/tmp/mldsa-arm-toolchain/root` with these overrides:

```sh
make arm-mps2 \
  ARM_CC=/tmp/mldsa-arm-toolchain/root/usr/bin/arm-none-eabi-gcc \
  ARM_OBJCOPY=/tmp/mldsa-arm-toolchain/root/usr/bin/arm-none-eabi-objcopy \
  ARM_SIZE=/tmp/mldsa-arm-toolchain/root/usr/bin/arm-none-eabi-size \
  ARM_INC='-isystem /tmp/mldsa-arm-toolchain/root/usr/include/newlib' \
  ARM_LIB='-L/tmp/mldsa-arm-toolchain/root/usr/lib/arm-none-eabi/newlib/thumb/v7e-m/nofp'
QEMU=/tmp/mldsa-arm-toolchain/root/usr/bin/qemu-system-arm \
  ARM_CC=/tmp/mldsa-arm-toolchain/root/usr/bin/arm-none-eabi-gcc \
  QEMU_LIBDIR=/tmp/mldsa-arm-toolchain/root/usr/lib/x86_64-linux-gnu \
  python3 tools/run_mps2.py
```

## Compact correctness suite

All ten checks passed. The [functional record](../test/qemu-mps2-an386.json) contains the compiler, emulator, command, and individual results; it contains no performance measurements.

- SHAKE256: official NIST ACVP FIPS 202 case `tcId 188`, a 21 byte input and 32 byte output.
- NTT: zero, the basis vector `X`, alternating `0` and `q-1`, and one fixed pseudorandom polynomial. Each forward transform is compared through a digest against independent polynomial evaluation, and each inverse must recover every input coefficient exactly.
- ML DSA 44: one deterministic key generation, one deterministic signing, one successful verification, one modified message rejection, and one modified signature rejection.

The key generation uses the first ML DSA 44 case in the pinned official NIST ACVP data. The deterministic signature fixture uses that official secret key and the previously validated host signer with message `Cortex M4 portable baseline`, context `arm`, and `rnd` bytes `0..31`. It is a host comparison fixture, not a separate official signing vector. The SHAKE input and expected output come directly from official data. [fips204.md](fips204.md) records the NIST repository and pinned revision.

`tools/gen_arm_vectors.py` computes the NTT expectations independently by evaluating each polynomial at `1753^(2*BitRev8(i)+1)` modulo `8380417`. It serializes canonical coefficients as little endian 32 bit words and hashes them with Python SHAKE256. The fixed random case uses a 32 bit recurrence `x = 1664525*x + 1013904223`, starting at `20446`, followed by reduction modulo `q`.

To regenerate or check these small fixtures when needed:

```sh
make build/libmldsa.so vectors
python3 tools/gen_arm_vectors.py
python3 tools/gen_arm_vectors.py --check
```

No ARM crypto replacement or coefficient representation change is involved. The full portable suites were validated in the previous stage and were not rerun for this integration change.

## Benchmark scaffold

```sh
make arm-mps2-bench
python3 tools/summarize_bench.py physical-run.jsonl
```

The same toolchain overrides apply to the benchmark build. This firmware and its DWT/stack helpers are provisional. They have compiled, but physical timing and stack behavior have not been validated.

`platform_dwt_init` enables trace access, checks cycle counter support, clears and enables `DWT_CYCCNT`, and checks that it advances. The register addresses and control bits come from the Arm Cortex M4 processor documentation. QEMU 6.2.0 reports the counter unavailable for this machine; the benchmark exits with `DWT UNAVAILABLE` and emits no observations. Even if a future emulator provides a counter, its output must not be used as real performance data.

On a physical target the harness is prepared to record 101 samples each for the forward NTT, inverse NTT, pointwise multiplication, and verification, and 31 each for key generation and signing. It captures the end counter immediately after each operation, checks return values afterward, and subtracts the minimum of 101 pairs of counter reads. Unsigned subtraction handles a single wrap; each timed interval must remain shorter than `2^32` counter ticks. Counter calibration and this bound still need confirmation on hardware. Signing varies explicit `rnd` input and retains standardized rejection behavior. All output occurs after the timed loops.

A separate pass fills the unused reserved stack below the current main stack pointer with `0xa55aa55a`, then scans for overwritten words after NTT, key generation, signing, and verification. The estimate is additional depth below the measurement call site and can include helper frames; it is not total RAM use or an exhaustive worst case. The physical linker must reserve enough memory before enabling this method. Cycle and stack records use separate JSON fields. The summary tool reports cycle sample count, minimum, median, and maximum. No physical observations are checked in yet.

For a future physical run record the exact board, MCU, clock setup, compiler and flags, firmware commit, and output transport alongside the raw observations.

## Physical work pending

| Item | Status |
| --- | --- |
| Exact Nucleo board and MCU | Pending |
| Physical linker layout and startup details | Pending |
| Clock setup and frequency | Pending |
| ST Link flashing and serial output | Pending |
| Real DWT cycle counts and harness calibration | Pending |
| Physical flash and static RAM usage | Pending |
| Physical stack measurements | Pending |

A physical target will supply its linker script, startup/clock setup, and implementations of `platform_write` and `platform_done`. The DWT and stack interfaces remain separate from the crypto API. No cryptographic redesign is required to add the board. Current large matrix and vector stack objects still need review against the selected MCU's RAM budget.

## ARM audit

With this compiler and configuration, disassembly shows `mldsa_mul` using `umull` and `__aeabi_uldivmod`; its `__udivmoddi4` callee uses `udiv` and conditional branches. Each NTT butterfly uses modular multiplication. `mldsa_add` branches on the coefficient sum; `mldsa_sub` uses conditional Thumb instructions. `mldsa44_norm` exits early, and `mldsa44_sample_ball` uses a sampled coefficient index for a load and store. These observations are recorded in [ct.md](ct.md). They establish neither timing nor side channel security. No arithmetic optimization was made in this stage.

## Testing policy

Use targeted tests during development: arithmetic tests for arithmetic edits, the selected NTT cases and a small fixed random sample for NTT edits, checker tests plus a small baseline NTT comparison for checker edits, encoding tests for encoding edits, and the compact suite above for ARM integration. Run complete regression and official NIST validation at major milestones: completion of each checker, formal verification, and the final thesis artifact. Keep exhaustive mathematical location/determinant certificates whenever they are part of a research result.

## Prior checker target

The [prior checker](prior_checker.md) also passes this machine's compact suite, including eight baseline/protected NTT comparisons, 66 selected runtime wire injections, and error propagation through the scheme API. Build with `make arm-mps2-prior` and run `python3 tools/run_mps2.py --prior`; the same compiler and QEMU overrides above apply. The results are recorded in [qemu-mps2-an386-prior.json](../test/qemu-mps2-an386-prior.json).

`make arm-mps2-prior-bench` builds the matched protected benchmark image. Its forward timing/stack hook selects the protected transform, and key generation checks its new return status. Neither benchmark image contains injection hooks. Both counter-unavailable paths were smoke tested and emitted no observations. The [generated cost table](prior_costs.md) reports linked emulator image sizes and counted field operations. Physical measurements remain pending.

## Our checker target

The [intermediate boundary checker](our_checker.md) passes the same Cortex M4 emulator. `make arm-mps2-our` builds its compact suite, and `python3 tools/run_mps2.py --our` checks the expected output and writes the [functional record](../test/qemu-mps2-an386-our.json). It includes ten selected NTT comparisons and round trips, 45 single fault cases, 30 first checksum cancelling pairs, and the shared ML DSA/SHAKE checks. A malformed signature case and injected failure propagation through each scheme API also pass.

`make arm-mps2-our-bench` builds the protected benchmark without fault hooks. The forward benchmark selects our checker and the shared scheme algorithms use it through `MLDSA_OUR_CHECKER`. Its QEMU counter availability path reports `DWT UNAVAILABLE` and produces no timing or stack observations.

`make comparison` generates the [three variant comparison](comparison.md), including actual modular calls, matched ARM images and current certificate/formal/QEMU evidence. The lower level `make build/count_checkers` and `python3 tools/measure_checkers.py` remain cost-only collection commands. Physical measurement work is pending. The extracted toolchain is under ignored `build/toolchain/root`; the [reproduction guide](reproduction.md#tool-overrides) gives current overrides for it.
