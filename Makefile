CC = gcc
OPT = -O2
SAN =
SEED =
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow $(OPT) $(SAN) -fno-omit-frame-pointer
CPPFLAGS = -Iinclude
SRC = src/poly.c src/ntt.c src/shake.c src/round.c src/encode.c src/sample.c src/vector.c src/keygen.c src/sign.c src/verify.c src/message.c
ARM_CC = arm-none-eabi-gcc
ARM_OBJCOPY = arm-none-eabi-objcopy
ARM_SIZE = arm-none-eabi-size
ARM_INC =
ARM_LIB =
ARM_CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -std=c11 -O2 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow
ARM_COMMON = $(SRC) platform/cortexm4/startup.c platform/cortexm4/mps2_io.c
ARM_SRC = $(ARM_COMMON) platform/cortexm4/test_main.c
ARM_DEPS = $(wildcard include/*.h) src/mldsa44_internal.h src/zetas.inc src/keccak_tables.inc platform/cortexm4/platform.h
ARM_BENCH = $(ARM_COMMON) platform/cortexm4/core.c platform/cortexm4/bench_main.c

.PHONY: test model shake sample keygen sign verify prehash differential vectors arm-mps2 arm-mps2-bench clean

build/test_poly: test/test_poly.c src/poly.c src/ntt.c src/zetas.inc include/mldsa_poly.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_poly.c src/poly.c src/ntt.c -o $@

build/test_round: test/test_round.c src/round.c src/poly.c src/mldsa44_internal.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) test/test_round.c src/round.c src/poly.c src/ntt.c -o $@

build/test_encode: test/test_encode.c src/encode.c src/poly.c src/mldsa44_internal.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) test/test_encode.c src/encode.c src/poly.c src/ntt.c -o $@

build/libmldsa.so: src/poly.c src/ntt.c src/zetas.inc include/mldsa_poly.h src/shake.c src/keccak_tables.inc include/mldsa_shake.h src/round.c src/encode.c src/sample.c src/vector.c src/keygen.c src/sign.c src/verify.c src/message.c src/mldsa44_internal.h include/mldsa44.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) -fPIC -shared $(SRC) -o $@

build/test_negative: test/test_negative.c $(SRC) include/mldsa44.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) test/test_negative.c $(SRC) -o $@

test: build/test_poly build/test_round build/test_encode build/test_negative
	./build/test_poly $(SEED)
	./build/test_round
	./build/test_encode
	./build/test_negative

model: build/libmldsa.so
	python3 tools/check_model.py build/libmldsa.so

vectors:
	python3 tools/fetch_nist.py

shake: build/libmldsa.so vectors
	python3 test/test_shake.py build/libmldsa.so build/nist

sample: build/libmldsa.so
	python3 test/test_sample.py build/libmldsa.so

keygen: build/libmldsa.so vectors
	python3 test/test_keygen.py build/libmldsa.so build/nist

sign: build/libmldsa.so vectors
	python3 test/test_sign.py build/libmldsa.so build/nist

verify: build/libmldsa.so vectors
	python3 test/test_verify.py build/libmldsa.so build/nist

prehash: build/libmldsa.so vectors
	python3 test/test_prehash.py build/libmldsa.so build/nist

differential: build/libmldsa.so
	PYTHONPATH=build/oracle python3 test/test_differential.py build/libmldsa.so

build/arm/mps2.elf: $(ARM_SRC) $(ARM_DEPS) platform/cortexm4/mps2.ld platform/cortexm4/mps2_vectors.inc
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) $(ARM_SRC) -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

build/arm/mps2.bin: build/arm/mps2.elf
	$(ARM_OBJCOPY) -O binary $< $@

arm-mps2: build/arm/mps2.bin
	$(ARM_SIZE) build/arm/mps2.elf

build/arm/mps2_bench.elf: $(ARM_BENCH) $(ARM_DEPS) platform/cortexm4/core.h platform/cortexm4/mps2.ld
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) $(ARM_BENCH) -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_bench.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

arm-mps2-bench: build/arm/mps2_bench.elf
	$(ARM_SIZE) build/arm/mps2_bench.elf

clean:
	rm -rf build
