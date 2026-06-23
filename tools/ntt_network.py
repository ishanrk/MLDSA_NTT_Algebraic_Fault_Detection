from gen_zetas import N, Q, ZETA, bitrev8, table

H = N.bit_length() - 1


def bitrev(x, bits):
    return int(f"{x:0{bits}b}"[::-1], 2) if bits else 0


def layers():
    z = table()
    out = []
    k = 0
    for length in (N >> l for l in range(1, H + 1)):
        layer = []
        for off in range(0, N, 2 * length):
            k += 1
            layer.extend((j, j + length, z[k]) for j in range(off, off + length))
        out.append(layer)
    return out


def forward(a, start=0):
    a = a.copy()
    for layer in layers()[start:]:
        for i, j, z in layer:
            u, t = a[i], z * a[j] % Q
            a[i], a[j] = (u + t) % Q, (u - t) % Q
    return a


def pullback(a):
    out = [None] * (H + 1)
    out[H] = a.copy()
    for l, layer in reversed(list(enumerate(layers()))):
        a = a.copy()
        for i, j, z in layer:
            u, v = a[i], a[j]
            a[i], a[j] = (u + v) % Q, z * (u - v) % Q
        out[l] = a
    return [x for row in out for x in row]


def paper_wire(l, i):
    m = N >> l
    g, pos = divmod(i, m)
    return m * bitrev(g, l) + pos


def propagation():
    out = []
    for l in range(H + 1):
        m = N >> l
        for i in range(N):
            mu, pos = divmod(paper_wire(l, i), m)
            out.append({j: pow(ZETA, (2 * j + 1) * pos, Q)
                        for j in range(mu, N, 1 << l)})
    return out


def verify_network(v):
    net = layers()
    for r, row in enumerate(v):
        l, i = divmod(r, N)
        a = [0] * N
        a[i] = 1
        for layer in net[l:]:
            for j, k, z in layer:
                u, t = a[j], z * a[k] % Q
                a[j], a[k] = (u + t) % Q, (u - t) % Q
        assert a == [row.get(bitrev8(j), 0) for j in range(N)], r


def transpose(a):
    return [sum(a[m] * pow(ZETA, (2 * m + 1) * j, Q)
                for m in range(N)) % Q for j in range(N)]
