# Reproduction

Run commands from the repository root.

## Tools

The host code needs Make, GCC or Clang, and Python 3.10+. ARM builds need GNU Arm GCC/binutils and Newlib. QEMU must provide the `mps2-an386` machine; instruction benchmarks additionally need TCG plugin support and Matplotlib. Formal checks use CBMC 6 and Z3. The comprehensive differential suite uses `pqcrypto==1.0.0` as a test oracle, installed into ignored `build/oracle` when needed.

Recorded versions, flags, input/source digests and commands are in [comparison.json](../bench/comparison.json), [QEMU results](../bench/qemu_benchmark.json) and the [formal records](verification.md). Physical Cortex M4 cycles and stack high water are unmeasured.

## Correctness and certificates

```sh
make baseline prior our
python3 tools/gen_prior_checker.py --check
python3 tools/gen_our_checker.py --check
```

The correctness suites exercise selected NTT vectors, inverse round trips, deterministic scheme operations, malformed-message/signature rejection and modeled single/pair faults. `--check` reconstructs coefficients and every pair determinant and requires byte identity with the C tables and certificate JSON. The full official-vector targets are `make keygen sign verify prehash shake`; `make vectors` fetches pinned NIST data into `build/nist`.

## QEMU measurements and graphs

```sh
make qemu-benchmark
python3 tools/plot_benchmarks.py
```

The benchmark builds baseline, prior and our variants at both `-O2` and `-O3 -flto`, runs the correctness images, and records 101 observations of each operation with calibrated guest-instruction counts. It checks the fixed assembly control and matching complete key/signature transcripts. [Method](qemu_benchmark.md), [statistics](qemu_results.md), [raw observations](../bench/qemu_benchmark.json). The second command redraws PNG/SVG graphs and updates README tables from the saved data.

## Focused comparison and formal checks

```sh
make comparison
python3 verify/run.py --group arithmetic
python3 verify/run.py --group checkers
```

`make comparison` runs the focused GCC/Clang/sanitizer suites, both certificates, formal groups, field-operation counters, six matched ARM images and three QEMU correctness runs. It generates [Markdown](comparison.md), [JSON](../bench/comparison.json) and [LaTeX](../bench/comparison.tex). A failed command stops publication. Use `python3 tools/render_comparison.py bench/comparison.json` to redraw tables without rerunning experiments.

Set `CBMC` if the default executable is not version 6. The 32-bit proof frontend may need the headers described in [verification.md](verification.md#reproduction). Every proof enables unwinding assertions and has a 45-second job limit. The exact scope and preconditions are documented there.

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

Installed toolchains normally need none of these overrides. Select CBMC with `export CBMC=/path/to/cbmc`; the version-6 executable must match the proof configuration. Dependencies under `build` are not tracked repository files. Avoid `make clean` if they must be retained.

## Physical target and thesis tables

[Hardware instructions](../hardware/README.md) cover explicit F411RE/F446RE builds, board identification, flashing, serial acquisition, DWT calibration and total stack watermarks. `python3 hardware/offline.py` checks the software path and produces linked image sizes without a board. Its synthetic counter controls supply no physical timing observations. WSL USB access follows [Microsoft's guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).

`make thesis` runs the comprehensive regression and regenerates the [thesis tables](thesis_results.md). [Thesis reproduction](thesis_reproduction.md) explains capture import and LaTeX inclusion. Historical result records retain the names and source digests of their original runs; current commands and filenames are documented here.
