# Scope of the fault detection claim

The guarantee concerns **at most two additive deviations at modeled forward NTT boundary wires**, interpreted over the finite field `F_q` with `q=8380417`. Every slot of the transform work array at the input boundary and after each complete layer is a modeled wire. The production transform has eight layers. Layer order, array indices and twiddles are those of the implementation, not arbitrary intermediate instruction states.

For input `p`, the working array input boundary is observed after the expected input checks have been captured and the input has been copied. Corrupting a caller's input before the expected checks are captured changes the checked input itself and is not covered as a deviation from that captured input. Trusted checker arithmetic also includes the expected input checksum computation.

The output propagation of a unit deviation at location `r` is `v_r`. The two scalar checks respond with `A_r=a^T*v_r` and `B_r=alpha^T*v_r`. For distinct locations `r,s`, a nonzero determinant `A_r*B_s-A_s*B_r` prevents a nonzero pair of additive magnitudes from cancelling both checks. A nonzero first response covers a single deviation. Two deviations at the same wire combine into one; exact cancellation has no erroneous transform result to detect. The claim is detection, not correction, localization or recovery.

## Trusted components and preconditions

The guarantee assumes finite field arithmetic with the implementation's documented canonical representation and valid object contracts. Checksum arithmetic, stored weights, expected values and the comparison are trusted. Control flow is trusted unless separately analyzed: skipped checks, corrupted returns and faulty error propagation are not supplied with a separate control flow guarantee here. The surrounding scheme must honor a checker error and discard the output.

The exact certificates cover the concrete coefficient conditions. Focused CBMC results cover the documented C components and their assumptions. Neither supplies a proof that every physical fault is equivalent to one of the permitted canonical field deviations.

## Events outside this guarantee

- More than two modeled wire deviations, including a shared event affecting many coefficients.
- Shared twiddle corruption, corruption of checker constants or computation, and corruption of control flow or memory addressing.
- Noncanonical machine values that violate the arithmetic ranges, or invalid pointers/objects outside the implementation contract.
- Faults in inverse NTT, matrix sampling, SHAKE, encoding or other unprotected scheme operations.
- Physical or side channel resistance of the complete device, algorithm or protocol.

Physical Cortex M4 correctness and DWT/stack measurements establish execution and cost on the recorded board and input schedule. They do not by themselves establish resistance against every real physical fault mechanism. Selected C boundary injections check that modeled deviations reach and are rejected by the implementation; they are software experiments, not physical glitch experiments. Physical fault injection has not been evaluated in the current artifact.
