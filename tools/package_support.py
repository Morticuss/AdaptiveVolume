"""Shared, offline release documentation and runtime cleanup."""
from pathlib import Path
import shutil


def prepare_distribution(root, distribution):
    distribution = distribution.resolve()
    qt = distribution / '_internal' / 'PySide6'
    keep_libraries = {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll',
                      'Qt6Network.dll', 'Qt6Svg.dll', 'Qt6OpenGL.dll'}
    keep_plugins = {'platforms/qwindows.dll', 'styles/qmodernwindowsstyle.dll',
                    'styles/qwindowsvistastyle.dll', 'imageformats/qico.dll',
                    'imageformats/qjpeg.dll', 'imageformats/qgif.dll',
                    'imageformats/qsvg.dll', 'tls/qopensslbackend.dll',
                    'tls/qschannelbackend.dll', 'tls/qcertonlybackend.dll',
                    'networkinformation/qnetworklistmanager.dll'}
    removable = [p for p in qt.glob('Qt6*.dll') if p.name not in keep_libraries]
    plugins = qt / 'plugins'
    removable += [p for p in plugins.rglob('*') if p.is_file() and
                  p.relative_to(plugins).as_posix() not in keep_plugins]
    portaudio = distribution / '_internal' / '_sounddevice_data' / 'portaudio-binaries'
    removable += [p for p in portaudio.glob('*.dll') if p.name != 'libportaudio64bit.dll']
    for path in removable:
        if not path.resolve().is_relative_to(distribution):
            raise ValueError('Runtime cleanup path leaves the distribution')
        path.unlink()
    obsolete = [distribution / 'VALIDATION.md', distribution / 'docs' / 'RELEASE_1.0.0.md']
    source_licenses = {p.relative_to(root / 'licenses') for p in (root / 'licenses').rglob('*') if p.is_file()}
    obsolete += [p for p in (distribution / 'licenses').rglob('*') if p.is_file()
                 and p.relative_to(distribution / 'licenses') not in source_licenses]
    for path in obsolete:
        if path.exists():
            if not path.resolve().is_relative_to(distribution):
                raise ValueError('Documentation cleanup path leaves the distribution')
            path.unlink()
    for name in ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                 'CHANGELOG.md', 'VERSION'):
        shutil.copyfile(root / name, distribution / name)
    for name in ('docs', 'licenses'):
        shutil.copytree(root / name, distribution / name, dirs_exist_ok=True)
    print(f'Release documentation copied; removed {len(removable)} unused Qt runtime files')
