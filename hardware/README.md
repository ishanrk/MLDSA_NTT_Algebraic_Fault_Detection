# Cortex M4 physical-stage software

The STM32F4 firmware has two reference targets, `NUCLEO-F411RE` and `NUCLEO-F446RE`. Their six compact/benchmark images can be cross compiled without a board. Select the profile matching the actual board before flashing. Physical identification, flashing, UART correctness, DWT observations and measured stack high water remain pending.

[Generated offline tables](../docs/cortexm4_offline.md) and [raw results](../bench/offline_cortexm4.json) report compiled image sizes and software checks. Physical cycle and stack fields stay `pending`. The portable crypto, checker mathematics and generated coefficients are unchanged.

## Reference configuration

Both profiles use 512 KiB flash at `0x08000000` and 128 KiB main SRAM at `0x20000000`. The F446 backup SRAM is unused. The linker reserves 96 KiB for the main stack and asserts that static data does not overlap it. The [F411 datasheet](https://www.st.com/resource/en/datasheet/stm32f411re.pdf) and [F446 datasheet](https://www.st.com/resource/en/datasheet/stm32f446re.pdf) specify these devices; [UM1724](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf) describes the Nucleo board and ST-Link UART connections.

The minimal startup sets VTOR, copies data, clears BSS, disables interrupts/SysTick and initializes polling USART2 on PA2/PA3 at 115200 8N1. The clock is configured to nominal 16 MHz HSI with PLL/HSE off and no bus prescaling. Flash caches/prefetch are off, latency is zero, and FPU access is disabled with the existing soft ABI. The physical run records the actual clock/control registers; nominal HSI frequency is not an independent frequency measurement. All variants use the same configuration and inputs.

The [F401RE](https://www.st.com/resource/en/datasheet/stm32f401re.pdf) is **not supported by this unchanged benchmark layout**. GCC's signing frame plus the benchmark static data already exceeds its 96 KiB main SRAM before adding callees. This is a concrete memory constraint, not a physical observation. Larger profiles avoid that known overlap; static frame information is not a bound on complete call depth. The board watermark remains necessary.

## Offline reproduction

Requirements: Python 3, GCC, Clang, ARM GCC/binutils/Newlib, QEMU and OpenOCD. Use the ARM/QEMU overrides in the [reproduction guide](../docs/reproduction.md#tool-overrides) for the local extracted toolchain. OpenOCD configuration is parsed and shut down without `init`, probing or flashing.

```sh
python3 hardware/offline.py
```

This command builds both profiles; runs parser, serial handshake and report integrity controls; executes the actual benchmark code with clearly labeled synthetic timers/stack controls under GCC, Clang, ASan and UBSan; compares every variant's complete key/signature transcript; and checks the ARM watermark/unavailable-DWT helpers under QEMU. Synthetic numbers remain in ignored `build/hardware-offline` and are never published as physical observations. It generates JSON, Markdown and LaTeX offline tables without rerunning generic test campaigns.

OpenOCD 0.11.0 was extracted locally into ignored `build/hardware-tools/root`. For that installation:

```sh
export OPENOCD="$PWD/build/hardware-tools/root/usr/bin/openocd"
export OPENOCD_SCRIPTS="$PWD/build/hardware-tools/root/usr/share/openocd/scripts"
export LD_LIBRARY_PATH="$PWD/build/hardware-tools/root/usr/lib/x86_64-linux-gnu:$PWD/build/hardware-tools/root/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python3 hardware/offline.py
```

On a machine with ordinary installed tools, those exports are unnecessary. The local package extraction is a dependency, not repository source. Compiler flags and source/ELF hashes are stored with each build. CBMC continues to cover the documented portable crypto components; STM32 startup, registers and ARM helper instructions are outside that formal result.

## Build and freeze one experiment

Select the model explicitly after checking the board label; there is no automatic/default selection:

```sh
python3 hardware/build.py --board NUCLEO-F411RE
python3 hardware/prepare.py --board NUCLEO-F411RE --output build/physical-runs/run-01
python3 hardware/report.py build/physical-runs/run-01/run.json \
  --pending --output build/physical-runs/run-01/report
```

Substitute `NUCLEO-F446RE` if that is the confirmed board. Other MCUs need a matching profile/adapter; do not rename a profile to bypass identity checks. `prepare.py` freezes the six ELF files, exact selectors, linker/startup files, compiler settings, expected compact output, source hashes and comparison evidence. It refuses an existing destination. The illustrative null template is not a substitute for this generated manifest.

The pending report gives real linked flash (`text+data`) and static RAM (`data+bss`) sizes, excluding linker padding and stack. These are compile results for the selected reference layout, not evidence of a successful physical run. The source hashes identify the compiled worktree; a dirty-worktree flag distinguishes it from the recorded base commit.

## Command ready for an accessible board

First confirm the exact model and ordinary board configuration, including ST-Link connection and USART solder bridges described in UM1724. Discover device visibility with:

```sh
python3 hardware/discover.py --output bench/physical_status.json
```

Under WSL, follow Microsoft's [USB attachment guide](https://learn.microsoft.com/en-us/windows/wsl/connect-usb) to expose the actual ST-Link device and its serial port. Then run:

```sh
python3 hardware/acquire.py build/physical-runs/run-01/run.json \
  --port /dev/serial/by-id/ACTUAL_DEVICE --probe-serial ACTUAL_STLINK_SERIAL
```

This is the hardware-dependent command and has not been run on a physical board. It checks the MCU ID, CPUID and flash size before programming; uses OpenOCD [ELF programming and verification](https://openocd.org/doc/html/Flash-Programming.html); and opens the UART before reset. Firmware emits a readiness record and waits for `R`, preventing lost early output. Target unique-ID words must match between SWD and serial. Actual OpenOCD version/method and serial transport are recorded. The Cortex M4 revision is decoded from observed CPUID.

All three compact suites must complete with the existing SHAKE known answer, selected NTT vectors, deterministic keygen/sign, valid verification and modified message/signature rejection before benchmarks are accepted. Protected images also retain their small selected software injection checks; those are not physical fault injection.

Failures preserve raw/probe/flash logs. A fresh prepared directory is required for another attempt; earlier observations are not overwritten. A partial run never becomes a measured result.

## Measurement and report rules

The physical benchmark records 101 observations each for forward NTT, inverse NTT, pointwise multiplication, keygen, signing and verification. Signing uses a fixed key and message, varying explicit randomness across the same sample schedule in every variant; it retains ordinary rejection behavior. Each signature is verified outside its timed interval. Inverse NTT is unprotected in every current variant.

It preserves all 101 timer read-pair samples, uses their minimum as correction, and retains both raw and corrected operation counts. Output follows the timed loops. Stack is filled/scanned outside timed intervals, using frameless assembly helpers. Each keygen/sign/verify invocation has a total high-water observation including the caller frame; reports use the maximum over all planned inputs. This is not an exhaustive worst case bound.

Acquisition bounds the entire batch, including serial output, below one DWT wrap with a 10% HSI frequency margin. A passing whole-batch bound also bounds every individual interval. This relies on the configured factory HSI operating within the documented device conditions. A batch that exceeds the bound is refused, with logs retained; it cannot be rescued by merely setting a manifest flag.

```sh
python3 hardware/report.py build/physical-runs/run-01/run.json \
  --output build/physical-runs/run-01/report
```

The measured report requires matching frozen sources, compiler settings, exact variant ELFs, complete compact output, runtime register checks, every sample and stack record, correct timer subtraction, an established wrap bound and identical full key/signature transcripts across variants. It rejects synthetic device records, variant swaps, missing/duplicate observations and exhausted stack reservations. JSON, Markdown and LaTeX give sample count/minimum/median/maximum/nearest-rank P95, baseline-relative median overhead, linked memory, stack high water, modular operation counts and modeled coverage.

Mathematical coverage remains the certified additive wire model with trusted checker arithmetic/control flow. Physical correctness and timing measurements do not establish physical fault resistance. No physical injection success is claimed.
