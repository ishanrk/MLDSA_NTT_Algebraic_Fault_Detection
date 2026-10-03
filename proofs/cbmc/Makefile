CBMC ?= cbmc
# use arm headers so 64 bit values stay 64 bit
ARM_CPP ?= arm-none-eabi-gcc
PPDIR = ../../build/cbmc
SRC = $(PPDIR)/round.i $(PPDIR)/poly.i
HARNESS = $(addprefix $(PPDIR)/,power2round.i decompose.i decompose_wrappers.i \
          use_hint.i hint_recovery.i arithmetic.i)
FLAGS = --arch arm --32 --little-endian \
        --bounds-check --pointer-check --signed-overflow-check \
        --undefined-shift-check --unwinding-assertions

.PHONY: all
all: $(HARNESS) $(SRC)
	$(CBMC) $(PPDIR)/power2round.i $(SRC) $(FLAGS) --function harness --unwind 1
	$(CBMC) $(PPDIR)/decompose.i $(SRC) $(FLAGS) --function harness --unwind 1
	$(CBMC) $(PPDIR)/decompose_wrappers.i $(SRC) $(FLAGS) --function harness --unwind 1
	$(CBMC) $(PPDIR)/use_hint.i $(SRC) $(FLAGS) --function harness --unwind 1
	$(CBMC) $(PPDIR)/hint_recovery.i $(SRC) $(FLAGS) --function harness --unwind 1
	$(CBMC) $(PPDIR)/arithmetic.i $(SRC) $(FLAGS) --function add --unwind 1
	$(CBMC) $(PPDIR)/arithmetic.i $(SRC) $(FLAGS) --function sub --unwind 1
	$(CBMC) $(PPDIR)/arithmetic.i $(SRC) $(FLAGS) --function center --unwind 1
	$(CBMC) $(PPDIR)/arithmetic.i $(SRC) $(FLAGS) --function reduce --unwind 7

$(PPDIR):
	mkdir -p $@

$(PPDIR)/%.i: %.c | $(PPDIR)
	$(ARM_CPP) -E -I../../include -I../../src $< -o $@

$(PPDIR)/round.i: ../../src/round.c | $(PPDIR)
	$(ARM_CPP) -E -I../../include -I../../src $< -o $@

$(PPDIR)/poly.i: ../../src/poly.c | $(PPDIR)
	$(ARM_CPP) -E -I../../include -I../../src $< -o $@

$(PPDIR)/decompose_wrappers.i: decompose.c | $(PPDIR)
	$(ARM_CPP) -E -DCHECK_WRAPPERS -I../../include -I../../src $< -o $@
