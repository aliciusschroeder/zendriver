import types

def coro_chain(task):
    """walk cr_await of a task's coroutine and return [(func, file, line)]"""
    out = []
    c = task.get_coro()
    while c is not None:
        f = getattr(c, "cr_frame", None) or getattr(c, "gi_frame", None) or getattr(c, "ag_frame", None)
        if f is not None:
            out.append(f"{f.f_code.co_qualname} ({f.f_code.co_filename.split('/zendriver/')[-1]}:{f.f_lineno})")
        c = getattr(c, "cr_await", None) or getattr(c, "gi_yieldfrom", None)
        if c is not None and not isinstance(c, (types.CoroutineType, types.GeneratorType)):
            out.append(f"awaiting {type(c).__name__}: {str(c).split(chr(10))[1].strip() if chr(10) in str(c) else c}")
            break
    return out
