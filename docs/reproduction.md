# Reproduce the research artifact

Run from the repository root. No physical board is needed. All evidence is for the portable C implementation and the QEMU Cortex M4 path; physical performance and physical fault injection are unmeasured.

## Tools

Use Python 3.10 or later, Make, GCC, Clang, ARM GNU GCC/binutils with Newlib, `qemu-system-arm`, CBMC 6 and Z3 on `PATH`. No third party Python package is required. Recorded tool versions and full commands are in [comparison.json](../bench/comparison.json) and the [formal records](verification.md). The current evidence uses CBMC 6.10.0 with Z3 4.8.12; other versions require rerunning the checks.

If `cbmc` selects an older installation, set `CBMC` to the version 6 executable. The runner rejects version 5. CBMC uses a 32 bit model; hosts without 32 bit preprocessing headers need the small header extraction described in [verification.md](verification.md#reproduction). The proof runner limits each job to 45 seconds and fails on timeouts and unwinding failures.

## One comparison command

```sh
make comparison
```

The pipeline force rebuilds the compact host suites with GCC, Clang, ASan and UBSan; regenerates and checks both coefficient sets and exact certificates; runs the focused CBMC groups; counts actual modular calls; rebuilds the six matched ARM correctness/benchmark images; and runs the three compact QEMU suites. It runs no large random campaign or generic compiler test suite. A failed stage stops publication of new comparison files. Logs go to ignored `build/comparison` and `build/verify`.

Outputs:

- [bench/comparison.json](../bench/comparison.json): schema version, source digests, tool versions, commands, log digests, operation/storage counts, ARM ELF digests and sizes, exact certificates, formal scope/status, QEMU status and explicit pending physical fields.
- [docs/comparison.md](comparison.md): generated comparison and interpretation.
- [bench/comparison.tex](../bench/comparison.tex): the same rows as plain LaTeX `tabular` environments, ready to include or wrap in thesis table environments.

Operation and size numbers must be changed by rebuilding, not editing a table. Runtimes are real wall times for reproduction, not Cortex M4 cycles. Host shared library size is omitted because all three checker bodies are linked into those libraries; matched ARM benchmark images give the relevant size comparison.

### Tool overrides

The pipeline forwards `ARM_CC`, `ARM_OBJCOPY`, `ARM_SIZE`, `ARM_INC` and `ARM_LIB` to Make. QEMU uses `QEMU` and optional `QEMU_LIBDIR`. CBMC uses `CBMC` and optional `CBMC_INCLUDES`. For the extracted toolchain present on this WSL host:

```sh
export ARM_CC="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-gcc"
export ARM_OBJCOPY="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-objcopy"
export ARM_SIZE="$PWD/build/toolchain/root/usr/bin/arm-none-eabi-size"
export ARM_INC="-isystem $PWD/build/toolchain/root/usr/include/newlib"
export ARM_LIB="-L$PWD/build/toolchain/root/usr/lib/arm-none-eabi/newlib/thumb/v7e-m/nofp"
export QEMU="$PWD/build/toolchain/root/usr/bin/qemu-system-arm"
export QEMU_LIBDIR="$PWD/build/toolchain/root/usr/lib/x86_64-linux-gnu"
export CBMC=/home/ishan/.local/toolchains/cbmc-6.10.0/usr/bin/cbmc
make comparison
```

The extracted binaries and headers are local dependencies, not repository files. On a machine with installed ARM tools, Newlib, QEMU and CBMC 6, use their ordinary `PATH` names and omit these exports. Make accepts these exported ARM overrides or explicit `NAME=value` arguments; the pipeline forwards the selected values to its builds.

## Individual commands

### Host build and ML DSA smoke validation

```sh
make build/libmldsa.so build/libmldsa_prior.so build/libmldsa_our.so
make -B baseline prior our CC=gcc
make -B baseline prior our CC=clang
make -B baseline prior our CC=gcc OPT='-O1 -g' SAN='-fsanitize=address'
make -B baseline prior our CC=gcc OPT='-O1 -g' SAN='-fsanitize=undefined -fno-sanitize-recover=all'
```

The compact entry point checks a SHAKE known answer, selected forward/inverse NTT vectors, deterministic key generation/signing, valid verification and modified message/signature rejection. Protected variants also run their selected C wire injections and failure propagation checks. These are functional tests, not formal proofs or physical injection experiments.

### Generation and exact certificates

```sh
python3 tools/gen_prior_checker.py
python3 tools/gen_prior_checker.py --check
python3 tools/gen_our_checker.py
python3 tools/gen_our_checker.py --check
```

Each generator automatically derives its coefficients, verifies row and production network identities and enumerates every distinct modeled wire pair. The `--check` command regenerates everything and requires byte identity with both the checked-in C constants and JSON certificate. It therefore performs both a generation check and an exact certificate, with no need to edit constants. The full pipeline uses these nonmutating checks. To check repeated deterministic generation, run `--check` twice; each run must match the same checked-in bytes.

### Focused CBMC verification

```sh
python3 verify/run.py --group arithmetic
python3 verify/run.py --group checkers
```

Set `CBMC` first if necessary. Result records include every job's command, unwind bound, assumptions' source harness, solver version and wall time. The comparison validates source, proof view and log digests before reporting proof success. Read [verification.md](verification.md) for preconditions, contracts and compositional scope; these jobs do not formally verify all ML DSA or SHAKE.

### ARM cross compilation and QEMU compact tests

```sh
make arm-mps2 arm-mps2-prior arm-mps2-our
make arm-mps2-bench arm-mps2-prior-bench arm-mps2-our-bench
python3 tools/run_mps2.py
python3 tools/run_mps2.py --prior
python3 tools/run_mps2.py --our
```

The correctness and benchmark images have separate entry points. The matched benchmark images contain no test injection hooks and are used for the size comparison. QEMU correctness records describe `mps2-an386`, not a Nucleo board. Emulator time or emulated DWT output must not populate physical cycle fields.

### Regenerate tables without rerunning experiments

```sh
python3 tools/render_comparison.py bench/comparison.json
```

This converts already collected raw results into both output formats and performs no measurements. The older `tools/measure_checkers.py` command is a cost-only collector for existing builds; `make comparison` is the complete authoritative pipeline.

## Physical board stage

Exact Nucleo model, MCU, clock/startup/linker layout, ST-Link access and serial transport must be identified before adding and flashing the board target. A connected physical board is required to fill cycle, flash, static RAM and stack fields. Mathematical pair certificates and physical fault injection remain distinct forms of evidence.

On WSL, a Windows-connected ST-Link must be made accessible to Linux. Microsoft's [USB connection guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb) documents discovery with `usbipd list`, administrator sharing with `usbipd bind --busid BUSID` and attachment with `usbipd attach --wsl --busid BUSID`. Use the board's actual bus ID. Check `lsusb` and its serial device after attachment. The pre hardware pipeline works without this connection.
