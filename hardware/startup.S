.syntax unified
.cpu cortex-m4
.thumb
.section .vectors,"a",%progbits
.balign 512
.word __stack_top
.word Reset_Handler
.rept 110
.word Fault_Handler
.endr
.section .text.Fault_Handler,"ax",%progbits
.thumb_func
.global Fault_Handler
Fault_Handler:
    cpsid i
1:  b 1b
.section .note.GNU-stack,"",%progbits
