"""
Compiles LegacyRoblox.css.css (the VibeX19 UI design reference) into a plain
CSS file for the website (app/static/css/legacy.css).

The source userstyle is written for the Stylus extension and uses
Stylus-specific conditional guards:

    & when (@Var = value) { ... }              (nested form)
    selector when (@Var = value) { ... }       (trailing form)
    ... not (@Var = value) ... or/and ...      (boolean combinations)

lesscpy cannot parse these, so this tool evaluates every guard against the
variable defaults declared in the userstyle header (@var lines), strips the
true guards and drops the false blocks, then lets lesscpy finish the plain
Less/CSS compilation.

Braces and parentheses inside CSS strings (data URIs) and comments are
ignored during guard/brace resolution, so string content can never corrupt
the structural parsing.

Usage (from the syntaxwebsite directory):
    python tools/compile_legacy_css.py
"""

import bisect
import os
import re

# tools/ -> syntaxwebsite -> syntaxsource -> project root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SOURCE_CSS = os.path.join(ROOT, "LegacyRoblox.css.css")
OUT_CSS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "css", "legacy.css"
)
TMP_LESS = OUT_CSS + ".less.tmp"

# The design reference's default selections, matching the * markers in the
# userstyle header. Keep in sync with LegacyRoblox.css.css.
DEFAULTS = {
    "BadgeStyle": "201902",
    "BoxShadows": "0",
    "SiteCurrency": "Robux",
    "forcesignuplighttheme": "0",
    "fiveColumn": "1",
    "CardStyle": "2019M",
    "LogoStyle": "201701",
    "LegacyNextStyleGuideButtons": "0",
    "LegacyFooterText": "0",
    "SponsorSizing": "1",
    "PlayButtonStyle": "2019M",
    "RestoreSidebarPadding": "0",
    "RemoveUpdates": "1",
    "StyleGuideStyle": "2018",
    "SignUpStyle": "2018",
    "SourceSansPro": "0",
    "TransitionalAnimations": "1",
    "RedLogoStyle": "0",
}

# Guard grammar: one or more atoms joined by and/or; every atom may be negated.
#   (...)   not (...)   (...) and not (...)   not (...) or (...) and (...)
COND_ATOM = r"(?:not\s*)?\([^)]*\)"
CONDITION = COND_ATOM + r"(?:\s*(?:and|or)\s+" + COND_ATOM + r")*"

GUARD_RE = re.compile(r"&\s*when\s+(?P<cond>" + CONDITION + r")\s*\{")

# The userstyle contains several selectors written with bare element idents
# missing their leading `.` (e.g. `social-link-icon-list .Discord`,
# `div.profilecontainer ng.scope`). lesscpy's parser rejects them.
# Dot-prefixing is a safe parser workaround: these are extension-specific
# class selectors that never match VibeX19's DOM either way.
#
# The lookbehind avoids touching tokens that are already part of a class
# chain (.foo-bar), an id (#foo), a compound selector (foo-bar), or an
# attribute value (type="checkbox").
BARE_IDENT_REGEXES = [
    (re.compile(r"(?<![\w.\-#\]\"'])social-link-icon-list"), ".social-link-icon-list"),
    (re.compile(r"(?<![\w.\-#\]\"'])group-landing-row"), ".group-landing-row"),
    (re.compile(r"(?<![\w.\-#\]\"'])thumbnail-2d"), ".thumbnail-2d"),
    (re.compile(r"(?<![\w.\-#\]\"'])group\[minimizable\]"), ".group[minimizable]"),
    (re.compile(r"(?<![\w.\-#\]\"'])group:"), ".group:"),
    (re.compile(r"(?<![\w.\-#\]\"'])checkbox:"), ".checkbox:"),
    (re.compile(r"(?<![\w.\-#\]\"'])ng\.scope"), ".ng.scope"),
]


def parse_header_defaults(text: str) -> dict:
    """Parse @var defaults from the ==UserStyle== header."""
    defaults = dict(DEFAULTS)
    header = text.split("==/UserStyle==")[0]
    for m in re.finditer(
        r"@var\s+(select|checkbox)\s+(\w+)\s+\"[^\"]*\"\s*\[([^\]]*)\]", header
    ):
        kind, name, options = m.group(1), m.group(2), m.group(3)
        if kind == "checkbox":
            defaults[name] = options.split()[-1] if options.split() else "0"
            continue
        quoted = re.findall(r'"([^"]*)"', options)
        chosen = None
        for opt in quoted:
            if opt.endswith("*"):
                chosen = opt.rstrip("*")
                break
        if chosen is None and quoted:
            chosen = quoted[0]
        if chosen is not None:
            defaults[name] = chosen
    return defaults


def extract_main_block(text: str) -> str:
    """Extract the inner rules of the main @-moz-document url-prefix block."""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if 'url-prefix("https://www.roblox.com")' in line:
            start = i
            break
    if start is None:
        raise SystemExit("main @-moz-document block not found")
    depth = 0
    seen_open = False
    for j in range(start, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            seen_open = True
        if seen_open and depth == 0:
            return "\n".join(lines[start + 1 : j])
    raise SystemExit("main @-moz-document block not terminated")


# ── string/comment span machinery ──────────────────────────────


def build_skip_spans(text: str):
    """Return sorted list of (start, end, kind) spans covering quoted strings
    and the userstyle's `/*/ ... /*/` comments. Braces/parens/words inside
    these spans are not structural."""
    spans = []
    i = 0
    n = len(text)
    while i < n:
        best = None  # (pos, kind)
        for d, kind in (('"', "string"), ("'", "string"), ("/*/", "comment")):
            j = text.find(d, i)
            if j != -1 and (best is None or j < best[0]):
                best = (j, d, kind)
        if best is None:
            break
        j, d, kind = best
        if kind == "comment":
            end = text.find("/*/", j + 3)
            end = n if end == -1 else end + 3
        else:
            k = j + 1
            while True:
                k = text.find(d, k)
                if k == -1:
                    k = n - 1
                    break
                bs = 0
                m = k - 1
                while m >= 0 and text[m] == "\\":
                    bs += 1
                    m -= 1
                if bs % 2 == 0:
                    break
                k += 1
            end = k + 1
        spans.append((j, end, kind))
        i = end
    return spans


class SpanIndex:
    def __init__(self, spans):
        self.starts = [s for s, _, _ in spans]
        self.ends = [e for _, e, _ in spans]

    def contains(self, pos: int) -> bool:
        idx = bisect.bisect_right(self.starts, pos) - 1
        return idx >= 0 and pos < self.ends[idx]


def strip_comments(text: str, spans) -> str:
    """Replace the userstyle's `/*/ ... /*/` comment spans with a single
    space (strings are kept). lesscpy's lexer would otherwise leave stray
    slashes behind them."""
    out = []
    i = 0
    for start, end, kind in spans:
        if kind != "comment":
            continue
        out.append(text[i:start])
        out.append(" ")
        i = end
    out.append(text[i:])
    return "".join(out)


def find_matching_brace(text: str, open_idx: int, spans: SpanIndex) -> int:
    """Index of the matching `}` for the `{` at open_idx, ignoring braces
    inside strings/comments."""
    depth = 0
    i = open_idx
    while True:
        nxt_open = text.find("{", i)
        nxt_close = text.find("}", i)
        if nxt_close == -1:
            return -1
        if nxt_open != -1 and nxt_open < nxt_close:
            if not spans.contains(nxt_open):
                depth += 1
            i = nxt_open + 1
        else:
            if not spans.contains(nxt_close):
                depth -= 1
                if depth == 0:
                    return nxt_close
            i = nxt_close + 1


def eval_condition(cond: str, variables: dict) -> bool:
    """Evaluate a guard condition string against the variable map."""

    def atom(value: str) -> bool:
        value = value.strip()
        negated = False
        if value.startswith("not "):
            negated = True
            value = value[4:]
        m = re.match(r"\(\s*@(\w+)\s*=\s*(.+?)\s*\)$", value)
        if not m:
            raise ValueError(f"unparsable guard atom: {value!r}")
        actual = variables.get(m.group(1))
        result = str(actual) == m.group(2)
        return (not result) if negated else result

    if " or " in cond:
        return any(eval_condition(p, variables) for p in re.split(r"\bor\b", cond))
    return all(atom(p) for p in re.split(r"\band\b", cond))


def resolve_guards(text: str, variables: dict) -> str:
    """Evaluate every nested `& when (...)` guard."""
    spans = SpanIndex(build_skip_spans(text))
    out = []
    i = 0
    while True:
        m = GUARD_RE.search(text, i)
        if m is None or spans.contains(m.start("cond")):
            if m is None:
                out.append(text[i:])
                break
            # rare: guard inside a string; skip past it safely
            out.append(text[i : m.end()])
            i = m.end()
            continue

        keep = eval_condition(m.group("cond"), variables)
        open_idx = m.end() - 1
        close_idx = find_matching_brace(text, open_idx, spans)
        if close_idx == -1:
            raise ValueError("unbalanced braces around guard at %d" % m.start())
        block = text[open_idx + 1 : close_idx]
        inner = process(block, variables)
        out.append(text[i : m.start()])
        if keep:
            # keep the `&` so lesscpy flattens the block into the parent selector
            out.append("& {" + inner + "}")
        i = close_idx + 1
    return "".join(out)


def _match_parens(text: str, open_idx: int, spans: SpanIndex):
    """Return index of matching ')' for '(' at open_idx, or None."""
    depth = 0
    i = open_idx
    while True:
        nxt_open = text.find("(", i)
        nxt_close = text.find(")", i)
        if nxt_close == -1:
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            if not spans.contains(nxt_open):
                depth += 1
            i = nxt_open + 1
        else:
            if not spans.contains(nxt_close):
                depth -= 1
                if depth == 0:
                    return nxt_close
            i = nxt_close + 1


def resolve_trailing_guards(text: str, variables: dict) -> str:
    """Evaluate `selector when (cond) { ... }` guards (trailing form)."""
    spans = SpanIndex(build_skip_spans(text))
    out = []
    i = 0
    while True:
        w = text.find("when", i)
        if w == -1:
            out.append(text[i:])
            break
        if spans.contains(w):
            i = w + 4
            continue
        # skip occurrences that are part of another word
        if w > 0 and (text[w - 1].isalnum() or text[w - 1] in "-_"):
            i = w + 4
            continue
        # condition must start within a few chars after `when`
        p = text.find("(", w, w + 8)
        if p == -1 or spans.contains(p):
            i = w + 4
            continue
        q = _match_parens(text, p, spans)
        if q is None:
            i = w + 4
            continue
        cond = text[p : q + 1]
        if len(cond) > 300:
            i = w + 4
            continue
        # the block must open right after the condition (whitespace only)
        k = text.find("{", q + 1)
        if k == -1 or text[q + 1 : k].strip() != "" or spans.contains(k):
            i = w + 4
            continue
        if not re.fullmatch(CONDITION, cond):
            i = w + 4
            continue
        # selector prefix: back to start of line, must not contain & or @
        line_start = text.rfind("\n", 0, w) + 1
        prefix = text[line_start:w]
        if "&" in prefix or "@" in prefix or "when" in prefix or "/*" in prefix:
            i = w + 4
            continue
        keep = eval_condition(cond, variables)
        close_idx = find_matching_brace(text, k, spans)
        if close_idx == -1:
            raise ValueError("unbalanced braces around guard at %d" % w)
        block = text[k + 1 : close_idx]
        inner = process(block, variables)
        if keep:
            # `selector when (cond) { ... }` -> `selector { ... }`: emit text
            # up to the guard token, then re-attach the selector line to its
            # block so the rule keeps its selector.
            out.append(text[i:w])
            out.append(text[line_start:w].rstrip() + " {" + inner + "}")
        else:
            # drop the whole construct; keeping only text before the selector
            # line preserves separators so surrounding rules stay well-formed
            out.append(text[i:line_start])
        i = close_idx + 1
    return "".join(out)


def process(text: str, variables: dict) -> str:
    """Run both guard passes (idempotent)."""
    text = resolve_guards(text, variables)
    text = resolve_trailing_guards(text, variables)
    return text


def main() -> None:
    text = open(SOURCE_CSS, encoding="utf-8").read()
    variables = parse_header_defaults(text)
    print("resolved variables:", variables)
    body = extract_main_block(text)
    for pattern, replacement in BARE_IDENT_REGEXES:
        body = pattern.sub(replacement, body)
    # lesscpy's tokenizer requires a space between @media and its parens
    body = re.sub(r"@media\s*\(", "@media (", body)
    body = process(body, variables)
    body_spans = build_skip_spans(body)
    body = strip_comments(body, body_spans)

    # ── integrity checks before handing off to lesscpy ────────
    spans = SpanIndex(build_skip_spans(body))
    depth = 0
    for idx in range(len(body)):
        if spans.contains(idx):
            continue
        if body[idx] == "{":
            depth += 1
        elif body[idx] == "}":
            depth -= 1
            if depth < 0:
                raise SystemExit(f"integrity check failed: unbalanced '}}' at {idx}")
    if depth != 0:
        raise SystemExit("integrity check failed: unbalanced braces remain")
    if GUARD_RE.search(body):
        raise SystemExit("integrity check failed: unresolved nested guard remains")
    if "& when" in body:
        raise SystemExit("integrity check failed: unresolved '& when' remains")
    for m in re.finditer(r"\bwhen\b", body):
        if not spans.contains(m.start()):
            raise SystemExit(
                "integrity check failed: residual 'when' guard near offset %d: %r"
                % (m.start(), body[max(0, m.start() - 60) : m.start() + 80])
            )

    with open(TMP_LESS, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    import lesscpy

    css = lesscpy.compile(TMP_LESS)
    if len(css) < 100000:
        raise SystemExit(f"integrity check failed: output suspiciously small ({len(css)} bytes)")
    for landmark in (".rbx-header", "#navbar-search-input"):
        if landmark not in css:
            raise SystemExit(f"integrity check failed: missing landmark selector {landmark}")
    with open(OUT_CSS, "w", encoding="utf-8", newline="\n") as f:
        f.write(css)
    os.remove(TMP_LESS)
    print(f"compiled {len(css)} bytes -> {OUT_CSS}")


if __name__ == "__main__":
    main()
