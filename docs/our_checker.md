# Deterministic intermediate boundary checker

Our construction uses boundary `k=4` of the existing forward NTT. The baseline and published checker keep their original transforms and constants. All rows here use physical production array indices and canonical field values modulo `q=8380417`.

## Model and criterion

Write the column transform as `T`. Boundary `l` is the array after `l` complete layers, including input boundary 0 and output boundary 8. Location `r=256*l+i` denotes slot `i`. A unit additive deviation there propagates to output vector `v_r`. For output rows `a` and `alpha`, define `A_r=a^T v_r` and `B_r=alpha^T v_r`. The corresponding input rows are `b=T^T a` and `beta=T^T alpha`.

The first expected checksum is the ordinary input sum, so `b` is all ones. The generator obtains `a=T^(-T)b` by inverse transpose butterflies. It checks this row against direct evaluation at `1753^(2*BitRev8(i)+1)` and against a separate graph pullback. Every modeled first response is nonzero.

For distinct locations `r,s`, the determinant `A_r B_s-A_s B_r` must be nonzero. This means the two response columns are independent. Consequently two additive magnitudes cannot cancel both checks unless both are zero. With nonzero first responses, the same condition says that all `B_r/A_r` are distinct. A single nonzero deviation is detected by the first check.

Coverage concerns at most two additive field deviations at modeled forward NTT boundary wires. Checker arithmetic, constants, comparisons, and control flow are trusted. Deviations at the same wire combine; exact cancellation leaves no result error. Shared corruptions that affect more than two modeled wires are outside this guarantee. The inverse NTT and matrix sampling are outside this protection. Physical injection resistance remains unmeasured.

## Intermediate variables

Let `P_l` map input to boundary `l`, and `S_k` map boundary `k` to output, so `T=S_k P_k`. The variable vector `u` is the checksum row at boundary `k`. A unit fault at boundary `l` is represented there by

```
w_r = P_k P_l^(-1) e_i
alpha = S_k^(-T) u
beta = P_k^T u
W_r(u) = w_r^T u / A_r
```

For `l<=k`, propagate the unit wire forward from `l` to `k`. For `l>k`, run inverse butterflies from `l` back to `k`. Every resulting intermediate vector is checked by propagating it to the final output and comparing with the independently derived unit wire formula used by the prior network model. This shares network modeling code, without reading prior checker constants or invoking its construction.

A wire before the intermediate boundary has `2^(k-l)` nonzero intermediate coordinates; a wire after it has `2^(l-k)`. At each intermediate coordinate the number of incident modeled wires is

```
K(k) = 2^(k+1) + 2^(h-k+1) - 3
M = n*(h+1)
D(k) = K(k)*M - K(k)*(K(k)+1)/2
```

There are at most `D(k)` pairs with at least one incident wire: subtract the pairs among the `M-K(k)` nonincident wires from all `M*(M-1)/2` pairs. Any pair difference with a nonzero coefficient at this coordinate belongs to that set. In particular its assigned constraint group has at most `D(k)` entries.

For `n=256`, `h=8`, and `k=4`, the generator verifies `M=2304`, `K=61`, and `D=138653`. The sufficient condition `8380417>138653` holds. It also verifies the exact incidence of 61 at every coordinate and the group bound. The largest group has exactly 138653 constraints.

## Greedy construction

For each pair form `H_rs=W_r-W_s`, verify that it is nonzero and assign it to its greatest nonzero coordinate `j`. Process coordinates in increasing physical index order. Maintain each form's evaluation on the already chosen prefix through the partial values of `W_r`. A constraint assigned to `j` forbids

```
u_j = -(H_rs evaluated on the prefix) / H_rs[j] mod q
```

Collect those values in a set and choose the smallest nonnegative value absent from it. At most `D(k)<q` choices are forbidden, so a choice exists. The search stops after at most the set size plus one membership checks and does not scan the whole field. Later coordinates cannot change already satisfied constraints.

After the assignment, compute all normalized responses. To make every second response nonzero, choose the smallest `t` outside `{ -W_r(u) }`. Replace the intermediate row by `u+t*c`, where `c=S_k^T a` is the first checksum row at boundary `k`. This adds `t` to every normalized response and preserves every pair determinant. The generated instance uses `t=1`. Only after this shift are the final output and input rows emitted.

The construction groups `M*(M-1)/2` constraints. With at most `s=max(2^k,2^(h-k))` nonzero coefficients per intermediate form, grouping takes `O(M^2*(s+log q))` field arithmetic work including modular inverses. Greedy evaluation takes `O(M^2+n*K)` further work. Constraint arrays occupy `O(M^2)` memory; sparse forms and incidence lists occupy `O(n*K)`. Network verification and the direct determinant certificate add polynomial work. These describe this exact integer implementation, rather than an optimized construction algorithm.

The improvement over the prior output coordinate recursion is the sufficient field bound obtained from intermediate support. The prior implementation uses `(2*n-1)*M=1177344` as its sufficient bound and fixes half its output weights to one. This construction uses `D=138653` and assigns every intermediate variable greedily. A smaller existence bound does not establish lower execution cost.

## Reproduction and certificate

```sh
python3 tools/gen_our_checker.py
python3 tools/gen_our_checker.py --check
```

The [certificate](our_certificate.json) records the unshifted intermediate assignment, smallest shift, group sizes, forbidden counts, and the exact network and coefficient digests. Runtime is printed separately so it does not affect deterministic artifacts. The coefficient digest covers full `b`, `a`, `beta`, and `alpha` in production order, serialized as little endian 32 bit words. The C tables store `a`, `beta`, and `alpha`; the all one input row is implicit.

The generator verifies both row identities by direct evaluation and graph pullback, both responses for every modeled wire, intermediate propagation, nonzero first and second responses, distinct normalized responses, and all 2653056 pair determinants independently of the greedy test. All failure counts are zero. A generation on this host took 6.642 seconds including certification. Regeneration is checked byte for byte against the emitted tables and certificate.
