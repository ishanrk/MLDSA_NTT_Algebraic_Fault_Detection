CC = gcc
OPT = -O2
SAN =
SEED =
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow $(OPT) $(SAN) -fno-omit-frame-pointer
CPPFLAGS = -Iinclude
SRC = src/poly.c src/ntt.c src/prior.c src/our.c src/shake.c src/round.c src/encode.c src/sample.c src/vector.c src/keygen.c src/sign.c src/verify.c src/message.c
ARM_CC = arm-none-eabi-gcc
ARM_OBJCOPY = arm-none-eabi-objcopy
ARM_SIZE = arm-none-eabi-size
ARM_INC =
ARM_LIB =
ARM_CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -std=c11 -O2 -ffreestanding -fno-builtin -fdata-sections -ffunction-sections -Wall -Wextra -Wpedantic -Wconversion -Wshadow
ARM_COMMON = $(SRC) platform/cortexm4/startup.c platform/cortexm4/mps2_io.c
ARM_SRC = $(ARM_COMMON) platform/cortexm4/test_main.c
ARM_DEPS = $(wildcard include/*.h) src/mldsa44_internal.h src/zetas.inc src/prior_tables.inc src/our_tables.inc src/keccak_tables.inc platform/cortexm4/platform.h
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

build/libmldsa.so: $(SRC) $(ARM_DEPS)
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) -fPIC -shared $(SRC) -o $@

build/libmldsa_prior.so: $(SRC) $(ARM_DEPS)
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) -DMLDSA_PRIOR_CHECKER -fPIC -shared $(SRC) -o $@

build/libmldsa_our.so: $(SRC) $(ARM_DEPS)
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc $(CFLAGS) -DMLDSA_OUR_CHECKER -fPIC -shared $(SRC) -o $@

build/test_our: $(SRC) test/our_cases.c test/our_cases.h test/host_io.c platform/cortexm4/test_main.c platform/cortexm4/mps2_vectors.inc $(ARM_DEPS)
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc -Itest -Iplatform/cortexm4 $(CFLAGS) -DMLDSA_OUR_CHECKER -DMLDSA_TEST_FAULTS platform/cortexm4/test_main.c test/our_cases.c test/host_io.c $(SRC) -o $@

.PHONY: our
our: build/test_our
	./build/test_our

build/test_prior: $(SRC) test/prior_cases.c test/prior_cases.h test/host_io.c platform/cortexm4/test_main.c platform/cortexm4/mps2_vectors.inc src/prior_tables.inc $(ARM_DEPS)
	mkdir -p build
	$(CC) $(CPPFLAGS) -Isrc -Itest -Iplatform/cortexm4 $(CFLAGS) -DMLDSA_PRIOR_CHECKER -DMLDSA_TEST_FAULTS platform/cortexm4/test_main.c test/prior_cases.c test/host_io.c $(SRC) -o $@

.PHONY: prior
prior: build/test_prior
	./build/test_prior

build/count_poly.o: src/poly.c include/mldsa_poly.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -Dmldsa_add=count_add -Dmldsa_sub=count_sub -Dmldsa_mul=count_mul -c src/poly.c -o $@

build/count_prior: test/count_prior.c src/ntt.c src/prior.c src/prior_tables.inc build/count_poly.o $(ARM_DEPS)
	$(CC) $(CPPFLAGS) $(CFLAGS) test/count_prior.c src/ntt.c src/prior.c build/count_poly.o -o $@

build/count_checkers: test/count_checkers.c src/ntt.c src/prior.c src/our.c build/count_poly.o $(ARM_DEPS)
	$(CC) $(CPPFLAGS) $(CFLAGS) test/count_checkers.c src/ntt.c src/prior.c src/our.c build/count_poly.o -o $@

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

build/arm/mps2_prior.elf: $(ARM_SRC) $(ARM_DEPS) platform/cortexm4/mps2.ld platform/cortexm4/mps2_vectors.inc test/prior_cases.c test/prior_cases.h
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Itest -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) -DMLDSA_PRIOR_CHECKER -DMLDSA_TEST_FAULTS $(ARM_SRC) test/prior_cases.c -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_prior.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

.PHONY: arm-mps2-prior arm-mps2-prior-bench
arm-mps2-prior: build/arm/mps2_prior.elf
	$(ARM_SIZE) build/arm/mps2_prior.elf

build/arm/mps2_our.elf: $(ARM_SRC) $(ARM_DEPS) platform/cortexm4/mps2.ld platform/cortexm4/mps2_vectors.inc test/our_cases.c test/our_cases.h
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Itest -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) -DMLDSA_OUR_CHECKER -DMLDSA_TEST_FAULTS $(ARM_SRC) test/our_cases.c -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_our.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

.PHONY: arm-mps2-our
arm-mps2-our: build/arm/mps2_our.elf
	$(ARM_SIZE) build/arm/mps2_our.elf

build/arm/mps2_bench.elf: $(ARM_BENCH) $(ARM_DEPS) platform/cortexm4/core.h platform/cortexm4/mps2.ld
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) $(ARM_BENCH) -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_bench.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

arm-mps2-bench: build/arm/mps2_bench.elf
	$(ARM_SIZE) build/arm/mps2_bench.elf

build/arm/mps2_prior_bench.elf: $(ARM_BENCH) $(ARM_DEPS) platform/cortexm4/core.h platform/cortexm4/mps2.ld
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) -DMLDSA_PRIOR_CHECKER $(ARM_BENCH) -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_prior_bench.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

arm-mps2-prior-bench: build/arm/mps2_prior_bench.elf
	$(ARM_SIZE) build/arm/mps2_prior_bench.elf

build/arm/mps2_our_bench.elf: $(ARM_BENCH) $(ARM_DEPS) platform/cortexm4/core.h platform/cortexm4/mps2.ld
	mkdir -p build/arm
	$(ARM_CC) $(CPPFLAGS) -Isrc -Iplatform/cortexm4 $(ARM_INC) $(ARM_CFLAGS) -DMLDSA_OUR_CHECKER $(ARM_BENCH) -nostartfiles -nostdlib -Wl,--gc-sections -Wl,-Map,build/arm/mps2_our_bench.map -Tplatform/cortexm4/mps2.ld $(ARM_LIB) -lc -lgcc -o $@

.PHONY: arm-mps2-our-bench
arm-mps2-our-bench: build/arm/mps2_our_bench.elf
	$(ARM_SIZE) build/arm/mps2_our_bench.elf

clean:
	rm -rf build
