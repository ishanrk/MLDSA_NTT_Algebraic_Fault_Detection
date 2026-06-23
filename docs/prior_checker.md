# Abdelmonem two checksum NTT checker

This implements the Dilithium construction in Abdelmonem, Holzbaur, Raddum, and Zeh, [ePrint 2025/170](https://eprint.iacr.org/2025/170.pdf), Sections 3.1–3.3 and 4.1–4.2. The implementation and generator were written from the equations, without using supplementary implementation code. The preflight HEAD was `94d0263c35d0948f100b14e91f4f83a65d66ca95`; the compact host and QEMU suites passed there.

## Network and representation

Let `T` be our forward transform with column inputs. Every coefficient is an ordinary canonical `uint32_t` field value in `[0,q)`, with `q=8380417`. There is no Montgomery factor, lazy representation, or final forward scaling. The production NTT evaluates at `1753^(2*BitRev8(i)+1)` in slot `i`. The paper's output slot `m` evaluates at `1753^(2*m+1)`, so `m=BitRev8(i)`.

Boundary `l` is the array after exactly `l` layers, including the copied input at boundary 0 and final output at boundary 8. Location `r=256*l+i` names array slot `i` at that boundary. There are `256*(8+1)=2304` locations, and `2304*2303/2=2653056` distinct pairs.

| Layer from boundary | Butterfly distance `len` | Blocks | Twiddle table indices |
| --- | ---: | ---: | --- |
| 0 | 128 | 1 | 1 |
| 1 | 64 | 2 | 2–3 |
| 2 | 32 | 4 | 4–7 |
| 3 | 16 | 8 | 8–15 |
| 4 | 8 | 16 | 16–31 |
| 5 | 4 | 32 | 32–63 |
| 6 | 2 | 64 | 64–127 |
| 7 | 1 | 128 | 128–255 |

Within block `g`, `off=2*len*g` and the pairs are `(j,j+len)` for `off<=j<off+len`. The twiddle is `1753^BitRev8(2^l+g)`. A butterfly sends `(u,v)` to `(u+z*v,u-z*v)` modulo `q`, reducing each product and sum immediately. Input and output slots retain their physical array indices within each layer; the bit reversal maps them to mathematical residue indices.

At boundary `l`, write `i=g*(256/2^l)+pos`. The corresponding paper wire is `w=BitRev_l(g)*(256/2^l)+pos`. Put `mu=BitRev_l(g)`. A unit deviation reaches natural output `m` exactly when `m mod 2^l=mu`, with coefficient `1753^((2*m+1)*pos)`. `tools/ntt_network.py` compares this formula against propagation through the exact butterfly graph for every modeled location. This also checks the output permutation, not just an end to end transform identity.

The summation printed in Equation (12) is inconsistent with its output-specific propagation interpretation. The coefficient above follows from the residue decomposition in its proof and the weighted sum in Equation (17); the generator checks it against the entire actual network. No printed propagation expression is assumed without this check.

## Rows and construction

For output rows `a` and `alpha`, the input rows are `b=T^T*a` and `beta=T^T*alpha`. The paper uses row inputs in some places; our transpose notation expresses the same checksum equality for column inputs.

Section 4.1 sets `b[j]=1`. In natural output order, with `x_m=1753^(2*m+1)`, the independently derived row is

```
a[m] = (1/256) * sum(x_m^(-j) for j=0..255)
     = 2 / (256 * (1-x_m^(-1))) mod q
```

For each wire form `v_r`, compute `A_r=a^T*v_r`. All `A_r` are nonzero. Following the output-coordinate recursion in Theorem 5 and Section 4.2, fix natural `alpha[128..255]=1`, then choose the remaining coordinates in descending order. For each pair form `v_r/A_r-v_s/A_s`, assign its constraint to the smallest output coordinate with a nonzero coefficient. At that coordinate all higher coordinates have been fixed, and the constraint excludes exactly one field value. Single-response constraints also exclude values that make the second response zero. Pick the smallest legal value; the paper does not specify a tie break. This is its output-coordinate construction, with no intermediate boundary assignment or random search.

The sufficient bound is `(2*256-1)*2304=1177344`, below `q`. The actual largest forbidden set is recorded in the generated certificate.

The printed Section 4.2 range ends at `N/2-1`, although it calls the fixed portion half the entries. Theorem 3 uses `N/2..N-1`. We use exactly that 128 entry half. Appendix A.1 prints a different placement of its 128 ones and different free-coordinate choices. We generate an instance from the body construction rather than importing that appendix table. Every row identity and determinant is independently certified, so the particular permitted choices are explicit.

Finally, compute `beta[j]=sum(alpha[m]*x_m^j)` and permute the two output rows into production order. Natural `alpha[128..255]=1` becomes all odd physical output slots. The C tables therefore store `a[256]`, `beta[256]`, and only `alpha[128]` for even slots. The input row `b` and odd output weights are implicit ones. All four full rows are included in the certificate digest in production order.

## Exact certificate

```sh
python3 tools/gen_prior_checker.py
python3 tools/gen_prior_checker.py --check
```

The generator uses exact integer arithmetic modulo `q`. It checks the primitive root, all unit propagation vectors, both row identities by direct evaluation and a separate graph pullback, both response coordinates at every boundary, and every pair determinant `A_r*B_s-A_s*B_r`. The checked in [certificate](prior_certificate.json) records the counts and SHA256 digest. The coefficient digest concatenates full `b`, `a`, `beta`, and `alpha` rows as little endian 32 bit words. The network digest covers ordered butterfly triples for all eight layers.

This run certified all 2653056 pairs with zero zero determinants, zero zero first responses, and zero zero second responses. A generation run took 7.73 seconds on this host; runtime is not part of the deterministic certificate.

## Scope

The claim concerns at most two additive field deviations at distinct modeled forward NTT boundary wires. Checker arithmetic, constants, comparison, and control flow are trusted. Two deviations at one wire combine into one; exact cancellation causes no result error. A shared twiddle corruption can affect many modeled wires and is outside this two deviation guarantee. Physical injection resistance and physical Cortex M4 cycle, flash, RAM, and stack measurements remain pending.
