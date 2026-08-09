# Physical Cortex M4 acquisition

The physical stage requires an identified, accessible Nucleo board. The repository currently has an MPS2 emulator target and provisional DWT/stack interfaces, not a validated STM32 board startup/linker/serial target. Hardware measurements remain pending. The [discovery record](../bench/physical_status.json) records actual device visibility, without substituting emulator results.

```sh
python3 hardware/discover.py --output bench/physical_status.json
```

The tool reads Linux USB/serial discovery and, under WSL, Windows `usbipd.exe state`. It records only ST-Link candidates and serial paths; it does not flash, attach or reconfigure a device. A probe's USB name does not determine the exact Nucleo model or MCU. Confirm the board silkscreen/model and MCU before selecting a physical target. Windows attachment follows Microsoft's [WSL USB guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).

To complete the target, record the exact Nucleo model, STM32 part, core revision if readable, clock source/frequency, flash/RAM layout, FPU/ABI configuration, compiler/version/flags, linker and startup files, ST-Link tool/method and serial port/baud. Configure startup, clock and serial for that MCU. Reserve stack space using its real RAM capacity. The MPS2 linker reserves memory that does not describe an STM32 device.

The physical compact suite must run separately for baseline, prior and our variants before accepting benchmark observations. Reuse the existing selected vectors, deterministic scheme tests and known answers. Mathematical additive wire coverage and physical fault injection are separate evidence; this stage does not establish physical injection success.

The existing benchmark entry point keeps output outside measured regions, records DWT overhead and varies explicit signing randomness across samples. Its stack watermark estimates additional depth below the measurement call site. Hardware must confirm DWT availability, intervals shorter than one counter wrap, interrupt policy and sufficient reserved stack. A memory watermark reaching the stack limit invalidates a measurement.
