# Cortex M4 reference builds

Generated from [raw results](../bench/offline_cortexm4.json). Physical correctness, cycles and stack measurements are pending.

## `NUCLEO-F411RE`

### Cycle comparison

| Variant | NTT median | NTT overhead % | Sign median | Sign overhead % | Verify median | Verify overhead % | Keygen median | Keygen overhead % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | pending | pending | pending | pending | pending | pending | pending | pending |
| Abdelmonem et al. | pending | pending | pending | pending | pending | pending | pending | pending |
| Current method | pending | pending | pending | pending | pending | pending | pending | pending |

### Memory and evidence

| Variant | Linked flash | Static RAM | Keygen stack | Sign stack | Verify stack | Extra mul | Extra add | Modeled deviations | Board correctness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 12812 | 17096 | pending | pending | pending | 0 | 0 | 0 | pending |
| Abdelmonem et al. | 15644 | 17096 | pending | pending | pending | 640 | 1024 | 2 | pending |
| Current method | 16136 | 17096 | pending | pending | pending | 768 | 1024 | 2 | pending |

GCC reports a largest individual frame of `82376` bytes and the linker reserves `98304` stack bytes. These are static observations; complete stack high water requires a physical capture.

## `NUCLEO-F446RE`

### Cycle comparison

| Variant | NTT median | NTT overhead % | Sign median | Sign overhead % | Verify median | Verify overhead % | Keygen median | Keygen overhead % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | pending | pending | pending | pending | pending | pending | pending | pending |
| Abdelmonem et al. | pending | pending | pending | pending | pending | pending | pending | pending |
| Current method | pending | pending | pending | pending | pending | pending | pending | pending |

### Memory and evidence

| Variant | Linked flash | Static RAM | Keygen stack | Sign stack | Verify stack | Extra mul | Extra add | Modeled deviations | Board correctness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 12812 | 17096 | pending | pending | pending | 0 | 0 | 0 | pending |
| Abdelmonem et al. | 15644 | 17096 | pending | pending | pending | 640 | 1024 | 2 | pending |
| Current method | 16136 | 17096 | pending | pending | pending | 768 | 1024 | 2 | pending |

GCC reports a largest individual frame of `82376` bytes and the linker reserves `98304` stack bytes. These are static observations; complete stack high water requires a physical capture.

The recorded offline controls check the implementation and acquisition software with synthetic timer and stack responses. They supply no physical performance observations.
