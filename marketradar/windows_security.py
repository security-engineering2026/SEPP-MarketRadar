from __future__ import annotations
"""Windows-native secret protection helpers.

Secrets are protected with Windows DPAPI when running on Windows. The module
never silently falls back to plaintext storage.
"""
import base64
import ctypes
import os
from ctypes import wintypes

class DPAPIUnavailable(RuntimeError):
    pass

if os.name == 'nt':
    class DATA_BLOB(ctypes.Structure):
        _fields_=[('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]
    _crypt32=ctypes.windll.crypt32
    _kernel32=ctypes.windll.kernel32

    def _blob(data: bytes):
        buf=ctypes.create_string_buffer(data)
        return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

    def protect(data: bytes, entropy: bytes|None=None) -> str:
        if not isinstance(data,(bytes,bytearray)): raise TypeError('data must be bytes')
        inp, _ = _blob(bytes(data)); ent=None; ent_blob=None
        if entropy:
            ent_blob, _ = _blob(bytes(entropy)); ent=ctypes.byref(ent_blob)
        out=DATA_BLOB()
        if not _crypt32.CryptProtectData(ctypes.byref(inp), 'SEPP-MarketRadar', ent, None, None, 0, ctypes.byref(out)):
            raise OSError(ctypes.get_last_error(), 'CryptProtectData failed')
        try:
            raw=ctypes.string_at(out.pbData, out.cbData)
            return base64.b64encode(raw).decode('ascii')
        finally:
            _kernel32.LocalFree(out.pbData)

    def unprotect(token: str, entropy: bytes|None=None) -> bytes:
        raw=base64.b64decode(token.encode('ascii'), validate=True)
        inp, _ = _blob(raw); ent=None; ent_blob=None
        if entropy:
            ent_blob, _ = _blob(bytes(entropy)); ent=ctypes.byref(ent_blob)
        out=DATA_BLOB()
        if not _crypt32.CryptUnprotectData(ctypes.byref(inp), None, ent, None, None, 0, ctypes.byref(out)):
            raise OSError(ctypes.get_last_error(), 'CryptUnprotectData failed')
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            _kernel32.LocalFree(out.pbData)
else:
    def protect(data: bytes, entropy: bytes|None=None) -> str:
        raise DPAPIUnavailable('Windows DPAPI is available only on Windows')
    def unprotect(token: str, entropy: bytes|None=None) -> bytes:
        raise DPAPIUnavailable('Windows DPAPI is available only on Windows')
