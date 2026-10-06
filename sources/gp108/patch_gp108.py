#!/usr/bin/env python3
"""Experimental: append the GP108 (GT 1030) registration block to a built
Forceware 382.69 nv4_mini.sys.

Inputs are the exact 10-5-2026 nv4_mini.sys (with the GP107 block) and the
expanded GeForce 382.33 x86 nvlddmkm.sys. GP108 firmware is read from the donor
at run time and is never stored in this repository.

  python3 sources/gp108/patch_gp108.py --mini <nv4_mini.sys> \
      --donor inputs/geforce-382.33/nvlddmkm.sys --out <dir>
"""
import argparse, hashlib, pathlib, shutil, struct, subprocess, zlib

HERE = pathlib.Path(__file__).resolve().parent
MINI_SHA256 = 'bb795828c84e831d1871f48c64d06bb084d2a21fb3be4a3795a4d61cd20ef21f'  # 10-5-2026 release
DONOR_SHA256 = '862d3743cd2629d0adc7b0d303a5bb4bd966df95bbca977db640ff983adf056f'
BLOCK_VA = 0xd68f00
HOOK_VA = 0x46f7aa
REGISTER_GP107 = 0xd07c40
# GeForce 382.33 descriptor VAs ({u32 length, u32 va, u32 compressed}).
DONOR = {
    'gr-bundle.bin': (0xa9fdec, 87603),        # GP108 GR bundle (family 0x3D, slot 29 +0x420)
    'fecs-signature.bin': (0xb2daf0, 192),     # GP108 FECS signature (slot 18 +0x24)
    'gpccs-signature.bin': (0xb9c5f8, 192),    # GP108 GPCCS signature (slot 25 +0x20)
    # Secure-boot (ACR) set from the GP102/GP106/GP107/GP108 slot-0 table 0xBCE090
    # (+0x64/+0x6C/+0x74/+0x7C/+0x84/+0x8C), replacing upstream's 376.84 ACR 0-5.
    'acr0.bin': (0xb16cec, 16640),
    'acr1.bin': (0xb187c8, 36),
    'acr2.bin': (0xb189a4, 16),
    'acr3.bin': (0xb18a54, 16),
    'acr4.bin': (0xb18af8, 4),
    'acr5.bin': (0xb18b4c, 4),
}
# XP ACR 0-5 descriptors ({u32 length, u32 va, u32 compressed}); their pointer
# fields already have base relocations.
XP_ACR_DESCRIPTORS = [0xc33f90 + 0x18 * i for i in range(6)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def require(c, msg):
    if not c:
        raise SystemExit('error: ' + msg)


def pe(d):
    p = struct.unpack_from('<I', d, 60)[0]
    op = p + 24
    base = struct.unpack_from('<I', d, op + 28)[0]
    st = op + struct.unpack_from('<H', d, p + 20)[0]
    secs = []
    for i in range(struct.unpack_from('<H', d, p + 6)[0]):
        vs, va, rs, raw = struct.unpack_from('<IIII', d, st + i * 40 + 8)
        secs.append((st + i * 40, va, vs, raw, rs))
    return p, op, base, secs


def va_off(d, va, n=1):
    _, _, base, secs = pe(d)
    rva = va - base
    for _, sva, vs, raw, rs in secs:
        if sva <= rva and rva + n <= sva + max(vs, rs):
            return raw + rva - sva
    raise SystemExit('error: unmapped VA %#x' % va)


def descriptor(d, va, size):
    length, ptr, comp = struct.unpack_from('<III', d, va_off(d, va, 12))
    require(length == size and comp in (0, 1), 'unexpected donor descriptor at %#x' % va)
    p = va_off(d, ptr)
    if comp:
        dec = zlib.decompressobj(-15)
        out = dec.decompress(d[p:p + length + 65536], length + 1)
        require(dec.eof and len(out) == length, 'bad donor stream at %#x' % va)
        return out
    return d[p:p + length]


def checksum(d, off):
    b = bytearray(d)
    b[off:off + 4] = bytes(4)
    if len(b) & 1:
        b.append(0)
    s = 0
    for (w,) in struct.iter_unpack('<H', b):
        s += w
        s = (s & 0xffff) + (s >> 16)
    return (s & 0xffff) + len(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--mini', required=True)
    ap.add_argument('--donor', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    mini = bytearray(pathlib.Path(a.mini).read_bytes())
    donor = pathlib.Path(a.donor).read_bytes()
    require(sha(mini) == MINI_SHA256, 'input is not the 10-5-2026 nv4_mini.sys')
    require(sha(donor) == DONOR_SHA256, 'donor is not GeForce 382.33 x86 nvlddmkm.sys')
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=False)

    p, op, base, secs = pe(mini)
    hook = va_off(mini, HOOK_VA, 5)
    require(mini[hook] == 0xe8 and HOOK_VA + 5 + struct.unpack_from('<i', mini, hook + 1)[0] == REGISTER_GP107,
            'input miniport has no GP107 hook at 0x46F7AA')
    hdr, rva, vs, raw, rs = secs[-1]
    require(mini[hdr:hdr + 6] == b'.reloc' and raw + rs == len(mini) and vs == rs, 'unexpected final section layout')
    require(base + rva + vs == BLOCK_VA, 'block VA %#x does not follow the image' % (base + rva + vs))

    for name, (va, size) in DONOR.items():
        blob = descriptor(donor, va, size)
        (out / name).write_bytes(blob)
        print(f'{name}: {len(blob)} bytes sha256 {sha(blob)}')

    for cmd in (['as', '--32', str(HERE / 'gp108.s'), '-o', 'gp108.o'],
                ['ld', '-m', 'elf_i386', '-T', str(HERE / 'gp108.ld'), 'gp108.o', '-o', 'gp108.elf'],
                ['objcopy', '-O', 'binary', '-j', '.text', 'gp108.elf', 'gp108.bin']):
        subprocess.run(cmd, cwd=out, check=True)
    require('There are no relocations' in subprocess.check_output(['readelf', '-r', 'gp108.elf'], cwd=out, text=True),
            'unexpected relocations in gp108.elf')
    syms = {l.split()[2]: int(l.split()[0], 16) for l in
            subprocess.check_output(['nm', 'gp108.elf'], cwd=out, text=True).splitlines() if len(l.split()) == 3}
    require(syms['register_gp108'] == BLOCK_VA, 'register_gp108 is not at the block start')
    block = (out / 'gp108.bin').read_bytes()
    block += bytes(-len(block) % 0x20)

    for i, va in enumerate(XP_ACR_DESCRIPTORS):
        off = va_off(mini, va, 12)
        length, ptr, comp = struct.unpack_from('<III', mini, off)
        require(comp == 0 and ptr < BLOCK_VA, 'unexpected XP ACR descriptor %d' % i)
        blob = (out / f'acr{i}.bin').read_bytes()
        struct.pack_into('<II', mini, off, len(blob), syms[f'acr{i}_payload'])
        print(f'ACR {i}: XP descriptor {va:#x} {length}->{len(blob)} bytes, {ptr:#x}->{syms[f"acr{i}_payload"]:#x}')

    # Redirect the hook, then grow the final section and the image.
    struct.pack_into('<i', mini, hook + 1, BLOCK_VA - (HOOK_VA + 5))
    mini += block
    struct.pack_into('<II', mini, hdr + 8, vs + len(block), rva)
    struct.pack_into('<I', mini, hdr + 16, rs + len(block))
    struct.pack_into('<I', mini, op + 56, rva + vs + len(block))
    struct.pack_into('<I', mini, op + 64, checksum(mini, op + 64))
    (out / 'nv4_mini.sys').write_bytes(mini)
    print(f'block {len(block)} bytes at {BLOCK_VA:#x}; nv4_mini.sys sha256 {sha(mini)}')


if __name__ == '__main__':
    main()
