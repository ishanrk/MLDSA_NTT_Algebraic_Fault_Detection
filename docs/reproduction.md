# Reproduction

Run commands from the repository root.

## Tools

The host code needs Make, GCC or Clang, and Python 3.10+. ARM builds need GNU Arm GCC/binutils and Newlib. QEMU must provide the `mps2-an386` machine; instruction benchmarks additionally need TCG plugin support and Matplotlib. Formal checks use CBMC 6 and Z3. The comprehensive differential suite uses `pqcrypto==1.0.0` as a test oracle, installed into ignored `build/oracle` when needed.

Recorded versions, flags, input/source digests and commands are in [comparison.json](../bench/comparison.json), [QEMU results](../bench/qemu_benchmark.json), the [arithmetic proof record](../verify/results_arithmetic.json) and the [checker proof record](../verify/results_checkers.json). Physical Cortex M4 cycles and stack high water are unmeasured.

## Correctness and certificates

```sh
make baseline prior our
python3 tools/gen_prior_checker.py --check
python3 tools/gen_our_checker.py --check
```

The correctness suites exercise selected NTT vectors, inverse round trips, deterministic scheme operations, malformed message/signature rejection and modeled single/pair faults. `--check` reconstructs coefficients and every pair determinant and requires byte identity with the C tables and certificate JSON. The full official vector targets are `make keygen sign verify prehash shake`; `make vectors` fetches pinned NIST data into `build/nist`.

## QEMU measurements and graphs

```sh
make qemu-benchmark
python3 tools/plot_benchmarks.py
```

The benchmark builds baseline, Abdelmonem et al. and current variants at both `-O2` and `-O3 -flto`, runs the correctness images, and records 101 observations of each operation. A QEMU plugin counts ARM instructions between markers; the minimum empty marker count is subtracted. A fixed assembly control must add exactly 301 instructions, and complete key/signature transcripts must be identical across all six builds. [Counter implementation](../tools/qemu_counter.c), [statistics](qemu_results.md), [raw observations](../bench/qemu_benchmark.json). The second command redraws PNG/SVG graphs and updates README tables from the saved data. These counts are not physical cycles.

## Focused comparison and formal checks

```sh
make comparison
python3 verify/run.py --group arithmetic
python3 verify/run.py --group checkers
```

`make comparison` runs the focused GCC/Clang/sanitizer suites, both certificates, formal groups, field operation counters, six ARM images and three QEMU correctness runs. It generates [JSON](../bench/comparison.json) and [LaTeX](../bench/comparison.tex). A failed command stops publication. Use `python3 tools/render_comparison.py bench/comparison.json` to redraw LaTeX tables without rerunning experiments. An optional `--markdown` path writes a separate report when requested.

Set `CBMC` to the installed version 6 executable. The records contain every command, property result, unwind bound, runtime and source digest. The runner uses Z3, a 32 bit little endian model, unwinding assertions and a 45 second limit per job. Scalar jobs use unwind `1`; layer and memory jobs use `257`. The [runner](../verify/run.py) defines the complete selection.

The component proofs cover modular arithmetic, centered conversions, forward and inverse butterflies, each forward layer, complete loop memory safety, checksum initialization, accumulation and decisions. Arithmetic substitutions use independently proved range contracts; layer and checksum harnesses check their operands. No single query proves the full transform, ML-DSA, SHAKE or ARM machine code. No fault acceptance combines these component results with the exact row certificates.

The harness preconditions and composition assumptions are:

1. Canonical operands and coefficients are in `[0,8380417)`.
2. Centered inputs to `mldsa_uncenter` are in `[-4190208,4190208]`.
3. Symbolic butterfly indices select a valid layer, block and pair; every production pair is included.
4. Symbolic checksum prefix accumulators are canonical; separate jobs check zero initialization and range preservation.
5. Substituted arithmetic results and baseline NTT outputs are canonical and side effect free. Scalar and full loop proofs establish the range contracts; layer and checksum substitutions also assert the exact operands.
6. Harnesses allocate valid, full sized, live, disjoint input/output objects. Null, dangling and short pointers violate this contract. Pointwise in place aliasing is outside the memory proof scope.

The [harnesses](../verify) contain the assumptions. CBMC, Z3, the [source view extractor](../verify/source_views.py) and certificate generators are trusted tools. There are no assumptions of successful checksum decisions or already equal checksums. The proofs do not establish physical fault resistance.

If the host lacks 32 bit libc preprocessing headers, install them or extract them locally:

```sh
mkdir -p build/verify/headers
cd build/verify/headers
apt-get download libc6-dev-i386
dpkg-deb -x libc6-dev-i386_*.deb root
cd ../../..
```

The runner detects that include root. Additional include flags can be supplied in `CBMC_INCLUDES` and are recorded in each command.

## Tool overrides

The commands honor `ARM_CC`, `ARM_OBJCOPY`, `ARM_SIZE`, `ARM_INC`, `ARM_LIB`, `QEMU` and `QEMU_LIBDIR`. The instruction benchmark additionally accepts `ARM_NM` and automatically locates tools extracted under `build/toolchain/root`. For other Make targets using that local extraction:

```sh
export ARM_CC="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-gcc"
export ARM_OBJCOPY="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-objcopy"
export ARM_SIZE="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-size"
export ARM_INC="-isystem $PWD/build/toolchain/root/usr/include/newlib"
export ARM_LIB="-L$PWD/build/toolchain/root/usr/lib/arm-none-eabi/newlib/thumb/v7e-m/nofp"
export QEMU="$PWD/build/toolchain/root/usr/bin/qemu-system-arm"
export QEMU_LIBDIR="$PWD/build/toolchain/root/usr/lib/x86_64-linux-gnu"
```

Installed toolchains normally need none of these overrides. Select CBMC with `export CBMC=/path/to/cbmc`; the version 6 executable must match the proof configuration. Dependencies under `build` are not tracked repository files. Avoid `make clean` if they must be retained.

## Physical target and thesis tables

[Hardware instructions](../hardware/README.md) cover explicit F411RE/F446RE builds, board identification, flashing, serial acquisition, DWT calibration and total stack watermarks. `python3 hardware/offline.py` checks the software path and produces linked image sizes without a board. Its synthetic counter controls supply no physical timing observations. WSL USB access follows [Microsoft's guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).

`make thesis` runs the comprehensive regression and regenerates the [thesis tables](thesis_results.md). `python3 tools/render_thesis.py bench/thesis.json` redraws them without repeating experiments. Include a fragment with `\input{bench/thesis/performance_our.tex}`; `bench/thesis/tables.tex` lists all fragments. Adjust paths for a separate thesis project.

After physical capture, use `python3 tools/final_regression.py --physical-manifest /absolute/path/to/run/run.json` to validate and incorporate the recorded observations. Acquisition is the separate board action described in the hardware guide. Historical result records retain the names and source digests of their original runs.
