import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/verify'


def without_comments(text):
    tokens = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/'
    # leave quoted strings alone when dropping comments
    def replace(match):
        token = match.group()
        if token.startswith(('//', '/*')):
            return ''.join('\n' if char == '\n' else ' ' for char in token)
        return token
    return re.sub(tokens, replace, text, flags=re.S)


def write(name, text):
    temporary = OUT / f'{name}.{os.getpid()}.tmp'
    temporary.write_text(text)
    temporary.replace(OUT / name)


def block(text, start):
    left = text.index('{', start)
    depth = 1
    right = left + 1
    while depth:
        depth += (text[right] == '{') - (text[right] == '}')
        right += 1
    return text[left + 1:right - 1], right


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    text = without_comments((ROOT / 'src/ntt.c').read_text())
    guard = 'for (unsigned j = off; j < off + len; j++)'
    for name in ('forward', 'inverse'):
        body, _ = block(text, text.index(f'void mldsa_ntt_{name}('))
        copy = re.search(r'for \(unsigned i = 0; i < MLDSA_N; i\+\+\)\s+r->c\[i\] = a->c\[i\];', body)
        assert copy, name
        write(f'{name}_copy.inc', copy.group() + '\n')
        assert body.count(guard) == 1
        view, _ = block(body, body.index(guard))
        write(f'{name}_body.inc', view.strip() + '\n')
        start = body.index('for (unsigned off = 0; off < MLDSA_N; off += 2 * len)')
        _, end = block(body, start)
        write(f'{name}_layer.inc', body[start:end] + '\n')
    for name in ('prior', 'our'):
        text = without_comments((ROOT / f'src/{name}.c').read_text())
        body, _ = block(text, text.index(f'int mldsa_ntt_forward_{name}('))
        guard = 'for (unsigned i = 0; i < MLDSA_N; i++)'
        assert body.count(guard) == 2
        first, end = block(body, body.index(guard))
        second, last = block(body, body.index(guard, end))
        assert body[:body.index(guard)].strip() == 'uint32_t x = 0, y = 0, u = 0, v = 0;'
        assert body[end:body.index(guard, end)].strip() == 'mldsa_ntt_forward(r, a);'
        final = body[last:].strip()
        assert re.fullmatch(r'return [^;]+;', final)
        initial = body[:body.index(guard)].strip()
        for label, view in (('initial', initial), ('input', first), ('output', second), ('return', final)):
            write(f'{name}_{label}.inc', view.strip() + '\n')


if __name__ == '__main__':
    generate()
