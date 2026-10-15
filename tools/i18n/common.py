"""Wspólne funkcje: wyciąganie i podmiana tekstów w HTML stron (bez zależności)."""
import html, re

PAGES = ["index.html", "apartament-21/index.html", "apartament-23/index.html"]
TAG_RE = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
ATTRS = ("alt", "aria-label", "title", "placeholder")
META_KEYS = ('name="description"', 'property="og:title"', 'property="og:description"', 'property="og:image:alt"')


def norm(s):
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


def has_words(s):
    return bool(re.search(r"[A-Za-zÀ-žА-яІіЇїЄєҐґ]{2,}", s))


def walk(src, fn_text, fn_attr):
    """Przechodzi po HTML; fn_text(core)->nowy tekst lub None, fn_attr(name, value)->nowa wartość lub None."""
    out, skip = [], None
    for part in TAG_RE.split(src):
        if not part:
            continue
        if part.startswith("<!--"):
            out.append(part); continue
        if part.startswith("<"):
            m = re.match(r"<\s*(/?)\s*([a-zA-Z0-9]+)", part)
            name = m.group(2).lower() if m else ""
            closing = m and m.group(1) == "/"
            if skip:
                if closing and name == skip:
                    skip = None
                out.append(part); continue
            if not closing and name in ("script", "style"):
                skip = name
            def sub_attr(am):
                an, q, val = am.group(1), am.group(2), am.group(3)
                if an == "content":
                    if not any(k in part for k in META_KEYS):
                        return am.group(0)
                new = fn_attr(an, norm(val)) if has_words(val) else None
                return am.group(0) if new is None else f'{an}={q}{html.escape(new, quote=True)}{q}'
            if not closing:
                part = re.sub(r'\b(alt|aria-label|title|placeholder|content)=(["\'])(.*?)\2', sub_attr, part, flags=re.S)
            out.append(part)
        else:
            if skip or not has_words(part):
                out.append(part); continue
            core = norm(part)
            new = fn_text(core)
            if new is None:
                out.append(part); continue
            lead = re.match(r"^\s*", part).group(0)
            trail = re.search(r"\s*$", part).group(0)
            out.append(lead + html.escape(new, quote=False) + trail)
    return "".join(out)


def title_of(src):
    return norm(re.search(r"<title>(.*?)</title>", src, re.S).group(1))
