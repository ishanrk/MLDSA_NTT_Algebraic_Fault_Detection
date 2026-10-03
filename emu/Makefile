CC = arm-none-eabi-gcc
OBJDUMP = arm-none-eabi-objdump
SIZE = arm-none-eabi-size
CPPFLAGS = -I../include -I../src -I../research -DMLDSA_ARCHIE \
           -DMLDSA_FAULTY_PRONE_MEMORY_OPTIMIZATION
CFLAGS = -O2 -g -std=c11 -mcpu=cortex-m4 -mthumb -ffreestanding -fno-builtin \
         -ffunction-sections \
         -fdata-sections -Wall -Wextra -Wpedantic
LDFLAGS = -nostdlib -Wl,--gc-sections -Wl,-T,mps2-an386.ld -lgcc
SRC = ../src/poly.c ../src/ntt.c ../src/shake.c ../src/round.c \
      ../src/encode.c ../src/sample.c ../src/vector.c ../src/keygen.c \
      ../src/sign.c ../src/verify.c ../src/message.c

.PHONY: all clean
all: build/plain.elf build/guarded.elf

build/plain.elf: runner.c startup.c fips_case.h mps2-an386.ld $(SRC)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) runner.c startup.c $(SRC) $(LDFLAGS) -o $@
	$(SIZE) $@

build/guarded.elf: runner.c startup.c fips_case.h mps2-an386.ld $(SRC) ../research/block_guard.c
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DMLDSA_BLOCK_CHECKER runner.c startup.c $(SRC) \
	    ../research/block_guard.c $(LDFLAGS) -o $@
	$(SIZE) $@

clean:
	rm -rf build qemu-*.json fault-*.json *.hdf5
