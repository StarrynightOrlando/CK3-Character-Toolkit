from pathlib import Path
import zipfile
from . import core
from .product import RUNTIME_KEY,TITLE
from .runtime import build_runtime
def runtime_zip():
 out=core.ROOT/'releases';mod=out/RUNTIME_KEY;build_runtime(core.settings()['game'],mod)
 descriptor=(mod/'descriptor.mod').read_text(encoding='utf-8')+'path="mod/'+RUNTIME_KEY+'"\n'
 (out/(RUNTIME_KEY+'.mod')).write_text(descriptor,encoding='utf-8')
 archive=out/(RUNTIME_KEY+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for file in mod.rglob('*'):
   if file.is_file():z.write(file,RUNTIME_KEY+'/'+file.relative_to(mod).as_posix())
  z.write(out/(RUNTIME_KEY+'.mod'),RUNTIME_KEY+'.mod')
  z.write(core.ROOT/'docs/玩家安装说明.txt','玩家安装说明.txt')
 return archive
