# Final thesis artifact reproduction

The current artifact contains a complete available host regression and generated thesis tables. **Physical smoke tests and benchmark reproduction remain pending.** Run records and tables preserve this status; the final physical milestone has not been completed.

## Dependencies and one comprehensive command

Use the compiler, ARM/Newlib, QEMU, CBMC/Z3 and header configuration in [reproduction.md](reproduction.md). The final run also needs OpenOCD for an offline configuration parse and `pqcrypto==1.0.0` as a black-box differential oracle. The runner installs that version into ignored `build/oracle` if absent; it is never a production dependency. NIST inputs are fetched into ignored `build/nist` and verified against [the pinned blob manifest](../tools/nist_manifest.json). No board is contacted by the default command.

```sh
make thesis
```

On this WSL machine, use the ARM/QEMU/CBMC exports in [reproduction.md](reproduction.md#tool-overrides), then also export the extracted OpenOCD paths:

```sh
export OPENOCD="$PWD/build/hardware-tools/root/usr/bin/openocd"
export OPENOCD_SCRIPTS="$PWD/build/hardware-tools/root/usr/share/openocd/scripts"
export LD_LIBRARY_PATH="$PWD/build/hardware-tools/root/usr/lib/x86_64-linux-gnu:$PWD/build/hardware-tools/root/lib/x86_64-linux-gnu"
make thesis
```

An ordinary installation uses `openocd` on `PATH` and its installed scripts. The offline OpenOCD command parses configuration and exits without `init`, probing or flashing. The final run rebuilds targets in ignored `build`; it does not call `make clean`, which would also remove locally extracted toolchains and cached vectors.

## What the run covers

Each of GCC, Clang, ASan and UBSan runs the existing full C arithmetic/NTT, rounding, encoding and negative suites; all three compact checker suites; baseline Python arithmetic/sampling/SHAKE tests; and every supported official ML DSA 44 keygen, pure/prehash signing and verification case for all three variants. The negative C program also runs with each protected scheme selector. The existing C polynomial test includes its original seeded 10000-pair campaign, once in each mode. The existing 200-case pqcrypto differential test runs once per variant under GCC; no new random campaign is added.

AddressSanitizer instruments both the C executables and the libraries loaded by Python. Python child processes preload GCC's ASan runtime and disable leak reporting for Python interpreter allocations; the standalone C test processes keep leak detection enabled. Bounds and other ASan findings still fail the Python runs. UBSan is configured to stop on its first error. Python assertions remain enabled.

The same invocation checks generated twiddle/Keccak constants, regenerates both exact checker certificates, runs both focused CBMC groups with unwinding assertions, counts modular calls, rebuilds six matched MPS2 images and runs the three compact QEMU suites. It rebuilds both STM32 reference profiles and exercises the actual benchmark code with explicit synthetic timer/stack controls, validates report rejection paths, and tests ARM stack helpers in QEMU. Synthetic observations are never copied into physical tables.

Any failed stage or timeout stops final result publication. Inspect `build/thesis/progress.json` and its named logs; do not interpret an older result file as a new successful run. A run records its base commit, dirty-tree status and the digests of every tested source. Artifact tooling may be uncommitted during collection; the source digests identify those exact bytes. Documentation-only follow-up commits do not change the tested implementation.

The current record also includes a separately identified reporting-only correction and its focused validation: the table renderer's pointwise operation name was aligned with the acquisition protocol. The comprehensive regression source hashes are preserved; replacement tooling hashes and the focused test log are recorded under `post_run_tooling_validation`. No production or benchmark source changed, and the expensive regression was not repeated.

## Raw results and LaTeX inclusion

- [bench/thesis.json](../bench/thesis.json): one frozen record of source/tool/input provenance, commands, logs' digests, actual case counts, costs, certificates, proof results and pending/validated physical evidence.
- [docs/thesis_results.md](thesis_results.md): all generated result tables and interpretation limits.
- [bench/thesis/tables.tex](../bench/thesis/tables.tex): includes every generated LaTeX fragment. Separate fragments cover each variant's performance, overhead, memory, arithmetic/storage costs, exact certificates, formal groups/properties and regression counts.
- `build/thesis/*.log`, `build/verify/*.log` and `build/hardware-offline`: raw local logs and compiled/capture artifacts. Their identifying digests are in the frozen records; these ignored files are not silently presented as tracked repository data.

Regenerate tables without repeating experiments:

```sh
python3 tools/render_thesis.py bench/thesis.json
```

Use `\input{bench/thesis/performance_our.tex}` from a document compiled at the repository root, or adjust the path for the thesis project. Each fragment is an ordinary `tabular`; wrap it in a table environment, give it a caption/label and adapt wide tables to the institutional page layout. `tables.tex` demonstrates every inclusion. Do not copy numbers into separately maintained tables. Runtime values in the proof/regression tables are host wall times, not Cortex M4 performance numbers.

## Complete the physical milestone

Use [hardware/README.md](../hardware/README.md) to identify the actual board, build its supported profile, freeze a new run and acquire all compact and benchmark captures. On WSL, expose its ST-Link and serial port first. The final acquisition must use the same compiled source and input plan identified by the run manifest. A profile name or successful link is not board identification or a physical correctness result.

After a real acquisition:

```sh
python3 tools/final_regression.py --physical-manifest /absolute/path/to/run/run.json
```

This validates the completed capture manifest and raw logs through the physical report's source, ELF, identity, compact-output, sample-count, transcript and counter-wrap checks. It incorporates actual observations into the same LaTeX tables. It does not independently flash a board or repeat physical measurements; the acquisition is the separate required hardware action. Old captures with differing frozen sources must not be relabeled as current measurements.

## History, scope and manuscript work

The run stores `build/thesis/git-log-at-run.txt`, which ends at the base commit before the new experiment commits. Obtain the full final history after committing the artifact:

```sh
git log --format=fuller --stat > build/thesis/git-log-final.txt
```

Use [implementation_methodology.md](implementation_methodology.md) for concise methods text and [threat_model.md](threat_model.md) for coverage language. The [formal verification document](verification.md) lists every command, precondition, contract and scope boundary. The exact certificates do not establish physical fault resistance, and physical timing would establish cost rather than such resistance.

The author still needs to integrate the general theorem proof, related-work discussion, construction/cost tradeoff, physical-board observations after capture, conclusions, citations in the thesis bibliography, and institutional formatting. The repository supplies reproducible numerical material and implementation methodology; it does not manufacture missing physical results or replace those manuscript arguments.
