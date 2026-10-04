from pathlib import Path
import json,re
TOOL_VERSION='0.5.0'
def game_version(game):
 path=Path(game).parent/'launcher/launcher-settings.json'
 if not path.is_file():return None
 value=json.loads(path.read_text(encoding='utf-8-sig')).get('rawVersion','')
 return value if re.fullmatch(r'\d+(?:\.\d+){1,3}',value) else None
def supported_version(game):
 version=game_version(game)
 return '.'.join(version.split('.')[:2])+'.*' if version else '*'
