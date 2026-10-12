from pathlib import Path
import zipfile
import sys
import hashlib
from package_support import prepare_distribution
root = Path(__file__).resolve().parents[1]
release = '--release' in sys.argv
distribution = root / 'dist' / 'release' / 'AdaptiveVolume' if release else root / 'dist' / 'AdaptiveVolume'
prepare_distribution(root, distribution)
version = root.joinpath('VERSION').read_text().strip()
filename = f'AdaptiveVolume-{version}-windows-x64.zip' if release else 'AdaptiveVolume.zip'
output = root / 'dist' / filename
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in distribution.rglob('*'):
        relative = path.relative_to(distribution)
        if path.is_file() and relative.parts[0] != 'data':
            archive.write(path, 'AdaptiveVolume/' + relative.as_posix())
print('Packaged portable folder; local test data and recovery state excluded')
with output.open('rb') as packaged:
    digest = hashlib.file_digest(packaged, 'sha256').hexdigest()
root.joinpath('dist/SHA256SUMS.txt').write_text(f'{digest}  {filename}\n', encoding='utf-8')
print(output)
