from __future__ import annotations
import json
from pathlib import Path
from typing import Any

LEVEL_NAMES = {1:'foundation',2:'junior',3:'intermediate',4:'advanced',5:'expert'}
TRACKS = {'software_engineering','red_team','blue_team','data_automation','general'}


def normalize_level(value: Any) -> int:
    if isinstance(value, bool): return 3
    try: return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 3


def load_profile(connection, settings=None, root=None) -> dict:
    row = connection.execute('SELECT payload FROM user_profile WHERE id=1').fetchone()
    if row:
        try:
            data = json.loads(row['payload'])
            if isinstance(data, dict): return data
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    settings = settings or {}
    path = settings.get('default_profile')
    if path:
        if root:
            p = Path(root) / path
        else:
            try:
                from .paths import app_root
                p = app_root() / path
            except Exception:
                p = Path(path)

        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                if isinstance(data, dict): return data
            except (OSError, ValueError, json.JSONDecodeError):
                pass
    return {'learning': {'level': 3, 'tracks': ['software_engineering'], 'stretch': True}, 'skills': []}


def save_profile(connection, profile):
    if not isinstance(profile, dict): raise ValueError('PROFILE_INVALID')
    now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    connection.execute('INSERT OR REPLACE INTO user_profile(id,payload,updated_at) VALUES(1,?,?)', (json.dumps(profile, ensure_ascii=False), now))
    connection.commit()


def learning_settings(profile: dict) -> dict:
    p = profile or {}
    learning = p.get('learning') if isinstance(p.get('learning'), dict) else {}
    level = normalize_level(learning.get('level', p.get('level', 3)))
    tracks = learning.get('tracks') or ['software_engineering']
    tracks = [str(x) for x in tracks if str(x) in TRACKS] or ['software_engineering']
    return {
        'level': level,
        'level_name': LEVEL_NAMES[level],
        'tracks': tracks,
        'stretch': bool(learning.get('stretch', True)),
        'max_complexity': max(1, min(5, normalize_level(learning.get('max_complexity', level + (1 if learning.get('stretch', True) else 0)))))
    }
