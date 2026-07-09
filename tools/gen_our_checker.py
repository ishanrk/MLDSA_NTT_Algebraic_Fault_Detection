#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from array import array
from pathlib import Path

from gen_zetas import OUT as ZETAS, render as render_zetas, table
from ntt_network import H, N, Q, bitrev8, layers, propagation, pullback
from ntt_network import transpose, verify_network

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'src/our_tables.inc'
CERT = ROOT / 'docs/our_certificate.json'


def transform(x, net, inverse=False, transposed=False):
    x = x.copy()
    half = pow(2, -1, Q)
    for layer in reversed(net) if inverse != transposed else net:
        for i, j, z in layer:
            a, b = x[i], x[j]
            if inverse:
                inv = pow(z, -1, Q)
                if transposed:
                    x[i], x[j] = (a + inv * b) * half % Q, (a - inv * b) * half % Q
                else:
                    x[i], x[j] = (a + b) * half % Q, (a - b) * half * inv % Q
            elif transposed:
                x[i], x[j] = (a + b) % Q, z * (a - b) % Q
            else:
                x[i], x[j] = (a + z * b) % Q, (a - z * b) % Q
    return x


def intermediate(net, v, first, k):
    rows = []
    for r, out in enumerate(v):
        l, i = divmod(r, N)
        x = [0] * N
        x[i] = 1
        x = transform(x, net[l:k]) if l <= k else transform(x, net[k:l], inverse=True)
        assert transform(x, net[k:]) == [out.get(bitrev8(j), 0) for j in range(N)], r
        inv = pow(first[r], -1, Q)
        rows.append({j: c * inv % Q for j, c in enumerate(x) if c})
    assert len({tuple(row.items()) for row in rows}) == len(rows)
    return rows


def construct(rows, bound):
    cols = [[] for _ in range(N)]
    for r, row in enumerate(rows):
        for j, c in row.items():
            cols[j].append((r, c))
    groups = [(array('H'), array('H'), array('I')) for _ in range(N)]
    assert len(rows) <= 65536
    for r, x in enumerate(rows):
        for s in range(r):
            y = rows[s]
            j = max(max(x), max(y))
            c = (x.get(j, 0) - y.get(j, 0)) % Q
            if not c:
                for j in sorted(x.keys() | y.keys(), reverse=True):
                    c = (x.get(j, 0) - y.get(j, 0)) % Q
                    if c:
                        break
                assert c, (r, s)
            groups[j][0].append(r)
            groups[j][1].append(s)
            groups[j][2].append(pow(c, -1, Q))
    sizes = [len(group[0]) for group in groups]
    assert sum(sizes) == len(rows) * (len(rows) - 1) // 2
    assert max(sizes) <= bound < Q
    u, part, banned_sizes = [0] * N, [0] * len(rows), []
    for j in range(N):
        banned = {(part[s] - part[r]) * inv % Q
                  for r, s, inv in zip(*groups[j])}
        x = 0
        while x in banned:
            x += 1
        assert x <= len(banned) <= bound and x < Q
        u[j] = x
        banned_sizes.append(len(banned))
        for r, c in cols[j]:
            part[r] = (part[r] + c * x) % Q
        if j % 32 == 0 or j == N - 1:
            print(f'coordinate {j}: constraints {sizes[j]} forbidden {len(banned)} chosen {x}', flush=True)
    assert len(set(part)) == len(rows)
    assert part == [sum(c * u[j] for j, c in row.items()) % Q for row in rows]
    return u, part, sizes, banned_sizes, [len(col) for col in cols]


def render(name, row):
    lines = [f'static const uint32_t {name}[{len(row)}] = {{']
    for i in range(0, len(row), 8):
        lines.append('    ' + ', '.join(f'{x}U' for x in row[i:i + 8]) + ',')
    return '\n'.join(lines + ['};'])


def generate():
    k = H // 2
    m = N * (H + 1)
    degree = (1 << (k + 1)) + (1 << (H - k + 1)) - 3
    bound = degree * m - degree * (degree + 1) // 2
    assert N == 1 << H and (N, H, Q, k) == (256, 8, 8380417, 4)
    assert (m, degree, bound) == (2304, 61, 138653) and Q > bound
    assert ZETAS.read_text() == render_zetas(table())
    net, v = layers(), propagation()
    verify_network(v)
    print('production network propagation verified', flush=True)
    b = [1] * N
    a = transform(b, net, inverse=True, transposed=True)
    assert transpose([a[bitrev8(i)] for i in range(N)]) == b
    first = pullback(a)
    assert len(first) == m and first[:N] == b and all(first)
    for r, row in enumerate(v):
        assert first[r] == sum(a[bitrev8(j)] * c for j, c in row.items()) % Q
    rows = intermediate(net, v, first, k)
    c = first[k * N:(k + 1) * N]
    assert all(sum(x * c[j] for j, x in row.items()) % Q == 1 for row in rows)
    u, ratios, sizes, banned, col_sizes = construct(rows, bound)
    assert max(col_sizes) == degree and all(x == degree for x in col_sizes)
    excluded = {(-x) % Q for x in ratios}
    t = 0
    while t in excluded:
        t += 1
    assert t <= m < Q
    shifted = [(x + t * y) % Q for x, y in zip(u, c)]
    alpha = transform(shifted, net[k:], inverse=True, transposed=True)
    beta = transform(shifted, net[:k], transposed=True)
    assert transpose([alpha[bitrev8(i)] for i in range(N)]) == beta
    second = pullback(alpha)
    assert second[:N] == beta
    for r, row in enumerate(v):
        assert second[r] == sum(alpha[bitrev8(j)] * x for j, x in row.items()) % Q
        assert second[r] == first[r] * (ratios[r] + t) % Q
    normalized = [y * pow(x, -1, Q) % Q for x, y in zip(first, second)]
    duplicates = m - len(set(normalized))
    zero = sum((first[r] * second[s] - first[s] * second[r]) % Q == 0
               for r in range(m) for s in range(r))
    assert first.count(0) == second.count(0) == duplicates == zero == 0
    raw = b''.join(x.to_bytes(4, 'little') for row in (b, a, beta, alpha) for x in row)
    content = '// generated by tools/gen_our_checker.py\n\n'
    content += '\n\n'.join(render(name, row) for name, row in
                             (('our_a', a), ('our_beta', beta), ('our_alpha', alpha))) + '\n'
    cert = {
        'n': N, 'q': Q, 'h': H, 'k': k, 'M': m, 'K': degree, 'D': bound,
        'field_bound_passed': Q > bound,
        'modeled_locations': m, 'checked_pairs': m * (m - 1) // 2,
        'zero_first_responses': first.count(0),
        'zero_second_responses': second.count(0),
        'duplicate_normalized_responses': duplicates,
        'zero_determinants': zero,
        'row_identities': 'direct evaluation and network pullback passed',
        'propagation_identity': 'all unit wires matched the production network',
        'intermediate_identity': 'every intermediate vector propagated to its unit wire output',
        'coefficients_sha256': hashlib.sha256(raw).hexdigest(),
        'digest_format': 'b then a then beta then alpha in production order as uint32 little endian',
        'network_sha256': hashlib.sha256(json.dumps(net, separators=(',', ':')).encode()).hexdigest(),
        'stored_coefficients': 3 * N, 'stored_bytes': 12 * N,
        'maximum_coordinate_incidence': max(col_sizes),
        'largest_constraint_group': max(sizes), 'largest_forbidden_set': max(banned),
        'constraints_by_final_coordinate': sizes, 'forbidden_counts': banned,
        'intermediate_assignment': u, 'second_row_shift': t,
        'tie_break': 'smallest legal field value in increasing production intermediate index order',
    }
    return content, json.dumps(cert, indent=2) + '\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    start = time.perf_counter()
    content, cert = generate()
    if args.check:
        assert OUT.read_text() == content, 'checker constants differ'
        assert CERT.read_text() == cert, 'checker certificate differs'
    else:
        OUT.write_text(content)
        CERT.write_text(cert)
    data = json.loads(cert)
    for key in ('M', 'K', 'D', 'checked_pairs', 'zero_first_responses',
                'zero_second_responses', 'duplicate_normalized_responses',
                'zero_determinants', 'coefficients_sha256', 'second_row_shift'):
        print(f'{key}: {data[key]}')
    print(f'construction and certificate seconds: {time.perf_counter() - start:.3f}')


if __name__ == '__main__':
    main()
