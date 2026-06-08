ENTRY(Reset_Handler)

MEMORY {
    CODE (rx) : ORIGIN = 0x00000000, LENGTH = 4M
    RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 4M
}

__stack_top = ORIGIN(RAM) + LENGTH(RAM);
__stack_limit = __stack_top - 256K;

SECTIONS {
    .vectors : { KEEP(*(.vectors)) } > CODE
    .text : {
        *(.text*)
        *(.rodata*)
        *(.ARM.exidx*)
    } > CODE
    __data_load = LOADADDR(.data);
    .data : {
        . = ALIGN(4);
        __data_start = .;
        *(.data*)
        . = ALIGN(4);
        __data_end = .;
    } > RAM AT> CODE
    .bss (NOLOAD) : {
        . = ALIGN(4);
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM
    ASSERT(__bss_end < __stack_limit, "RAM data overlaps stack reserve")
}
