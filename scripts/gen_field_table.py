# -*- coding: utf-8 -*-
"""CDS (+ interface + BDEF + ref_docs CSV) → alan açıklama tablosu (Markdown).

Amaç: TS Bölüm 4.5 (alan tablosu) ve KD Bölüm 6 (Alan Giriş Rehberi) için elle yazılan
alan tablolarını consumption CDS'ten otomatik üretmek (doğruluk kaynağı = CDS annotation'ı,
ChatGPT'nin önerdiği "screenshot→OCR" anti-pattern'inin doğru hali).

Çıkardığı bilgi (kaynak öncelik sırası):
  - Alan adı            : projection CDS eleman adı (alias varsa alias)
  - Anahtar mı          : 'key' öneki
  - Etiket              : @UI.lineItem label → @EndUserText.label → interface CDS'teki aynı eleman
                          → ref_docs CSV açıklaması (--ref-csv)
  - Filtrelenebilir     : @UI.selectionField var mı
  - Zorunlu (filtre)    : @Consumption.filter mandatory:true
  - Value-Help          : @Consumption.valueHelpDefinition entity.name
  - Düzenlenebilir mi   : sibling .bdef 'field ( readonly[: ...] ) A, B;' → Hayır

Sınır: "create'te zorunlu mu" CDS'ten kesin çıkmaz (parameter/abstract entity ister); bu kolon
bilgilendirme amaçlıdır, operatör KD'de gözden geçirmeli. Etiket çözülemeyen alan FLAG'lenir.

Kullanım:
    python gen_field_table.py <cds_yolu> [--ref-csv <dataelements_or_table_fields.csv>] [-o out.md]
    python gen_field_table.py <source_root>/SD/ZSD001_CLC/cds/ZSD001_C_SO_ITEM.cds
"""
import os
import re
import sys
import csv
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _body(text):
    """define ... entity NAME ... { BODY }  → (entity_name, projection_on, body).

    Body '{' aramaya define ifadesinden SONRA başlanır — yoksa define'dan önceki header
    annotation'larındaki '{' (ör. @ObjectModel.usageType: {...}) yanlışlıkla body sanılır.
    """
    m = re.search(r"define\s+(?:root\s+)?(?:view\s+entity|abstract\s+entity)\s+(\w+)", text)
    name = m.group(1) if m else "?"
    search_from = m.end() if m else 0
    pm = re.search(r"as\s+projection\s+on\s+(\w+)", text[search_from:])
    proj = pm.group(1) if pm else None
    if pm:
        search_from += pm.end()
    bi = text.find("{", search_from)
    if bi < 0:
        return name, proj, ""
    depth = 0
    for i in range(bi, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return name, proj, text[bi + 1:i]
    return name, proj, text[bi + 1:]


def _label_from_annots(annots):
    m = re.search(r"@UI\.lineItem\s*:\s*\[\{[^\]]*?label\s*:\s*'([^']+)'", annots, re.S)
    if m:
        return m.group(1)
    m = re.search(r"@EndUserText\.label\s*:\s*'([^']+)'", annots)
    if m:
        return m.group(1)
    return None


def parse_cds(path):
    """Döner: (entity_name, projection_on, [field dict...]). Association/redirect satırları atlanır."""
    text = _strip_comments(open(path, encoding="utf-8").read())
    name, proj, body = _body(text)
    fields = []
    annots = []
    # body'yi virgülle değil satır-mantığıyla taramak yerine token bazında: her '@' satırı
    # birikir, eleman satırı (key? NAME[ as ALIAS],) gelince flush.
    for raw in body.split("\n"):
        line = raw.strip().rstrip(",").strip()
        if not line:
            continue
        if line.startswith("@"):
            annots.append(line)
            continue
        # devam eden çok-satırlı annotation (ör. additionalBinding) — '@' ile başlamaz ama
        # önceki annotation'ın parçası olabilir; '{' '[' kapanmamışsa biriktir
        if annots and (line.endswith("]") or line.endswith("}") or line.endswith(")")) \
                and not re.match(r"^(key\s+)?[A-Za-z_]\w*\s*(:|,|$)", line):
            annots[-1] += " " + line
            continue
        # association / composition / redirect satırı → atla
        if re.match(r"^_\w+\s*[:]", line) or "redirected to" in line or " composition " in line:
            annots = []
            continue
        m = re.match(r"^(key\s+)?([A-Za-z_]\w*)(?:\s+as\s+(\w+))?\s*$", line)
        if not m:
            # ifade/cast alanı (alias yoksa) — atla ama annotation'ı temizle
            annots = []
            continue
        is_key = bool(m.group(1))
        elem = m.group(3) or m.group(2)
        ann = "\n".join(annots)
        fields.append({
            "name": elem,
            "key": is_key,
            "label": _label_from_annots(ann),
            "filter": "@UI.selectionField" in ann,
            "mandatory": bool(re.search(r"mandatory\s*:\s*true", ann)),
            "vh": (re.search(r"valueHelpDefinition[^\]]*?entity\s*:\s*\{\s*name\s*:\s*'([^']+)'", ann, re.S) or [None, None])[1],
        })
        annots = []
    return name, proj, fields


def parse_bdef_readonly(bdef_path):
    """sibling .bdef → readonly alan adları kümesi."""
    ro = set()
    if not os.path.exists(bdef_path):
        return ro
    txt = open(bdef_path, encoding="utf-8").read()
    for m in re.finditer(r"field\s*\(\s*readonly[^)]*\)\s*([^;]+);", txt):
        for f in m.group(1).split(","):
            f = f.strip()
            if f:
                ro.add(f)
    return ro


def load_csv_labels(csv_path):
    """ref_docs dataelements.csv / table_fields.csv → {NORMALIZE(name): description}."""
    out = {}
    if not csv_path or not os.path.exists(csv_path):
        return out
    with open(csv_path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = row.get("field_name") or row.get("name") or ""
            desc = row.get("description") or row.get("medium") or row.get("long") or ""
            if key and desc:
                out[_norm(key)] = desc.strip()
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def build_table(path, ref_csv=None):
    name, proj, fields = parse_cds(path)
    folder = os.path.dirname(path)
    # etiket fallback: interface CDS (as projection on X) → X.cds aynı klasörde
    iface_labels = {}
    if proj:
        ipath = os.path.join(folder, proj + ".cds")
        if os.path.exists(ipath):
            _, _, ifields = parse_cds(ipath)
            iface_labels = {f["name"]: f["label"] for f in ifields if f["label"]}
    # readonly: sibling .bdef + (projection ise) interface .bdef
    ro = parse_bdef_readonly(os.path.splitext(path)[0] + ".bdef")
    if proj:
        ro |= parse_bdef_readonly(os.path.join(folder, proj + ".bdef"))
    csv_labels = load_csv_labels(ref_csv)

    rows = []
    unresolved = []
    for f in fields:
        label = f["label"] or iface_labels.get(f["name"]) or csv_labels.get(_norm(f["name"])) or ""
        if not label:
            unresolved.append(f["name"])
            label = "_(etiket CDS'te yok)_"
        editable = "Hayır" if f["name"] in ro else "Evet"
        rows.append("| {nm} | {lb} | {k} | {flt} | {vh} | {ed} |".format(
            nm=f["name"], lb=label,
            k="🔑" if f["key"] else "",
            flt=("Evet" + (" (zorunlu)" if f["mandatory"] else "")) if f["filter"] else "",
            vh=f["vh"] or "", ed=editable))

    md = []
    md.append("### Alan Tablosu — `%s`%s" % (name, (" (projeksiyon: `%s`)" % proj) if proj else ""))
    md.append("")
    md.append("> Otomatik üretildi: `scripts/gen_field_table.py`. Etiketler CDS annotation'ından; "
              "düzenlenebilirlik sibling `.bdef` readonly'den. Operatör KD'de 'create'te zorunlu' "
              "kolonunu gözden geçirmeli (CDS'ten kesin çıkmaz).")
    md.append("")
    md.append("| Alan | Etiket | Anahtar | Filtre | Value-Help | Düzenlenebilir |")
    md.append("|---|---|---|---|---|---|")
    md.extend(rows)
    md.append("")
    md.append("_%d alan; %d salt-okunur._%s" % (
        len(fields), len(ro & {f["name"] for f in fields}),
        (" ⚠️ Etiketsiz: " + ", ".join(unresolved)) if unresolved else ""))
    return "\n".join(md)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cds")
    ap.add_argument("--ref-csv", default=None, help="ref_docs/dataelements.csv veya table_fields.csv")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args(argv)
    out = build_table(args.cds, args.ref_csv)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(out + "\n")
        print("OK →", args.out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
