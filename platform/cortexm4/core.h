#ifndef MLDSA_CORTEXM4_CORE_H
#define MLDSA_CORTEXM4_CORE_H

#include <stdint.h>

int platform_dwt_init(void);
uint32_t platform_cycles(void);
uint32_t platform_stack_fill(void);
uint32_t platform_stack_used(uint32_t start);

#endif
