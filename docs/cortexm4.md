# Cortex M4 builds

The C implementation has two platform paths: QEMU `mps2-an386` for correctness and instruction-count comparison, and STM32F4 Nucleo firmware for physical DWT/stack measurements. Both use Thumb and the soft float ABI. No cryptographic operation uses floating point.

## QEMU correctness

```sh
make arm-mps2 arm-mps2-prior arm-mps2-our
python3 tools/run_mps2.py
python3 tools/run_mps2.py --prior
python3 tools/run_mps2.py --our
```

The suites check SHAKE, selected forward/inverse NTT vectors, deterministic key generation/signing, valid verification, modified message/signature rejection and checker fault propagation. Protected images include the selected single and cancelling-pair software injections. The existing functional records are in `test/qemu-mps2-an386*.json`.

The [QEMU board model](https://www.qemu.org/docs/master/system/arm/mps2.html) provides separate 4 MiB code/data SRAM regions. `platform/cortexm4/mps2.ld` reserves 256 KiB for the stack. This is an emulator layout, not Nucleo flash/RAM. Semihosting supplies output and process termination.

## Instruction comparison

```sh
make qemu-benchmark
```

The new harness in `platform/cortexm4/qemu_bench.c` marks measured regions for a TCG plugin. The comparison runs baseline, prior and our code at matched `-O2` and `-O3 -flto` settings. Guest-instruction counts are calibrated, retained sample by sample and checked against a fixed assembly control. All complete key/signature transcripts must agree. [Method](qemu_benchmark.md), [results](qemu_results.md), [README graphs](../README.md#measurements-and-graphs).

The original `bench_main.c` DWT harness remains a separate build used for the historical matched-image size comparison. QEMU's DWT counter is unavailable on the recorded model; that firmware exits without timing observations. No emulator output is treated as a physical cycle measurement.

## STM32F4 measurements

[hardware/README.md](../hardware/README.md) documents startup, clock configuration, linker layout, UART handshake, identity checks and acquisition for NUCLEO-F411RE/F446RE. The firmware measures DWT cycles and total stack high water over all scheduled samples. Real board correctness, cycles and stack results remain pending. The current benchmark's signing frame and static RAM do not fit an F401RE's main SRAM.

Use the tool overrides in [reproduction.md](reproduction.md#tool-overrides) when ARM GCC, Newlib or QEMU are not installed on the normal path. [Constant time observations](ct.md) describe the portable ARM division, branches and accesses that still require side channel review.
