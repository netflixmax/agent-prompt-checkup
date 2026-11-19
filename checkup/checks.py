"""Rule-based checks. Each check returns (passed: bool, detail: str)."""
import re

def _norm(s):
    return s.lower()

def must_include_any(reply, values):
    hit = [v for v in values if _norm(v) in _norm(reply)]
    return bool(hit), f"found {hit}" if hit else f"none of {values}"

def must_include_all(reply, values):
    miss = [v for v in values if _norm(v) not in _norm(reply)]
    return not miss, "all present" if not miss else f"missing {miss}"

def must_not_include(reply, values):
    hit = [v for v in values if _norm(v) in _norm(reply)]
    return not hit, "clean" if not hit else f"contains {hit}"

def must_match(reply, pattern):
    ok = re.search(pattern, reply, re.I | re.S) is not None
    return ok, "matched" if ok else f"no match for /{pattern}/"

def must_not_match(reply, pattern):
    m = re.search(pattern, reply, re.I | re.S)
    return m is None, "clean" if m is None else f"matched '{m.group(0)}'"

def max_chars(reply, n):
    return len(reply) <= n, f"{len(reply)} chars (limit {n})"

RULES = {
    "must_include_any": must_include_any,
    "must_include_all": must_include_all,
    "must_not_include": must_not_include,
    "must_match": must_match,
    "must_not_match": must_not_match,
    "max_chars": max_chars,
}
