# Physical Cortex M4 acquisition

The physical stage requires an identified, accessible Nucleo board. The repository currently has an MPS2 emulator target and provisional DWT/stack interfaces, not a validated STM32 board startup/linker/serial target. Hardware measurements remain pending. The [discovery record](../bench/physical_status.json) records actual device visibility, without substituting emulator results.

```sh
python3 hardware/discover.py --output bench/physical_status.json
```

The tool reads Linux USB/serial discovery and, under WSL, Windows `usbipd.exe state`. It records only ST-Link candidates and serial paths; it does not flash, attach or reconfigure a device. A probe's USB name does not determine the exact Nucleo model or MCU. Confirm the board silkscreen/model and MCU before selecting a physical target. Windows attachment follows Microsoft's [WSL USB guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).

To complete the target, record the exact Nucleo model, STM32 part, core revision if readable, clock source/frequency, flash/RAM layout, FPU/ABI configuration, compiler/version/flags, linker and startup files, ST-Link tool/method and serial port/baud. Configure startup, clock and serial for that MCU. Reserve stack space using its real RAM capacity. The MPS2 linker reserves memory that does not describe an STM32 device.

The physical compact suite must run separately for baseline, prior and our variants before accepting benchmark observations. Reuse the existing selected vectors, deterministic scheme tests and known answers. Mathematical additive wire coverage and physical fault injection are separate evidence; this stage does not establish physical injection success.

The existing benchmark entry point keeps output outside measured regions, records DWT overhead and varies explicit signing randomness across samples. Its stack watermark estimates additional depth below the measurement call site. Hardware must confirm DWT availability, intervals shorter than one counter wrap, interrupt policy and sufficient reserved stack. A memory watermark reaching the stack limit invalidates a measurement.

## Raw run files and reporting

Copy [run.template.json](run.template.json) to a run directory and fill it only from the identified board, actual build and captured observations. Its null fields are missing facts, not defaults. The sample counts and input schedule must describe the exact benchmark firmware used for all three variants. Preserve both ELF files, the complete compact output and all JSON lines for each variant. Keep timer overhead and stack records together with every cycle sample; do not discard outliers or choose only successful fast signatures.

```sh
python3 hardware/report.py physical-run/run.json --output physical-run/report
```

Set `ARM_SIZE` if needed. The tool requires a completed physical manifest, matching ARM ELF/source digests, all three compact outputs, every contiguous sample, timer overhead and stack observations. It rejects pending manifests, missing/duplicate samples, zero operation cycles, mismatched correctness output and exhausted stack reservations. No physical dataset is currently present, so the checked-in template must be refused.

The output includes machine readable sample count/minimum/median/maximum/nearest-rank P95, median overhead versus baseline, timer overhead, linked flash/static RAM, the recorded stack semantics, operation counts and modeled fault coverage. Markdown is generated from these values. Measurements that give only additional stack depth are labeled accordingly; they do not become total stack high water estimates. A physical target must extend or calibrate that method before reporting total high water. Inverse NTT is unprotected in all three current variants.

Run `python3 hardware/test_report.py` for the statistics/parser controls. They use explicitly synthetic temporary data, not benchmark evidence, and verify complete sample accounting and rejection of malformed runs. No synthesized cycle or memory observations are published as physical results.
