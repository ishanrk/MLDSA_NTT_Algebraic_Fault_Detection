#ifndef MLDSA_PHYSICAL_TARGET_H
#define MLDSA_PHYSICAL_TARGET_H

#include <stdint.h>

void physical_init(void);
uint32_t physical_cycles(void);
int physical_dwt_init(void);
uint32_t physical_stack_fill(void);
uint32_t physical_stack_used(uint32_t start);
void physical_u32(uint32_t value);

#endif
