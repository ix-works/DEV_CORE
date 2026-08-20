#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""behavior_manifest.py — Davranış-yüzeyi manifest üreteci/doğrulayıcısı (F2, §11.3).

Davranış yüzeyi = ajanın davranışını şekillendiren proje-lokal dosyalar. Manifest
(hash envanteri) LİDER-onaylı PR ile güncellenir; session_start her oturum başında
canlı ağacı manifest'le karşılaştırır → kayıtsız/değişmiş dosya = BÜYÜK uyarı.
(Tespit post-load'dur; ÖNLEME F1'dedir — çevre duvarı.)

Kullanım:
  python core/scripts/behavior_manifest.py generate   # .claude/behavior-manifest.json yaz
  python core/scripts/behavior_manifest.py verify     # 0=eş, 1=sapma(rapor stdout)
Kütüphane: verify_quiet(proj) -> list[str] sapma satırları (session_start kullanır).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Davranış-yüzeyi kalemleri (proje-köküne göre). Dizinler özyinelemeli taranır;
# junction'lar (core'dan gelen agents/skills/commands) manifest DIŞI — onların
# bütünlüğü core-git'in işidir; buradaki amaç PROJE-LOKAL sapmaları yakalamak.
YUZEY_DOSYALAR = ["CLAUDE.md", "CLAUDE.local.md", ".mcp.json", "project.yaml",
                  "scripts/hook_shim.py", ".claude/settings.json"]
# ⚠GEVŞETME (2026-08-01, kullanıcı açık onayı — bug avı AV-20): `.claude/settings.local.json`
# yüzeyden ÇIKARILDI. Gerekçe: dosyayı Claude Code'un KENDİSİ her izin onayında yeniden yazar
# (git-ignore'lu, içeriği izin kayıtları) → manifest-diff her oturumda ateşleniyordu:
# session_start "bu oturumun çıktısına GÜVENME" diyor, config_change_guard exit 2 veriyor.
# Kalıcı açık alarm = gerçek tamper AYIRT EDİLEMEZ (alarm-yorgunluğu; F2'nin varlık amacını
# ortadan kaldırıyordu). Kaybedilen kapsam: o dosyaya ELLE eklenen bir izin artık alarm
# üretmez — bilinçli takas. `settings.json` (paylaşılan, git'li, hook kablolamasını taşıyan
# dosya) yüzeyde KALIR; asıl davranış-yüzeyi odur. İzin katmanı ayrıca D32 (always-allow
# yasağı) ile korunur. Geri alınırsa alarm da geri gelir.
YUZEY_DIZINLER = [".claude/rules"]  # varsa; nested CLAUDE.md'ler ayrıca taranır
MANIFEST = ".claude/behavior-manifest.json"


def _hash(p: Path) -> str:
    """Dosya imzası — SATIR-SONU NORMALİZE EDİLEREK (2026-08-20).

    ⚠ GEVŞETME (bilinçli, FP-kanıtlı): eskiden ham baytlar hash'leniyordu ⇒ yalnız
    satır-sonu (LF↔CRLF) farkı olan bir kopya "DEĞİŞMİŞ (manifest-onaysız)" sayılıyordu.
    ÖLÇÜM: kök `CLAUDE.md` `888e7624…` (5841 B, LF=71, CRLF=0) · worktree kopyası
    `337bd842…` (5912 B, CRLF=71) · **kök LF→CRLF çevrilince sha `337bd842…`** ⇒ içerik
    farkı **SIFIR**. Git `autocrlf` bu dönüşümü checkout'ta kendiliğinden yapar, yani
    uyarı geliştiricinin YAPTIĞI bir şeyi değil, git'in yaptığını bildiriyordu.
    ⛔ İzlenen yüzey TALİMAT METNİDİR (CLAUDE.md · rules/*.md · settings JSON'u);
    satır-sonu bu dosyalarda DAVRANIŞ TAŞIMAZ. Gerçek içerik değişikliği (tek karakter
    dahil) AYNEN yakalanır — korpus bunu mutasyonla kanıtlar.
    """
    ham = p.read_bytes()
    normal = ham.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    h = hashlib.sha256()
    h.update(normal)
    return h.hexdigest()[:16]


def _is_junction(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _topla(proj: Path) -> dict[str, str]:
    kayit: dict[str, str] = {}
    for rel in YUZEY_DOSYALAR:
        p = proj / rel
        if p.is_file():
            kayit[rel.replace("\\", "/")] = _hash(p)
    for rel in YUZEY_DIZINLER:
        d = proj / rel
        if d.is_dir() and not _is_junction(d):
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    kayit[str(f.relative_to(proj)).replace("\\", "/")] = _hash(f)
    # nested CLAUDE.md'ler (kök hariç; core junction'ı atla) — os.walk + DİZİN-BUDAMA.
    # (Eski rglob tüm ağacı yürüyordu; node_modules/.git filtresi sonuçta eleniyordu ama
    # yürüyüş budanmıyordu → session_start ~720ms manifest maliyeti; F2-P bulgusu 2026-07-08.)
    # ⚠ GEVŞETME (bilinçli, FP-kanıtlı): `worktrees` 2026-08-20'de eklendi.
    # Ajan worktree'leri (`.claude/worktrees/agent-<id>/`) aynı repo'nun GEÇİCİ
    # checkout'larıdır; içlerindeki `CLAUDE.md` kökün KOPYASIDIR (yukarıdaki `_hash`
    # notundaki ölçüm: içerik farkı SIFIR, yalnız satır-sonu). Manifest'e yazmak da
    # YANLIŞ olurdu: her yeni ajan worktree'si aynı uyarıyı yeniden üretir ⇒ UYARI
    # KÖRLÜĞÜ. Bunlar bağımsız bir davranış yüzeyi DEĞİLDİR.
    # ⛔ Ana ağaçtaki gerçek bir davranış dosyası AYNEN taranır (korpus çiviliyor).
    prune = {"node_modules", ".git", ".tmp", "core", "dist", "__pycache__", "worktrees"}
    for dirpath, dirnames, filenames in os.walk(proj):
        dirnames[:] = [d for d in dirnames
                       if d not in prune and not _is_junction(Path(dirpath) / d)]
        if "CLAUDE.md" in filenames:
            f = Path(dirpath) / "CLAUDE.md"
            rel = str(f.relative_to(proj)).replace("\\", "/")
            if rel != "CLAUDE.md":
                kayit[rel] = _hash(f)
    return kayit


def generate(proj: Path, only: list[str] | None = None) -> tuple[Path, list[str], list[str]]:
    """Manifest'i yazar. Döner: (yol, ONAYLANAN sapmalar, BEKLEMEDE kalan sapmalar).

    ⛔ I-1 — `generate` CERRAHİ DEĞİLDİ (2026-08-20 fix): tüm yüzeyi baştan damgalıyordu
    ⇒ o an bekleyen **HER** sapmayı topluca "onaylanmış" yapıyordu. Bir tur ölçüldü:
    `verify` **6 sapma** listeliyordu ve `generate` altısını da **sessizce** aklardı —
    içlerinde bilinçli olanlar da vardı, olmayanlar da. Bu, koruma mekanizmasının
    kendisini *"ya hep ya hiç"* hâline getirir ve pratikte KULLANILAMAZ kılar.

    ⭐ TASARIM KISITI: `behavior-manifest.json` **gitignore'dadır** (makine-lokal) ⇒
    değişikliği bir PR'da kimse GÖREMEZ. Tek denetim yüzeyi bu script'in ÇIKTISIDIR.
    Bu yüzden `generate` artık NEYİ onayladığını ve NEYİ beklemede bıraktığını
    satır satır basar; sessiz toplu-aklama artık mümkün değil.

    Args:
        only: yalnız bu göreli yolların kaydı güncellenir; geri kalan sapmalar
              BEKLEMEDE kalır (bir sonraki `verify` onları hâlâ gösterir).
    """
    m = proj / MANIFEST
    m.parent.mkdir(parents=True, exist_ok=True)
    canli = _topla(proj)

    if only is None:
        onceki = _manifest_oku(proj) or {}
        onaylanan = sorted(set(canli) - {k for k, v in onceki.items() if canli.get(k) == v})
        yeni = canli
        bekleyen: list[str] = []
    else:
        onceki = _manifest_oku(proj)
        if onceki is None:
            raise SystemExit(
                "[FAIL] --only için mevcut manifest GEREKLİ (yok). Önce tam `generate` koş."
            )
        istenen = {o.replace("\\", "/").strip() for o in only}
        bilinmeyen = sorted(i for i in istenen if i not in canli and i not in onceki)
        if bilinmeyen:
            raise SystemExit(
                "[FAIL] --only ile verilen yol(lar) ne canlı yüzeyde ne manifest'te: "
                + ", ".join(bilinmeyen)
                + "\n  ⇒ Yol tahmin etme; `verify` çıktısındaki yolu AYNEN kopyala."
            )
        yeni = dict(onceki)
        onaylanan = []
        for rel in sorted(istenen):
            if rel in canli:
                if yeni.get(rel) != canli[rel]:
                    onaylanan.append(rel)
                yeni[rel] = canli[rel]
            else:                      # diskte yok → kaydı DÜŞÜR (silme onayı)
                yeni.pop(rel, None)
                onaylanan.append(rel + " (kayıt DÜŞÜRÜLDÜ — diskte yok)")
        # Onaylanmayan sapmalar BEKLEMEDE kalmalı
        bekleyen = [s for s in _sapmalar(canli, yeni)]

    m.write_text(json.dumps(yeni, indent=1, sort_keys=True), encoding="utf-8")
    return m, onaylanan, bekleyen


def _manifest_oku(proj: Path) -> dict[str, str] | None:
    m = proj / MANIFEST
    if not m.exists():
        return None
    try:
        return json.loads(m.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sapmalar(canli: dict[str, str], beklenen: dict[str, str]) -> list[str]:
    """canli ↔ beklenen farkları (verify ile AYNI mantık — ikinci kopya YOK)."""
    out: list[str] = []
    for rel, h in canli.items():
        if rel not in beklenen:
            out.append(f"KAYITSIZ yeni davranış dosyası: {rel}")
        elif beklenen[rel] != h:
            out.append(f"DEĞİŞMİŞ (manifest-onaysız): {rel}")
    for rel in beklenen:
        if rel not in canli:
            out.append(f"manifest'te var, diskte YOK: {rel}")
    return out


def verify_quiet(proj: Path) -> list[str]:
    """Sapma listesi döndürür (boş=temiz). Manifest yoksa tek uyarı satırı."""
    m = proj / MANIFEST
    if not m.exists():
        return ["manifest YOK (.claude/behavior-manifest.json) — üret: "
                "python core/scripts/behavior_manifest.py generate"]
    try:
        beklenen = json.loads(m.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"manifest OKUNAMADI: {e}"]
    # TEK KAYNAK: `generate --only` de aynı fonksiyonu çağırır (ikinci kopya tutulmaz —
    # ayrışan iki kıyas mantığı bu evde daha önce kusur üretti).
    return _sapmalar(_topla(proj), beklenen)


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "generate":
        # `--only <yol>` tekrarlanabilir; `--only a,b` de kabul edilir.
        only: list[str] | None = None
        args = sys.argv[2:]
        for i, a in enumerate(args):
            if a == "--only" and i + 1 < len(args):
                only = (only or []) + [p for p in args[i + 1].split(",") if p.strip()]
            elif a.startswith("--only="):
                only = (only or []) + [p for p in a.split("=", 1)[1].split(",") if p.strip()]
        yol, onaylanan, bekleyen = generate(proj, only=only)
        kapsam = f"YALNIZ {len(only)} yol" if only is not None else "TÜM yüzey"
        print(f"[ OK ] manifest yazıldı: {yol} ({len(_topla(proj))} kalem · kapsam: {kapsam})")
        # ⛔ NE ONAYLANDIĞI GÖRÜNÜR OLMALI: manifest gitignored'dır, PR'da kimse göremez;
        # tek denetim yüzeyi bu çıktıdır. Sessiz toplu-aklama I-1'in ta kendisiydi.
        if onaylanan:
            print(f"  ONAYLANAN {len(onaylanan)} sapma:")
            for s in onaylanan:
                print("   ✔ " + s)
        else:
            print("  (onaylanan sapma yok — manifest zaten günceldi)")
        if only is None and len(onaylanan) > 1:
            print(f"  ⚠ TOPLU ONAY: yukarıdaki {len(onaylanan)} sapmanın HEPSİ tek komutla "
                  f"onaylandı. Bilinçli olmayan biri varsa ŞİMDİ geri al.")
            print("    Seçici onay: python core/scripts/behavior_manifest.py generate "
                  "--only <yol> [--only <yol2>]")
        if bekleyen:
            print(f"  ⏳ BEKLEMEDE kalan {len(bekleyen)} sapma (onaylanMADI):")
            for s in bekleyen:
                print("   ⛔ " + s)
        return 0
    sapmalar = verify_quiet(proj)
    if not sapmalar:
        print("[ OK ] behavior-manifest: canlı ağaç manifest'le EŞ")
        return 0
    print("[FAIL] behavior-manifest SAPMALARI:")
    for s in sapmalar:
        print("   ⛔ " + s)
    print("Onaylıysa: generate ile güncelle (lider-PR disiplini); değilse --safe-mode + lider'e bildir.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
