import hashlib
from pathlib import Path
from django.core.cache import cache
from casino.redis.client import redis_client

if cache is None:
    from django.core.cache import caches
    cache = caches['default']


class LuaScript:
    """
    Загрузчик Lua-скриптов с:
    - поиском по любому указанному пути
    - защитой от изменения на лету
    - кэшированием SHA
    """
    _scripts = {}

    @classmethod
    def register(cls, name: str, path: str | Path | None = None):
        """
        name: имя скрипта без .lua
        path: каталог, где искать скрипт (можно None, тогда поиск в cwd)
        """
        key = f"{str(path) if path else 'default'}:{name}"
        if key in cls._scripts:
            return cls._scripts[key]

        base_path = Path(path) if path else Path.cwd()
        candidates = list(base_path.rglob(f"{name}.lua"))
        if not candidates:
            raise FileNotFoundError(f"Lua script not found: {name}.lua (searched in {base_path})")

        script_path = candidates[0]
        source = script_path.read_text(encoding="utf-8")

        current_sha = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
        cache_key = f"lua_script_sha:{key}"

        stored_sha = cache.get(cache_key)
        if stored_sha and stored_sha != current_sha:
            raise RuntimeError(
                f"CRITICAL: Lua script changed without deploy!\n"
                f"Script: {name}\n"
                f"Path: {script_path}\n"
                f"Expected SHA: {stored_sha}\n"
                f"Current SHA:  {current_sha}\n"
                f"→ DEPLOY REQUIRED!"
            )

        cache.set(cache_key, current_sha, timeout=None)
        script = redis_client.register_script(source)
        cls._scripts[key] = script
        print(f"Lua script loaded: {name} → {script_path} (sha: {current_sha})")
        return script


def preload_all_scripts(path: str | Path | None = None):
    """Автозагрузка всех скриптов из указанного пути или cwd"""
    base_path = Path(path) if path else Path.cwd()
    if not base_path.exists():
        return

    for lua_file in base_path.rglob("*.lua"):
        rel_path = lua_file.relative_to(base_path).with_suffix("")
        name = str(rel_path).replace("/", "_").replace("\\", "_")
        try:
            LuaScript.register(name, path=path)
        except Exception as e:
            print(f"Failed to preload {lua_file}: {e}")
