from typing import Any
from zendriver.core._contradict import ContraDict, _check_key
class Reordered(ContraDict):
    def __getattribute__(self, attribute: str) -> Any:
        if not _check_key(attribute, self, True, silent=True):
            return getattr(super(), attribute)
        if attribute in self:
            return self[attribute]
        return object.__getattribute__(self, attribute)
cd = Reordered({"class": "c", "data-id": "d", "Items": "I", "clear": "all"}, silent=True)
for k in ("class", "data-id", "Items"):
    try: print(k, "->", getattr(cd, k))
    except Exception as e: print(k, "->", type(e).__name__, e)
