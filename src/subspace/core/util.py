# TODO: integrate this -- no need for its own source file, poor org

from time import time

def now():
    """ TODO: on win32, use ctypes.dll.kernel32.GetTickCount() / 10 """
    return int(time()*100 % 0xFFFFFFFF)