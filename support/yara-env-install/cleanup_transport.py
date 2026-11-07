from pathlib import Path
import json,shutil
r=Path('/home/ot/Students/hs/yara-env').resolve()
assert str(r)=='/home/ot/Students/hs/yara-env'
assert json.loads((r/'docker/IMAGE_RECEIPT.json').read_text())['rootfs_and_config_equal']
targets=[r/'docker/verified-ros-image.tar']+list((r/'docker/server_layers').glob('*.tar'))+list((r/'docker/server_layers').glob('*_chunks'))
targets += [r/'docker/wheels/torch_chunks']
for p in targets:
    assert not p.is_symlink() and p.resolve().is_relative_to(r)
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): p.unlink()
    print('removed transport temporary',p)
