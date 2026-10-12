from pathlib import Path
import pefile
import os
import sys

root = Path(__file__).resolve().parents[1]
bundle = root / ('dist/release/AdaptiveVolume/_internal' if '--release' in sys.argv else 'dist/AdaptiveVolume/_internal')
files = list(bundle.rglob('*.dll')) + list(bundle.rglob('*.pyd'))
lookup = {p.name.lower(): p for p in files}
system = Path(os.environ['WINDIR']) / 'System32'
cache = {}

def exports(path):
    if path in cache:
        return cache[path]
    pe = pefile.PE(str(path), fast_load=True, max_symbol_exports=100000)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    names = {s.name for s in pe.DIRECTORY_ENTRY_EXPORT.symbols} if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT') else set()
    cache[path] = names
    pe.close()
    return names

for path in files:
    if not path.name.lower().startswith(('qt', 'pyside', 'shiboken')):
        continue
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        library = entry.dll.decode().lower()
        target = lookup.get(library, system / library)
        if not target.exists():
            continue
        available = exports(target)
        missing = [s.name.decode(errors='replace') for s in entry.imports if s.name and s.name not in available]
        if missing:
            print(f'{path.name} -> {library}: {missing[:12]}')
    pe.close()
