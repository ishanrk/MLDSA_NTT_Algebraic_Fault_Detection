CC = gcc
OPT = -O2
SAN =
SEED =
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow $(OPT) $(SAN) -fno-omit-frame-pointer
CPPFLAGS = -Iinclude

.PHONY: test model clean

build/test_poly: test/test_poly.c src/poly.c src/ntt.c src/zetas.inc include/mldsa_poly.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test/test_poly.c src/poly.c src/ntt.c -o $@

build/libmldsa.so: src/poly.c src/ntt.c src/zetas.inc include/mldsa_poly.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared src/poly.c src/ntt.c -o $@

test: build/test_poly
	./build/test_poly $(SEED)

model: build/libmldsa.so
	python3 tools/check_model.py build/libmldsa.so

clean:
	rm -rf build
