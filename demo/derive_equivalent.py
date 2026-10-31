#!/usr/bin/env python3
"""Demonstrate equivalent ML-DSA-44 signing key from s1 plus original public key.
No original s2, t0, or secret nonce key are inputs to reconstruct().
"""
import hashlib
from pathlib import Path

Q=8380417
N=256
ZETA=1753
D=13

def centered(v): return v if v<=Q//2 else v-Q

def decode_bits(blob,bits,top=0,signed=False):
    vals=[]
    for i in range(N):
        v=sum(((blob[(i*bits+j)//8]>>((i*bits+j)%8))&1)<<j for j in range(bits))
        vals.append((top-v)%Q if signed else v)
    return vals

def encode_bits(vals,bits,top=0,signed=False):
    out=bytearray(32*bits)
    for i,x in enumerate(vals):
        v=(top-centered(x)) if signed else x
        assert 0<=v<1<<bits,(i,v)
        for j in range(bits):
            out[(i*bits+j)//8] |= ((v>>j)&1)<<((i*bits+j)%8)
    return bytes(out)

def rev8(x): return int(f'{x:08b}'[::-1],2)
ROOTS=[pow(ZETA,2*rev8(i)+1,Q) for i in range(N)]
INVROOTS=[pow(x,Q-2,Q) for x in ROOTS]
NINV=pow(N,Q-2,Q)
assert len(set(ROOTS))==N and all(pow(x,N,Q)==Q-1 for x in ROOTS)

def ntt(poly):
    return [sum(c*pow(x,j,Q) for j,c in enumerate(poly))%Q for x in ROOTS]

def intt(vals):
    out=[0]*N
    for a,y in zip(INVROOTS,vals):
        v=1
        for j in range(N):
            out[j]=(out[j]+y*v)%Q
            v=v*a%Q
    return [x*NINV%Q for x in out]

def sample_a(rho,row,col):
    # SHAKE128 byte-stream consistent with FIPS204 RejNTTPoly and the repo's sample_ntt.
    stream=hashlib.shake_128(rho+bytes([col,row])).digest(4096)
    p=[]
    for j in range(0,len(stream)-2,3):
        v=stream[j] | stream[j+1]<<8 | (stream[j+2]&127)<<16
        if v<Q:
            p.append(v)
            if len(p)==N:return p
    raise AssertionError('not enough SHAKE output')

def power2round(v):
    v%=Q
    t=v%(1<<D)
    if t>(1<<(D-1)): t-=1<<D
    return (v-t)//(1<<D),t

def reconstruct(pk,s1):
    assert len(pk)==1312 and len(s1)==4 and all(len(row)==N for row in s1)
    rho=pk[:32]
    tr=hashlib.shake_256(pk).digest(64)
    t1=[decode_bits(pk[32+320*i:32+320*(i+1)],10) for i in range(4)]
    s1_ntt=[ntt(row) for row in s1]
    s2=[];t0=[];t_val=[]
    for r in range(4):
        t_ntt=[0]*N
        for c in range(4):
            ai=sample_a(rho,r,c)
            for j in range(N):t_ntt[j]=(t_ntt[j]+ai[j]*s1_ntt[c][j])%Q
        t=intt(t_ntt);t_val.append(t)
        s2row=[];t0row=[]
        for j in range(N):
            for cand in (0,1,-1,2,-2):
                hi,lo=power2round(t[j]+cand)
                if hi==t1[r][j]:
                    s2row.append(cand%Q);t0row.append(lo%Q)
                    break
            else:raise AssertionError(f'no s2 candidate found: {r,j,t[j],t1[r][j]}')
        s2.append(s2row);t0.append(t0row)
    key=hashlib.sha256(b'equivalent research signing key'+pk).digest()
    sk = bytearray(rho + key + tr)
    sk += b''.join(encode_bits(row,3,2,True) for row in s1)
    sk += b''.join(encode_bits(row,3,2,True) for row in s2)
    sk += b''.join(encode_bits(row,13,4096,True) for row in t0)
    assert len(sk)==2560
    # Check mathematical key consistency and public-key encoding.
    for r in range(4):
        for j in range(N):
            hi,lo=power2round(t_val[r][j]+s2[r][j])
            assert hi==t1[r][j] and lo==centered(t0[r][j])
    return bytes(sk),s2,t0,t_val

def sk_parse_original(raw):
    assert len(raw)==2560
    ss1=[decode_bits(raw[128+96*i:128+96*(i+1)],3,2,True) for i in range(4)]
    ss2=[decode_bits(raw[512+96*i:512+96*(i+1)],3,2,True) for i in range(4)]
    tt0=[decode_bits(raw[896+416*i:896+416*(i+1)],13,4096,True) for i in range(4)]
    return ss1,ss2,tt0

def main():
    d=Path(__file__).resolve().parent
    sk=(d/'original_sk.bin').read_bytes()
    pk=(d/'pk.bin').read_bytes()
    s1,s2_old,t0_old=sk_parse_original(sk)
    forged,s2new,t0new,t=reconstruct(pk,s1)
    for r in range(4):
      for j in range(N):
       assert (t[r][j]+s2_old[r][j]-(t0_old[r][j]+(power2round(t[r][j]+s2_old[r][j])[0]<<D)))%Q==0
    same_s2=sum(v==w for a,b in zip(s2new,s2_old) for v,w in zip(a,b))
    print('Reconstructed alternative sk:',len(forged),'bytes. s1 unchanged, same s2 coefficients',same_s2,'of 1024.')
    assert forged!=sk
    (d/'alternative_sk.bin').write_bytes(forged)
if __name__=='__main__':main()
