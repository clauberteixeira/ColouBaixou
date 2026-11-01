"""Roda testes com janelas numa área de trabalho oculta do Windows.

O programa abre de verdade, mas nada aparece nos monitores nem rouba o foco de quem está usando o PC.
Uso: python scripts\\hidden_desktop.py [--timeout 90] -- comando argumentos...

Se o comando abrir outro programa (como o .exe gerado), ele mesmo precisa fechá-lo, inclusive quando der
erro: o que sobrar continua rodando escondido. Para fotografar, use capture() abaixo: ela pega só a janela
pedida, e não o que estiver na tela de quem está trabalhando.
"""

import argparse
import ctypes
import msvcrt
import os
import subprocess
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

GENERIC_ALL = 0x10000000
STARTF_USESTDHANDLES = 0x100
CREATE_NO_WINDOW = 0x08000000
WAIT_TIMEOUT = 0x102
PW_RENDERFULLCONTENT = 2
DESKTOP_NAME = "ColouBaixouTestes"


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", wintypes.LPVOID),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


def run_hidden(args: list[str], timeout: float) -> tuple[int, str]:
    """Roda o comando na área oculta e devolve (código de saída, saída). Código 124 = estourou o tempo."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.DWORD,
                                      wintypes.DWORD, wintypes.LPVOID]
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
                                        wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
                                        ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    desktop = user32.CreateDesktopW(DESKTOP_NAME, None, None, 0, GENERIC_ALL, None)
    if not desktop:  # sem a área oculta, a janela abriria na tela de quem está trabalhando
        raise ctypes.WinError(ctypes.get_last_error())
    os.environ["PYTHONIOENCODING"] = "utf-8"
    with tempfile.TemporaryFile() as output:
        handle = msvcrt.get_osfhandle(output.fileno())
        os.set_handle_inheritable(handle, True)
        startup = STARTUPINFOW(cb=ctypes.sizeof(STARTUPINFOW), lpDesktop=DESKTOP_NAME, dwFlags=STARTF_USESTDHANDLES,
                               hStdOutput=handle, hStdError=handle)
        process = PROCESS_INFORMATION()
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        try:
            if not kernel32.CreateProcessW(None, command, None, None, True, CREATE_NO_WINDOW, None, None,
                                           ctypes.byref(startup), ctypes.byref(process)):
                raise ctypes.WinError(ctypes.get_last_error())
            if kernel32.WaitForSingleObject(process.hProcess, int(timeout * 1000)) == WAIT_TIMEOUT:
                kernel32.TerminateProcess(process.hProcess, 124)
                kernel32.WaitForSingleObject(process.hProcess, 5000)
            code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(code))
            kernel32.CloseHandle(process.hProcess)
            kernel32.CloseHandle(process.hThread)
        finally:
            user32.CloseDesktop(desktop)
        output.seek(0)
        return code.value, output.read().decode("utf-8", "replace")


def capture(hwnd: int, path: Path) -> None:
    """Salva a imagem de uma janela. Funciona fora da tela e nunca pega o que há por cima dela."""
    from PIL import Image

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    for fn in (user32.GetWindowDC, gdi32.CreateCompatibleDC, gdi32.CreateCompatibleBitmap):
        fn.restype = wintypes.HANDLE
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HANDLE]
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_int]
    gdi32.SelectObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.GetBitmapBits.argtypes = [wintypes.HANDLE, ctypes.c_long, ctypes.c_void_p]
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteDC.argtypes = [wintypes.HANDLE]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.UINT]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HANDLE]

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    window_dc = user32.GetWindowDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    gdi32.SelectObject(memory_dc, bitmap)
    user32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT)
    pixels = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetBitmapBits(bitmap, len(pixels), pixels)
    Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1).save(path)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory_dc)
    user32.ReleaseDC(hwnd, window_dc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("command", nargs="+")
    options = parser.parse_args()
    code, output = run_hidden(options.command, options.timeout)
    sys.stdout.reconfigure(encoding="utf-8")
    print(output, end="")
    if code == 124:
        print(f"\nestourou o tempo de {options.timeout:.0f} s")
    return code


if __name__ == "__main__":
    sys.exit(main())
