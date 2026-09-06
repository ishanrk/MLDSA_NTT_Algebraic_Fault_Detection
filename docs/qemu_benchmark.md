# QEMU benchmark method

Run `make qemu-benchmark` to compile and execute all three variants at `-O2` and `-O3 -flto`. It produces [raw JSON](../bench/qemu_benchmark.json), [CSV](../bench/qemu_benchmark.csv), [full statistics](qemu_results.md), and the README graphs. `python3 tools/plot_benchmarks.py` redraws the figures from the saved observations without running the benchmarks.

## Measurement

The target is QEMU's [`mps2-an386` Cortex M4 model](https://www.qemu.org/docs/master/system/arm/mps2.html). The [TCG plugin API](https://www.qemu.org/docs/master/devel/tcg-plugins.html) instruments execution of each guest instruction. A single-vCPU inline 64-bit counter runs throughout execution; callbacks at the two marker-function entry addresses snapshot it. The difference counts instructions between those entries. ELF symbols supply the addresses for each build.

The guest first runs an empty marker pair and a fixed assembly control. The control consists of one setup instruction and a 100-iteration loop with three instructions per iteration; it must add exactly 301 instructions. A failed control, duplicate interval, missing sample or unfinished region invalidates the run. Each image also measures 101 empty marker pairs; their minimum is subtracted from every operation count. Raw counts and every calibration sample remain in the JSON.

This is an instruction-count measurement, not a hardware clock measurement. QEMU's instruction accounting does not model Cortex M4 instruction latency, flash wait states, memory contention or a physical pipeline. The model's DWT counter is unavailable. Neither emulator wall time nor instruction counts are converted into physical cycles. See [QEMU's instruction-counting documentation](https://www.qemu.org/docs/master/devel/tcg-icount.html).

## Inputs and correctness

Every build uses the same 101-sample schedules:

- Forward/inverse NTT and pointwise multiplication use the fixed polynomials recorded in the guest source. Forward output is compared against the baseline, inverse output against the input, and pointwise output against an untimed reference.
- Key generation uses bytes `0..31` with the first byte replaced by the sample index.
- Signing uses a fixed key, message and context. Its 32-byte randomness is zero except for the first byte, which is the sample index. Every signature is verified outside the measured region.
- Verification uses the final signing sample.

Hashing every generated public key and signature gives a SHAKE256 transcript. All six images must produce the same transcript. Each optimization/variant combination also executes the existing correctness and modeled-fault suite in a separate image before its benchmark is accepted. The scheme, transform and checker sources are shared with the production builds; benchmark images contain no fault-injection hooks.

## Statistics and comparisons

Reports retain all 101 observations and give minimum, median, maximum and nearest-rank P95. Signing variation reflects its ordinary rejection loop. Relative overhead compares variant medians within the same compiler configuration. The graph's whiskers span observed minimum to P95; they are not confidence intervals.

The prior variant is this repository's independent implementation of Abdelmonem et al.'s construction. It is measured with the same transform representation, compiler flags, inputs and instrumentation as our checker. Its numbers are not the paper's published measurements. Optimization compares `-O2` with `-O3 -flto` across both defenses; it does not compare one optimized defense with an unoptimized competitor.

The construction-bound graph is calculated directly from the two sufficient-bound formulas. Only the `n=256` instance has the concrete ML DSA coefficient certificate here; other plotted lengths illustrate those formulas, not additional implemented parameter sets.

## Provenance and dependencies

The raw record includes source/ELF/plugin digests, compiler flags, QEMU/compiler versions, commands, log digests, control results, input transcripts and all counts. Logs and builds are under ignored `build/qemu-benchmark`. Wall times recorded for commands describe reproduction time only.

The plugin builds against the official QEMU 6.2 API header, fetched once from a pinned URL and checked by SHA256. It is stored as an external dependency in `build/qemu-benchmark/deps`. QEMU must support the plugin API; an unsupported installation fails rather than falling back to a timing estimate. The plotting dependency is Matplotlib. ARM tool and library overrides are listed in the README.
