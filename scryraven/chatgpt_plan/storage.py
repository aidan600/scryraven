"""Separate Windows-user DPAPI vault; atomic rotation and cross-process locking.

No Codex credential paths, repository secrets or environment tokens are read.
The only decrypted data is the existing operator-created plan registration.
"""

from __future__ import annotations

import ctypes
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .http import PlanError

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def default_directory():
    root = Path(os.environ.get("LOCALAPPDATA", ""))
    if not root.is_absolute():
        root = Path.home() / "AppData" / "Local"
    return root / "ScryRaven" / "continuing-worker-chatgpt-plan"


class WindowsProtection:
    """DPAPI CurrentUser, with UI forbidden; fail closed outside Windows."""

    def __init__(self):
        if os.name != "nt":
            raise PlanError("model_configuration_missing", reason="windows_protection_required")

    def _crypt(self, data, encrypt):
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

        crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        source, target = Blob(len(data), buffer), Blob()
        function = crypt.CryptProtectData if encrypt else crypt.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise PlanError("model_configuration_missing", reason="credential_protection_failed")
        try:
            return ctypes.string_at(target.data, target.size)
        finally:
            kernel.LocalFree(target.data)

    def seal(self, data):
        return self._crypt(data, True)

    def open(self, data):
        return self._crypt(data, False)

    def restrict(self, path):
        # Protected DACL: only the file/directory owner has full access. DPAPI
        # additionally binds the encrypted contents to the current Windows user.
        from ctypes import wintypes

        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        descriptor = ctypes.c_void_p()
        convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
        convert.restype = wintypes.BOOL
        apply = advapi.SetFileSecurityW
        apply.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
        apply.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        if not convert("D:P(A;OICI;FA;;;OW)", 1, ctypes.byref(descriptor), None):
            raise PlanError("model_configuration_missing", reason="credential_permissions_failed")
        try:
            if not apply(str(path), 0x80000004, descriptor):
                raise PlanError("model_configuration_missing", reason="credential_permissions_failed")
        finally:
            kernel.LocalFree(descriptor)


class Vault:
    def __init__(self, directory=None, *, protection=None):
        self.directory = Path(directory) if directory is not None else default_directory()
        self.path = self.directory / "plan-v1.bin"
        self.protection = protection if protection is not None else WindowsProtection()
        with _LOCKS_GUARD:
            self._lock = _LOCKS.setdefault(str(self.path.resolve()).casefold(), threading.RLock())

    @contextmanager
    def locked(self, *, timeout=30):
        """Hold across read, refresh, validation and atomic replacement."""
        import msvcrt

        deadline = time.monotonic() + timeout
        if not self._lock.acquire(timeout=max(0, timeout)):
            raise PlanError("model_request_timed_out", reason="credential_lock_timeout")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.protection.restrict(self.directory)
            with (self.directory / "vault.lock").open("a+b") as handle:
                self.protection.restrict(self.directory / "vault.lock")
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise PlanError("model_request_timed_out", reason="credential_lock_timeout") from None
                        time.sleep(0.05)
                try:
                    yield self
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            raise PlanError("model_configuration_missing", reason="credential_storage_failed") from None
        finally:
            self._lock.release()

    def read(self):
        """Caller holds locked(); a corrupt vault never becomes a fresh account."""
        if not self.path.exists():
            return {"version": 1, "host_id": "urn:uuid:" + str(uuid.uuid4()), "accounts": {}}
        try:
            data = json.loads(self.protection.open(self.path.read_bytes()))
            if data["version"] != 1 or not isinstance(data["accounts"], dict):
                raise ValueError
            uuid.UUID(data["host_id"].removeprefix("urn:uuid:"), version=4)
            if not data["host_id"].startswith("urn:uuid:"):
                raise ValueError
            return data
        except (OSError, ValueError, KeyError, TypeError):
            raise PlanError("model_configuration_missing", reason="credential_storage_invalid") from None

    def write(self, data):
        """No plaintext temp file; failed replacement leaves the old vault intact."""
        encrypted = self.protection.seal(json.dumps(data, allow_nan=False).encode("utf-8"))
        descriptor, name = tempfile.mkstemp(prefix="plan-", suffix=".bin", dir=self.directory)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                self.protection.restrict(name)
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        except OSError:
            raise PlanError("model_configuration_missing", reason="credential_storage_failed") from None
        finally:
            if os.path.exists(name):
                os.unlink(name)
