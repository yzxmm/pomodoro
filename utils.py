import os
import sys

def base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resolve_path(subfolder, *parts):
    # 1. Check external (user override)
    external = os.path.join(base_dir(), subfolder, *parts)
    if os.path.exists(external):
        return external
    
    # 2. Check bundled (PyInstaller _MEIPASS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, subfolder, *parts)
        if os.path.exists(bundled):
            return bundled
            
    # 3. Return external as default
    return external

def asset_path(*parts):
    return resolve_path("assets", *parts)

def sound_path(*parts):
    return resolve_path("sounds", *parts)

def resolve_asset(name):
    local = asset_path(name)
    if os.path.exists(local):
        return local
    parent = os.path.join(os.path.dirname(base_dir()), "assets", name)
    return parent if os.path.exists(parent) else local
