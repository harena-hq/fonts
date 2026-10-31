# SPDX-License-Identifier: Apache-2.0
"""Measure v0.3's Segoe targets on the reference browser; write data/v0_3/.

v0.3 matches what a page can request through CSS: OpenType features and
languages. This writes:

1. segoe-features.json: Segoe UI Variable's GSUB and GPOS language systems and
   their feature tags; its `dlig` as the character sequences its ligatures read
   and its contexts as characters; and the characters its `frac` reads. Only tags
   and code points: gsub.ps1 asserts the rest on the guest.
   gsub.ps1 reads these on the Windows machine; its output is passed in as a file
   and must name the same Segoe file (SHA-256) as the provenance.
2. cases.json, what is measured: the cases and the base-and-mark matrix's bases,
   marks and languages; and segoe/<Size>-<Weight>.json, one per face, what Segoe
   measures for them, in DOM layout at 1000 px (`widths`, one per case, in order;
   `delta`, per language, the marks that change a base's width):
   - cases: one width per case. A case is a text, the CSS that requests it (a
     `lang` and a declaration), and the HarfBuzz features the request turns into,
     or null where the browser synthesizes instead of shaping (font-variant-caps).
     Groups: `matrix` (every feature tag either font has or a page commonly
     asks for, on and, where HarfBuzz turns it on by default, off; every keyword
     value of the font-variant-* properties; every combination of two or more
     of dlig, frac, tnum, kerning off and liga off; every language either font
     has a system for; on fixed lines), `dlig` (every Segoe dlig sequence alone
     and after and before each printable ASCII character: without the feature,
     with it, with it and kerning off, and with it and the default ligatures
     off), `frac` (every digit pair over `/` and U+2044, each digit alone before
     and after either slash, and a few longer fractions, with and without
     diagonal-fractions, and with it and kerning off), `dotless` (`i`, `j`, `į`,
     `і`, `ј`, `ị`, `fi` and `ffi` before each spacing accent, Sk, with and without
     dlig, kerning and ccmp), `kern` (every pair Segoe kerns in any face, with ccmp
     off), `joiner` (every ligature Open Sans' ccmp or liga forms and each Segoe
     dlig sequence and context, with ZWJ in each subset of its gaps, which keeps
     composition from hiding a rule, plain, with kerning off and with the feature
     off), `cgj` (the same rules with CGJ, and each letter alone and before CGJ,
     which Segoe's ccmp reads and Open Sans does not map). font-variant-alternates' functional values
     need @font-feature-values and are left out; neither font has their features.
   - marks: every target letter followed by each combining mark (Mn, Me) both
     fonts map, without a language and in Turkish: the width minus the
     letter's, kept only where it is not zero.

Text is v0.1's target set, which Harena UI and Segoe both map, plus the
combining marks both map. A dlig input Segoe reaches only through composition
(`r` before t + U+0323, which composes to a letter Open Sans lacks) is coverage,
which PLAN.md leaves out.

Usage: python probe/v0_3/run.py <cdp-http-base> <repo-root-url> <provenance.json> <gsub.json>
"""
import itertools
import json
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, SEGOE, evaluate  # noqa: E402

WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
V0_1 = json.loads((ROOT / "data/v0_1/segoe-ui-variable.json").read_text())

FEATURE_LINE = "0123456789 1/2 3\u20444 gIJ fi ffi ffl rf rt \u015E\u0219\u0163\u0104 l\u00B7l \u0431 \u0192 \u03B2\u03C7 x2 H2O AVATo"
# precomposed and decomposed forms side by side: U+0130 and I + U+0307, i + U+0307,
# U+0301 and U+0308 after i
LANG_LINE = ("i \u0130 \u0131 fi I\u0307 i\u0307 i\u0301 i\u0308 \u015E\u015F \u0162\u0163 l\u00B7l "
             "\u0431 \u0453 \u0104\u0105 \u013B\u013C \u0145\u0146 \u03B2\u03C7 \u0392\u03A7")
# Tags a page can turn on that neither font may have: their absence is part of the check.
REGISTERED = ["c2sc", "calt", "case", "clig", "cpsp", "dlig", "hist", "hlig", "smcp", "swsh",
              "titl", "unic", "afrc", "sinf"]
# HarfBuzz's defaults for horizontal Latin, Greek and Cyrillic
DEFAULT_ON = ["abvm", "blwm", "calt", "ccmp", "clig", "curs", "dist", "kern", "liga", "locl",
              "mark", "mkmk", "rclt", "rlig"]
NUMERIC = {"normal": {}, "lining-nums": {"lnum": 1}, "oldstyle-nums": {"onum": 1},
           "proportional-nums": {"pnum": 1}, "tabular-nums": {"tnum": 1},
           "diagonal-fractions": {"frac": 1}, "stacked-fractions": {"afrc": 1},
           "ordinal": {"ordn": 1}, "slashed-zero": {"zero": 1}}
LIGATURES = {"normal": {}, "none": {"liga": 0, "clig": 0, "dlig": 0, "hlig": 0, "calt": 0},
             "common-ligatures": {"liga": 1, "clig": 1},
             "no-common-ligatures": {"liga": 0, "clig": 0},
             "discretionary-ligatures": {"dlig": 1}, "no-discretionary-ligatures": {"dlig": 0},
             "historical-ligatures": {"hlig": 1}, "no-historical-ligatures": {"hlig": 0},
             "contextual": {"calt": 1}, "no-contextual": {"calt": 0}}
POSITION = {"normal": {}, "super": {"sups": 1}, "sub": {"subs": 1}}
ALTERNATES = {"normal": {}, "historical-forms": {"hist": 1}}
EAST_ASIAN = {"normal": {}, "jis78": {"jp78": 1}, "jis83": {"jp83": 1}, "jis90": {"jp90": 1},
              "jis04": {"jp04": 1}, "simplified": {"smpl": 1}, "traditional": {"trad": 1},
              "full-width": {"fwid": 1}, "proportional-width": {"pwid": 1}, "ruby": {"ruby": 1}}
# The browser synthesizes these where the font lacks the feature, so no HarfBuzz
# features stand for them (null); titling-caps is not synthesized and is plain `titl`.
CAPS = {"normal": {}, "small-caps": None, "all-small-caps": None, "petite-caps": None,
        "all-petite-caps": None, "unicase": None, "titling-caps": {"titl": 1}}
# Every OpenType language system either font has, as the BCP 47 tag a page would use.
LANGSYS = {"CAT": "ca", "MAH": "mh", "MOL": "mo", "NAV": "nv", "ROM": "ro", "MKD": "mk",
           "SRB": "sr", "TRK": "tr", "APPH": "und-fonnapa", "IPPH": "und-fonipa"}
MORE_LANGS = ["az", "crh", "tt", "kk", "el", "ru", "bg", "en"]
CGJ = "\u034F"
DLIG = {"css": "font-variant-ligatures:discretionary-ligatures;", "features": {"dlig": 1}}
FRAC = {"css": "font-variant-numeric:diagonal-fractions;", "features": {"frac": 1}}
# Requests that combine with dlig and frac: kerning off, and the default ligatures
# off, which Harena UI has and Segoe does not.
KERN_OFF = ("font-kerning:none;", {"kern": 0})
DLIG_NO_LIGA = ("font-variant-ligatures:no-common-ligatures discretionary-ligatures;",
                {"liga": 0, "clig": 0, "dlig": 1})
# Every combination of two or more of Segoe's features that change width, with kerning
# and the default ligatures off, through font-feature-settings.
COMBINED = ["dlig", "frac", "tnum", "kern 0", "liga 0"]
FRAC_MORE = ["12/34", "1 1/2", "10/100", "1/2/3", "2026/10/30", "a/b", "1/", "/1", "\u20441",
             "1\u2044", "x1/2y"]


def tags_and_systems(font):
    tags, systems = set(), set()
    for t in ("GSUB", "GPOS"):
        table = font[t].table
        tags |= {r.FeatureTag for r in table.FeatureList.FeatureRecord}
        for s in table.ScriptList.ScriptRecord:
            systems |= {l.LangSysTag.strip() for l in s.Script.LangSysRecord}
    return tags, systems


def segoe_tags(gsub):
    tags = {f for k in ("GSUB", "GPOS") for v in gsub[k].values() for f in v}
    systems = {k.split("/")[1] for t in ("GSUB", "GPOS") for k in gsub[t]} - {"dflt"}
    return tags, systems


def dlig_sequences(gsub, mapped):
    """Every input Segoe's dlig reads, as text: its ligature sequences, and each
    context's character followed by each character that may follow it."""
    out = {"".join(map(chr, s)) for s in gsub["dlig"]["sequences"]}
    for c in gsub["dlig"]["contexts"]:
        out |= {chr(a) + chr(b) for a in c["input"] for b in c["lookahead"]}
    return sorted(s for s in out if all(ord(c) in mapped for c in s))


def check_frac(gsub):
    """The fraction cases cover what Segoe's frac reads: digits, `/` and U+2044."""
    extra = set(gsub["frac"]["reads"]) - {0x2F, 0x2044} - set(range(0x30, 0x3A))
    assert not extra, f"Segoe's frac reads {sorted(extra)}, which the cases do not cover"


def rule_texts(font, tag, usable):
    """Each ligature that feature forms in this font, as text: the lowest character
    of each component. A rule with a component outside `usable` is coverage."""
    chars = {}
    for cp, g in sorted(font.getBestCmap().items()):
        chars.setdefault(g, cp)
    table = font["GSUB"].table
    texts = set()
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag != tag:
            continue
        for i in record.Feature.LookupListIndex:
            for st in table.LookupList.Lookup[i].SubTable:
                for first, ligs in getattr(st, "ligatures", {}).items():
                    for lig in ligs:
                        comps = [first, *lig.Component]
                        if all(g in chars and chars[g] in usable for g in comps):
                            texts.add("".join(chr(chars[g]) for g in comps))
    return sorted(texts)


def cases(gsub, mapped, os_tags, os_systems, kerned=(), rules=()):
    sg_tags, sg_systems = segoe_tags(gsub)
    out, seen = [], set()

    def add(group, text, css="", lang="", features=None, synthesized=False):
        key = (group, text, css, lang)
        if key in seen:
            return
        seen.add(key)
        out.append({"group": group, "text": text, "css": css, "lang": lang,
                    "features": None if synthesized else ({} if features is None else features)})

    for line in (FEATURE_LINE, LANG_LINE):
        add("matrix", line)
        for tag in sorted(os_tags | sg_tags | set(REGISTERED)):
            add("matrix", line, f"font-feature-settings:'{tag}';", features={tag: 1})
            if tag in DEFAULT_ON:
                add("matrix", line, f"font-feature-settings:'{tag}' 0;", features={tag: 0})
        for prop, values in (("font-variant-numeric", NUMERIC), ("font-variant-ligatures", LIGATURES),
                             ("font-variant-position", POSITION), ("font-variant-caps", CAPS),
                             ("font-variant-alternates", ALTERNATES),
                             ("font-variant-east-asian", EAST_ASIAN)):
            for v, f in values.items():
                add("matrix", line, f"{prop}:{v};", features=f, synthesized=f is None)
        add("matrix", line, "font-kerning:none;", features={"kern": 0})
        for n in range(2, len(COMBINED) + 1):
            for combo in itertools.combinations(COMBINED, n):
                tags = [(c.split()[0], int(c.split()[1]) if " " in c else 1) for c in combo]
                css = "font-feature-settings:" + ", ".join(f"'{g}' {v}" for g, v in tags) + ";"
                add("matrix", line, css, features=dict(tags))
        unknown = (os_systems | sg_systems) - set(LANGSYS)
        assert not unknown, f"no BCP 47 tag for language systems {unknown}"
        for lang in sorted(set(LANGSYS.values()) | set(MORE_LANGS)):
            add("matrix", line, lang=lang)
        # Segoe's dlig is in its Turkish system too
        add("matrix", line, DLIG["css"], lang="tr", features=DLIG["features"])
        add("matrix", line, DLIG_NO_LIGA[0], lang="tr", features=DLIG_NO_LIGA[1])

    context = [chr(c) for c in range(33, 127) if c in mapped]
    for seq in dlig_sequences(gsub, mapped):
        for text in [seq] + [c + seq for c in context] + [seq + c for c in context]:
            add("dlig", text, DLIG["css"], features=DLIG["features"])
            add("dlig", text)
            add("dlig", text, DLIG["css"] + KERN_OFF[0], features={**DLIG["features"], **KERN_OFF[1]})
            add("dlig", text, DLIG_NO_LIGA[0], features=DLIG_NO_LIGA[1])

    # Segoe's ccmp draws `i` dotless before a spacing accent: each accent both fonts map
    # after `i`, `j`, `fi` and `ffi`, with and without dlig and kerning
    accents = [chr(c) for c in sorted(mapped) if unicodedata.category(chr(c)) == "Sk"]
    for x in accents:
        for text in [ch + x for ch in "ij\u012F\u0456\u0458\u1ECB"] + ["fi" + x, "ffi" + x]:
            add("dotless", text)
            add("dotless", text, KERN_OFF[0], features=KERN_OFF[1])
            add("dotless", text, DLIG["css"], features=DLIG["features"])
            add("dotless", text, DLIG["css"] + KERN_OFF[0], features={**DLIG["features"], **KERN_OFF[1]})
            # with ccmp off Segoe keeps the dot, so its own kerning there shows
            add("dotless", text, "font-feature-settings:'ccmp' 0;", features={"ccmp": 0})
            add("dotless", text, "font-feature-settings:'ccmp' 0, 'kern' 0;", features={"ccmp": 0, "kern": 0})

    # Every pair Segoe kerns in any face (v0.2), with ccmp off: a v0.2 "kern" that is
    # really Segoe's ccmp at work shows there as no kerning
    for a, b in sorted(kerned):
        add("kern", chr(a) + chr(b), "font-feature-settings:'ccmp' 0;", features={"ccmp": 0})

    digits = "0123456789"
    for a in digits:
        for b in digits:
            for sep in ("/", "\u2044"):
                add("frac", a + sep + b, FRAC["css"], features=FRAC["features"])
                add("frac", a + sep + b)
            add("frac", a + "/" + b, FRAC["css"] + KERN_OFF[0], features={**FRAC["features"], **KERN_OFF[1]})
    singles = [s for d in digits for s in (d + "/", d + "\u2044", "/" + d, "\u2044" + d)]
    for s in singles + FRAC_MORE:
        add("frac", s, FRAC["css"], features=FRAC["features"])
        add("frac", s)
        add("frac", s, FRAC["css"] + KERN_OFF[0], features={**FRAC["features"], **KERN_OFF[1]})
        add("frac", s, KERN_OFF[0], features=KERN_OFF[1])

    # A ZWJ between a rule's characters keeps HarfBuzz from composing them first and
    # does not stop the ligature, so these reach rules plain text never does
    for group, joiner in (("joiner", "\u200D"), ("cgj", CGJ)):
        for text, tag in rules:
            for gaps in itertools.product(("", joiner), repeat=len(text) - 1):
                joined = text[0] + "".join(g + c for g, c in zip(gaps, text[1:]))
                if tag == "dlig":
                    add(group, joined, DLIG["css"], features=DLIG["features"])
                    add(group, joined, DLIG["css"] + KERN_OFF[0], features={**DLIG["features"], **KERN_OFF[1]})
                    continue
                add(group, joined)
                add(group, joined, KERN_OFF[0], features=KERN_OFF[1])
                add(group, joined, f"font-feature-settings:'{tag}' 0;", features={tag: 0})
    # Segoe's ccmp reads CGJ, which Open Sans does not map: each letter alone and before it
    for letter in (chr(c) for c in sorted(mapped) if unicodedata.category(chr(c)).startswith("L")):
        add("cgj", letter)
        add("cgj", letter + CGJ)
    return out


def main():
    cdp, base, prov, gsub_file = sys.argv[1:5]
    provenance = json.loads(Path(prov).read_text())
    assert provenance["segoe_ui_variable"] == V0_1["provenance"]["segoe_ui_variable"], \
        "a different Segoe file than v0.1's target set was read from"
    gsub = json.loads(Path(gsub_file).read_text())
    assert "error" not in gsub, f"gsub.ps1: {gsub.get('error')}"
    assert gsub.pop("sha256") == provenance["segoe_ui_variable"]["sha256"], \
        "gsub.ps1 read a different Segoe file than the provenance names"
    check_frac(gsub)
    page = f"{base}/probe/page.html"
    out = ROOT / "data/v0_3"
    out.mkdir(parents=True, exist_ok=True)
    doc = {"provenance": {k: v for k, v in provenance.items() if k != "browser"}
           | {"method": "probe/v0_3/gsub.ps1 on the Windows machine"}, **gsub}
    (out / "segoe-features.json").write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")

    mapped = set(V0_1["target"])
    open_sans = TTFont(OPEN_SANS)
    os_cmap = open_sans.getBestCmap()
    os_tags, os_systems = tags_and_systems(open_sans)
    kerned = set()
    for path in sorted((ROOT / "data/v0_2/segoe").glob("*.json")):
        kerned |= {tuple(map(int, k.split(","))) for k, v in
                   json.loads(path.read_text())["kern"].items() if v}
    usable = set(V0_1["segoe_cmap"]) & set(os_cmap)
    rules = [(t, tag) for tag in ("ccmp", "liga") for t in rule_texts(open_sans, tag, usable)]
    rules += [(t, "dlig") for t in dlig_sequences(gsub, mapped)]
    case_list = cases(gsub, mapped, os_tags, os_systems, kerned, rules)
    bases = [chr(c) for c in sorted(mapped) if unicodedata.category(chr(c)).startswith("L")]
    segoe_cmap = set(V0_1["segoe_cmap"])
    marks = [chr(c) for c in sorted(os_cmap) if c in segoe_cmap
             and unicodedata.category(chr(c)) in ("Mn", "Me")]
    langs = ["", "tr"]
    method = ("DOM span width at 1000 px; cases: the CSS declaration on the span and `lang` on "
              "it; marks: each base followed by each mark, minus the base alone, nonzero only")
    shared = {"cases": case_list, "marks": {"bases": "".join(bases), "marks": "".join(marks),
                                            "langs": langs}}
    (out / "cases.json").write_text(json.dumps(shared, indent=0, sort_keys=True, ensure_ascii=False) + "\n")
    for fam in SEGOE:
        size = fam.removeprefix("Segoe UI Variable ")
        for w, name in WEIGHTS.items():
            r = evaluate(cdp, page, "../v0_3/features.js",
                         {"family": fam, "weight": w, "cases": case_list, "bases": bases,
                          "marks": marks, "langs": langs})
            assert len(r["cases"]) == len(case_list)
            data = {"provenance": {**provenance, "method": method},
                    "unit": "px at 1000 px font size", "face": {"family": fam, "weight": w},
                    "widths": r["cases"], "delta": r["marks"]}
            path = out / "segoe" / f"{size}-{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=0, sort_keys=True, ensure_ascii=False) + "\n")
            print(f"{size}-{name}: {len(case_list)} cases, "
                  f"{sum(len(v) for v in r['marks'].values())} nonzero marks")


if __name__ == "__main__":
    main()
