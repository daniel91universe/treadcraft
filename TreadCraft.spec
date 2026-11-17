# Windows onedir package; includes zeroconf's dynamic/Cython modules and license metadata.
from PyInstaller.utils.hooks import collect_all

zc_data, zc_binaries, zc_imports = collect_all('zeroconf')
ia_data, ia_binaries, ia_imports = collect_all('ifaddr')
a = Analysis(['app.py'], pathex=[],
             binaries=zc_binaries + ia_binaries,
             datas=[('assets/brand', 'assets/brand')] + zc_data + ia_data,
             hiddenimports=zc_imports + ia_imports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='TreadCraft',
          debug=False, strip=False, upx=False, console=False,
          icon='assets/brand/TreadCraft.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='TreadCraft')
