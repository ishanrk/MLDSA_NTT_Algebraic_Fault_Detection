# Thesis tables and regression

The [thesis dataset](../bench/thesis.json) is a frozen comprehensive regression record. It includes official vectors, arithmetic/NTT/negative tests, both exact certificates, formal jobs, compiler/sanitizer results and ARM/QEMU correctness. Physical correctness, DWT cycles and total stack observations remain unmeasured. The newer instruction-count comparison is recorded separately in [qemu_benchmark.json](../bench/qemu_benchmark.json).

## Run the comprehensive regression

Configure the tools in [reproduction.md](reproduction.md), including CBMC 6, Z3 and OpenOCD, then run:

```sh
make thesis
```

Each GCC, Clang, ASan and UBSan configuration runs the full C arithmetic/NTT, rounding, encoding and negative suites; three checker correctness suites; shared Python models/SHAKE; and all supported official ML DSA 44 keygen, pure/prehash signing and verification vectors for all three variants. The original 10000-pair C polynomial test runs once per configuration. The existing 200-case pqcrypto differential suite runs once per GCC variant.

ASan instruments the standalone C tests and the libraries loaded by Python. Python processes preload the sanitizer runtime and disable leak reporting for interpreter allocations; standalone C processes retain leak detection. UBSan stops on its first finding. Python assertions remain enabled.

The run also checks generated constants, regenerates both exact certificates, executes focused CBMC jobs, rebuilds matched ARM images, runs QEMU correctness suites and validates the physical benchmark tooling with explicit synthetic controls. Those controls supply no physical observations. Failed stages stop publication; logs and partial progress are in `build/thesis`.

Records pin the input data, tool versions, commands and tested source digests. Historical snapshots retain filenames from their original commits. A reporting-only correction to the original dataset has a separately recorded focused validation; it changed no production or benchmark C.

## Use the tables

```sh
python3 tools/render_thesis.py bench/thesis.json
```

This generates [Markdown results](thesis_results.md) and the fragments under [bench/thesis](../bench/thesis). Include a fragment with `\input{bench/thesis/performance_our.tex}` when compiling from the repository root; adjust the path in a separate thesis project. `tables.tex` lists every fragment. They use ordinary LaTeX `tabular` environments; add captions/labels and fit wide tables to the thesis layout. Regenerate numerical tables from raw records rather than maintaining copied values.

Proof/regression seconds are host reproduction times, not Cortex M4 performance. QEMU instruction graphs have a separate raw dataset, script and explicit measurement unit.

## Import physical results

First identify the actual board, build a matching profile, and acquire a complete run using [hardware/README.md](../hardware/README.md). Then validate and incorporate its captured observations:

```sh
python3 tools/final_regression.py --physical-manifest /absolute/path/to/run/run.json
```

The report checks frozen sources/ELFs, target identity, exact correctness output, sample completeness, transcripts and timer-wrap bounds. This command validates existing captures; acquisition is the separate board action. Captures with differing frozen sources cannot be relabeled as current measurements.

## Writing and history

[Implementation methodology](implementation_methodology.md) describes the C implementation and experiments. [Threat model](threat_model.md) states the additive wire guarantee. The theorem proof, related-work argument, cost/construction interpretation, physical-board discussion and thesis conclusions still belong in the manuscript.

Obtain the complete repository history with `git log --format=fuller --stat`. Compiler and implementation records are research evidence; neither passing vectors nor measured physical cost establishes general physical fault resistance.
