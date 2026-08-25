ENTRY(Reset_Handler)
MEMORY {
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = @FLASH_BYTES@
    RAM (rwx) : ORIGIN = 0x20000000, LENGTH = @RAM_BYTES@
}
__stack_top = ORIGIN(RAM) + LENGTH(RAM);
__stack_limit = __stack_top - @STACK_BYTES@;
SECTIONS {
    .vectors : { . = ALIGN(512); KEEP(*(.vectors)) } > FLASH
    .text : { *(.text*) *(.rodata*) } > FLASH
    .ARM.exidx : { *(.ARM.exidx*) } > FLASH
    .data : {
        . = ALIGN(8);
        __data_start = .;
        *(.data*)
        . = ALIGN(8);
        __data_end = .;
    } > RAM AT> FLASH
    __data_load = LOADADDR(.data);
    .bss (NOLOAD) : {
        . = ALIGN(8);
        __bss_start = .;
        *(.bss*) *(COMMON)
        . = ALIGN(8);
        __bss_end = .;
    } > RAM
    ASSERT(__bss_end <= __stack_limit, "Static RAM overlaps stack reserve")
}
