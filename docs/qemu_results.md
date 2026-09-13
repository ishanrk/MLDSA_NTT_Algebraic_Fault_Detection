# QEMU instruction measurements

Generated from [raw observations](../bench/qemu_benchmark.json). Unit: **guest instructions**, after empty marker subtraction. Physical cycles are unmeasured. The plots show medians; this table retains the complete range and P95.

Compiler: `arm-none-eabi-gcc (15:10.3-2021.07-4) 10.3.1 20210621 (release)`. Emulator: `QEMU emulator version 6.2.0 (Debian 1:6.2+dfsg-2ubuntu6.31)`. Target: `mps2-an386`.

The 100 iteration assembly control adds exactly 301 instructions in every image. Complete key/signature transcripts match all methods and both optimization settings.

## o2

Flags: `-mcpu=cortex-m4 -mthumb -mfloat-abi=soft -std=c11 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow -O2`.

| Variant | Operation | Samples | Min | Median | Max | P95 | Overhead vs baseline (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | `ntt_forward` | 101 | 96999 | 96999 | 96999 | 96999 | 0.0 |
| Baseline | `ntt_inverse` | 101 | 114452 | 114452 | 114452 | 114452 | 0.0 |
| Baseline | `pointwise` | 101 | 16657 | 16657 | 16657 | 16657 | 0.0 |
| Baseline | `keygen` | 101 | 7910186 | 8083359 | 8313558 | 8198727 | 0.0 |
| Baseline | `sign` | 101 | 11820567 | 25013074 | 82185869 | 64593447 | 0.0 |
| Baseline | `verify` | 101 | 8877948 | 8877948 | 8877948 | 8877948 | 0.0 |
| Prior method | `ntt_forward` | 101 | 149082 | 149082 | 149082 | 149082 | 53.6944 |
| Prior method | `ntt_inverse` | 101 | 114452 | 114452 | 114452 | 114452 | 0.0 |
| Prior method | `pointwise` | 101 | 16657 | 16657 | 16657 | 16657 | 0.0 |
| Prior method | `keygen` | 101 | 8119650 | 8292681 | 8522937 | 8408214 | 2.5895 |
| Prior method | `sign` | 101 | 12711327 | 26689522 | 87267041 | 68626803 | 6.7023 |
| Prior method | `verify` | 101 | 9349908 | 9349908 | 9349908 | 9349908 | 5.3161 |
| Current method | `ntt_forward` | 101 | 155996 | 155996 | 155996 | 155996 | 60.8223 |
| Current method | `ntt_inverse` | 101 | 114452 | 114452 | 114452 | 114452 | 0.0 |
| Current method | `pointwise` | 101 | 16657 | 16657 | 16657 | 16657 | 0.0 |
| Current method | `keygen` | 101 | 8147366 | 8320454 | 8550753 | 8436029 | 2.9331 |
| Current method | `sign` | 101 | 12829124 | 26910914 | 87938341 | 69159716 | 7.5874 |
| Current method | `verify` | 101 | 9412274 | 9412274 | 9412274 | 9412274 | 6.0186 |

## o3_lto

Flags: `-mcpu=cortex-m4 -mthumb -mfloat-abi=soft -std=c11 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow -O3 -flto`.

| Variant | Operation | Samples | Min | Median | Max | P95 | Overhead vs baseline (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | `ntt_forward` | 101 | 80139 | 80139 | 80139 | 80139 | 0.0 |
| Baseline | `ntt_inverse` | 101 | 98088 | 98088 | 98088 | 98088 | 0.0 |
| Baseline | `pointwise` | 101 | 15629 | 15629 | 15629 | 15629 | 0.0 |
| Baseline | `keygen` | 101 | 3262896 | 3310428 | 3373435 | 3342325 | 0.0 |
| Baseline | `sign` | 101 | 6379456 | 15057972 | 52667117 | 41093377 | 0.0 |
| Baseline | `verify` | 101 | 4227410 | 4227410 | 4227410 | 4227410 | 0.0 |
| Prior method | `ntt_forward` | 101 | 124927 | 124927 | 124927 | 124927 | 55.8879 |
| Prior method | `ntt_inverse` | 101 | 98088 | 98088 | 98088 | 98088 | 0.0 |
| Prior method | `pointwise` | 101 | 15629 | 15629 | 15629 | 15629 | 0.0 |
| Prior method | `keygen` | 101 | 3442149 | 3489654 | 3552601 | 3521611 | 5.414 |
| Prior method | `sign` | 101 | 7144541 | 16499515 | 57038997 | 44563373 | 9.5733 |
| Prior method | `verify` | 101 | 4634912 | 4634912 | 4634912 | 4634912 | 9.6395 |
| Current method | `ntt_forward` | 101 | 131576 | 131576 | 131576 | 131576 | 64.1847 |
| Current method | `ntt_inverse` | 101 | 98088 | 98088 | 98088 | 98088 | 0.0 |
| Current method | `pointwise` | 101 | 15629 | 15629 | 15629 | 15629 | 0.0 |
| Current method | `keygen` | 101 | 3468821 | 3516374 | 3579371 | 3548404 | 6.2211 |
| Current method | `sign` | 101 | 7258005 | 16712795 | 57685314 | 45076407 | 10.9897 |
| Current method | `verify` | 101 | 4694952 | 4694952 | 4694952 | 4694952 | 11.0598 |
