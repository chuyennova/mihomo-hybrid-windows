#!/usr/bin/env python3
from __future__ import annotations
import pathlib, struct, sys
for name in sys.argv[1:]:
    p=pathlib.Path(name)
    data=p.read_bytes()
    if len(data)<0x40 or data[:2]!=b'MZ': raise SystemExit(f"E42_PE_INVALID {p}: missing MZ")
    off=struct.unpack_from('<I',data,0x3c)[0]
    if off+6>len(data) or data[off:off+4]!=b'PE\0\0': raise SystemExit(f"E42_PE_INVALID {p}: missing PE")
    machine=struct.unpack_from('<H',data,off+4)[0]
    if machine!=0x8664: raise SystemExit(f"E42_PE_ARCH {p}: machine=0x{machine:04x}, expected amd64")
    print(f"PE_AMD64_OK {p} size={len(data)}")
