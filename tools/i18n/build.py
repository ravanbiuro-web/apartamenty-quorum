"""Generuje wersje językowe strony (/en/, /de/, /es/, /uk/, /ru/) z polskich plików.

Użycie (z katalogu głównego repozytorium):  python3 tools/i18n/build.py
Po każdej zmianie tekstu na polskich stronach uruchom ponownie; nowe teksty dopisz do plików *.tsv
(skrypt wypisze brakujące).
"""
import html, json, os, re, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from common import PAGES, walk, norm  # noqa: E402

SITE = "https://apartamentyquorum.pl"
LANGS = {  # kod: (nazwa w menu, og:locale)
    "pl": ("Polski", "pl_PL"),
    "en": ("English", "en_GB"),
    "de": ("Deutsch", "de_DE"),
    "es": ("Español", "es_ES"),
    "uk": ("Українська", "uk_UA"),
    "ru": ("Русский", "ru_RU"),
}
MSG = {  # treść wiadomości SMS/WhatsApp -> numer tłumaczenia w *.tsv
    "Dzień dobry, jestem zainteresowany apartamentami w Quorum.": 900,
    "Dzień dobry, jestem zainteresowany apartamentem na 21. piętrze (Quorum).": 921,
    "Dzień dobry, jestem zainteresowany apartamentem na 23. piętrze (Quorum).": 923,
}
ASSET_RE = re.compile(r"^((?:\.\./)*)(img|video|css|js|fonts|zdjecia)/|^((?:\.\./)*)favicon\.svg")
PATH_ATTRS = ("src", "href", "srcset", "data-srcset", "imagesrcset", "poster", "data-plan", "data-src")

SWITCH_TEXT = {"Język / Language"} | {c.upper() for c in LANGS} | {n for n, _ in LANGS.values()}
segments = json.load(open(os.path.join(HERE, "segments.json")))


def load(lang):
    tr = {}
    for line in open(os.path.join(HERE, f"{lang}.tsv"), encoding="utf-8"):
        line = line.rstrip("\n")
        if line:
            i, t = line.split("\t", 1)
            tr[int(i)] = t
    return tr


def page_url(page, lang):
    path = "" if page == "index.html" else page.replace("index.html", "")
    return f"{SITE}/{'' if lang == 'pl' else lang + '/'}{path}"


def switcher(page, cur):
    path = "" if page == "index.html" else page.replace("index.html", "")
    items = []
    for code, (name, _) in LANGS.items():
        href = f"/{'' if code == 'pl' else code + '/'}{path}"
        cur_attr = ' aria-current="true"' if code == cur else ""
        items.append(f'<li><a href="{href}" hreflang="{code}" lang="{code}"{cur_attr}>'
                     f'<span class="lang-code">{code.upper()}</span> {name}</a></li>')
    return (
        '<!-- i18n:switch -->\n'
        '      <details class="lang-switch" data-lang-switch>\n'
        f'        <summary aria-label="Język / Language"><svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>{cur.upper()}</summary>\n'
        '        <ul role="list">\n          ' + "\n          ".join(items) + "\n        </ul>\n"
        '      </details>\n'
        '      <!-- /i18n:switch -->'
    )


def alternates(page):
    links = [f'<link rel="alternate" hreflang="{c}" href="{page_url(page, c)}">' for c in LANGS]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{page_url(page, "pl")}">')
    return "<!-- i18n:alt -->\n  " + "\n  ".join(links) + "\n  <!-- /i18n:alt -->"


def with_blocks(src, page, lang):
    """Wstawia/odświeża przełącznik języka i linki hreflang (idempotentnie)."""
    sw = switcher(page, lang)
    if "<!-- i18n:switch -->" in src:
        src = re.sub(r"<!-- i18n:switch -->.*?<!-- /i18n:switch -->", lambda m: sw, src, flags=re.S)
    else:
        src = src.replace("      </nav>\n    </div>\n  </header>", "      </nav>\n      " + sw + "\n    </div>\n  </header>", 1)
        assert sw in src, f"brak miejsca na przełącznik: {page}"
    alt = alternates(page)
    if "<!-- i18n:alt -->" in src:
        src = re.sub(r"<!-- i18n:alt -->.*?<!-- /i18n:alt -->", lambda m: alt, src, flags=re.S)
    else:
        src = re.sub(r'(  <link rel="canonical" href="[^"]*">\n)', lambda m: m.group(1) + "  " + alt + "\n", src, count=1)
        assert alt in src, f"brak canonical: {page}"
    return src


def fix_paths(src):
    def one(u):
        return "../" + u if ASSET_RE.match(u) else u

    def attr(m):
        name, val = m.group(1), m.group(2)
        if name in ("srcset", "data-srcset", "imagesrcset"):
            parts = [p.strip() for p in val.split(",")]
            val = ", ".join(" ".join([one(p.split()[0])] + p.split()[1:]) for p in parts if p)
        else:
            val = one(val)
        return f'{name}="{val}"'
    return re.sub(r'\b(' + "|".join(PATH_ATTRS) + r')="([^"]*)"', attr, src)


def fix_messages(src, tr):
    def msg(m):
        pre, q = m.group(1), m.group(2)
        text = urllib.parse.unquote(q)
        if text in MSG:
            return pre + urllib.parse.quote(tr[MSG[text]], safe="")
        return m.group(0)
    return re.sub(r'((?:wa\.me/\d+\?text=|sms:\+?\d+\?body=))([^"]+)', msg, src)


def translate(src, page, lang):
    tr = load(lang)
    idx = {s: i for i, s in enumerate(segments)}
    missing = set()

    def t(core):
        i = idx.get(core)
        if i is None or i not in tr:
            if core not in SWITCH_TEXT:
                missing.add(core)
            return None
        return tr[i]

    brand = re.search(r'<span class="brand-text">.*?</span>', src, re.S).group(0)
    out = walk(src, t, lambda n, v: t(v))
    out = re.sub(r'<span class="brand-text">.*?</span>', lambda m: brand, out, count=1, flags=re.S)
    out = out.replace('<html lang="pl">', f'<html lang="{lang}">', 1)
    out = out.replace('content="pl_PL"', f'content="{LANGS[lang][1]}"')
    out = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + page_url(page, lang), out, count=1)
    out = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + page_url(page, lang), out, count=1)
    out = out.replace('"inLanguage": "pl-PL"', f'"inLanguage": "{lang}"')
    out = fix_paths(out)
    out = fix_messages(out, tr)
    out = with_blocks(out, page, lang)
    return out, missing


def main():
    all_missing = {}
    for page in PAGES:
        p = os.path.join(ROOT, page)
        src = open(p, encoding="utf-8").read()
        src = with_blocks(src, page, "pl")
        open(p, "w", encoding="utf-8").write(src)
        for lang in LANGS:
            if lang == "pl":
                continue
            out, missing = translate(src, page, lang)
            dst = os.path.join(ROOT, lang, page)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w", encoding="utf-8").write(out)
            if missing:
                all_missing.setdefault(lang, set()).update(missing)
    for lang, m in all_missing.items():
        print(f"[{lang}] brak tłumaczeń ({len(m)}):", *sorted(m), sep="\n  ")
    print("Gotowe:", ", ".join(c for c in LANGS if c != "pl"))


if __name__ == "__main__":
    main()
