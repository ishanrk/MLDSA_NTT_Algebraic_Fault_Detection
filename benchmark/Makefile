CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
CFLAGS = -O2 -std=c11 -mcpu=cortex-m4 -mthumb -ffreestanding -fno-builtin \
         -fno-unwind-tables -ffunction-sections -fdata-sections -Wall -Wextra
CPPFLAGS = -I../include -I../src -I../research -DMLDSA_FAULTY_PRONE_MEMORY_OPTIMIZATION
LDFLAGS = -nostdlib -Wl,--gc-sections -Tstm32l476rg.ld -lgcc
SRC = ../src/poly.c ../src/ntt.c ../src/shake.c ../src/round.c \
      ../src/encode.c ../src/sample.c ../src/vector.c ../src/keygen.c \
      ../src/sign.c ../src/verify.c ../src/message.c

.PHONY: all clean
all: build/plain.bin build/guarded.bin

build/plain.elf: bench.c board.c board.h stm32l476rg.ld $(SRC)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) bench.c board.c $(SRC) $(LDFLAGS) -o $@

build/guarded.elf: bench.c board.c board.h stm32l476rg.ld $(SRC) ../research/block_guard.c
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DMLDSA_BLOCK_CHECKER bench.c board.c $(SRC) \
	    ../research/block_guard.c $(LDFLAGS) -o $@

build/%.bin: build/%.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf build
