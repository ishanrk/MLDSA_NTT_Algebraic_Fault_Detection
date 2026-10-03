CC ?= cc
CBMC ?= cbmc
ARM_CPP ?= arm-none-eabi-gcc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow
CPPFLAGS = -Iinclude -Isrc -Iresearch
SRC = src/poly.c src/ntt.c src/shake.c src/round.c src/encode.c \
      src/sample.c src/vector.c src/keygen.c src/sign.c src/verify.c src/message.c
GUARD = research/block_guard.c
HEADERS = $(wildcard include/*.h) src/mldsa44_internal.h src/zetas.inc \
          src/keccak_tables.inc research/block_guard.h research/block_tables.inc

.DEFAULT_GOAL := test
.PHONY: test vectors cbmc clean

build/libmldsa.so: $(SRC) $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared $(SRC) -o $@

build/libmldsa_nttz.so: $(SRC) $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DMLDSA_FAULTY_PRONE_MEMORY_OPTIMIZATION -fPIC -shared $(SRC) -o $@

build/libmldsa_block.so: $(SRC) $(GUARD) $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -DMLDSA_FAULTY_PRONE_MEMORY_OPTIMIZATION -DMLDSA_BLOCK_CHECKER \
	    -fPIC -shared $(SRC) $(GUARD) -o $@

build/test_negative: test/test_negative.c $(SRC) $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_negative.c $(SRC) -o $@

build/test_poly: test/test_poly.c src/poly.c src/ntt.c $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_poly.c src/poly.c src/ntt.c -o $@

build/test_round: test/test_round.c src/round.c src/poly.c src/ntt.c $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_round.c src/round.c src/poly.c src/ntt.c -o $@

build/test_encode: test/test_encode.c src/encode.c src/poly.c src/ntt.c $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_encode.c src/encode.c src/poly.c src/ntt.c -o $@

build/test_block: test/test_block.c src/poly.c src/ntt.c $(GUARD) $(HEADERS)
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_block.c src/poly.c src/ntt.c $(GUARD) -o $@

vectors: build/libmldsa.so build/libmldsa_nttz.so build/libmldsa_block.so
	python3 test/acvp_compare.py vectors build/libmldsa.so \
	    build/libmldsa_nttz.so build/libmldsa_block.so

test: build/libmldsa.so build/libmldsa_nttz.so build/libmldsa_block.so build/test_poly build/test_round build/test_encode build/test_negative build/test_block
	./build/test_poly
	./build/test_round
	./build/test_encode
	./build/test_negative
	./build/test_block
	python3 research/block_guard.py --check
	python3 test/test_sample.py build/libmldsa.so
	$(MAKE) vectors

cbmc:
	$(MAKE) -C proofs/cbmc
	$(ARM_CPP) -E -Iinclude -Isrc research/block_cbmc.c -o build/cbmc/block_cbmc.i
	$(CBMC) build/cbmc/block_cbmc.i build/cbmc/poly.i --arch arm --32 \
	    --little-endian --bounds-check --pointer-check --signed-overflow-check \
	    --unwind 7 --unwinding-assertions --function normalize
	$(CBMC) build/cbmc/block_cbmc.i build/cbmc/poly.i --arch arm --32 \
	    --little-endian --bounds-check --pointer-check --signed-overflow-check \
	    --unwind 7 --unwinding-assertions --function accumulator

clean:
	rm -rf build

