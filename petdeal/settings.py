import os
import re
import yaml

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand(v):
    if isinstance(v, str):
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), v)
    if isinstance(v, dict):
        return {k: _expand(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_expand(x) for x in v]
    return v


def load(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return _expand(yaml.safe_load(f))
