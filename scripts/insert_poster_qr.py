#!/usr/bin/env python3
"""ポスターの `[QR]` プレースホルダを、実物の QR 画像に差し替える。

🔴 **ビルドスクリプトから組み直してはいけない。**実物には手編集が入っており
（9/21 の節）、組み直すと消える。9/25 の network 図・10/05 の Fig 1 と同じく
**zip の中を直接いじる。**

やること（4つだけ）:
  1. ppt/media/image3.png に QR を足す
  2. slide1.xml.rels に rId5（image3.png）を足す
  3. slide1.xml の `[QR]` の文字を消す
  4. 同じ座標に <p:pic> を1つ足す（枠の罫線より後ろに置くと上に描かれる）

座標は**実物から読む**。ビルドスクリプトの定数は単位が違う（96 = 48 inch）し、
手編集でずれている可能性がある。
"""
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs/poster/P202_poster_1007.pptx")
DST = os.path.join(ROOT, "docs/poster/P202_poster_1009_qr.pptx")
QR = os.path.join(ROOT, "docs/poster/assets/qr_supplement.png")
EMU = 914400

SLIDE = "ppt/slides/slide1.xml"
RELS = "ppt/slides/_rels/slide1.xml.rels"


def find_qr_box(xml):
    """`[QR]` のテキスト枠と、その直前にある正方形の枠を実物から探す。

    返す: (枠の off/ext, [QR] テキストの sp 文字列)
    """
    sps = re.findall(r"(?s)<p:sp>.*?</p:sp>", xml)
    qr_sp = None
    for sp in sps:
        if "<a:t>[QR]</a:t>" in sp:
            qr_sp = sp
            break
    if qr_sp is None:
        raise SystemExit("`[QR]` のプレースホルダが見つからない。既に差し替え済みか？")

    # [QR] の近くにある正方形（縦横が 1% 以内で一致）を枠とみなす
    box = None
    for sp in sps:
        m = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"', sp)
        if not m or "<a:t>" in sp:
            continue
        ox, oy, cx, cy = (int(v) for v in m.groups())
        if abs(cx - cy) < cx * 0.01 and cx > EMU and cx < 4 * EMU:
            box = (ox, oy, cx, cy)
    if box is None:
        raise SystemExit("QR の正方形の枠が見つからない")
    return box, qr_sp


def pic_xml(sid, rid, ox, oy, cx, cy):
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="QR supplementary handout"'
        f' descr="QR code linking to the supplementary handout at'
        f' https://ainus1022.github.io/cperf-idweek2026/"/>'
        f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{ox}" y="{oy}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )


def main():
    for p in (SRC, QR):
        if not os.path.exists(p):
            raise SystemExit(f"無い: {p}")

    zin = zipfile.ZipFile(SRC)
    names = zin.namelist()
    xml = zin.read(SLIDE).decode("utf8")
    rels = zin.read(RELS).decode("utf8")

    box, qr_sp = find_qr_box(xml)
    ox, oy, cx, cy = box
    print(f"QR 枠（実測）: ({ox/EMU:.3f}, {oy/EMU:.3f}) {cx/EMU:.3f}x{cy/EMU:.3f} in")

    if "image3.png" in " ".join(names) or 'Id="rId5"' in rels:
        raise SystemExit("image3.png か rId5 が既にある。手で確認すること")

    # 1) rels に追加
    rels_new = rels.replace(
        "</Relationships>",
        '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="../media/image3.png"/>'
        "</Relationships>")
    assert rels_new != rels

    # 2) 使われていない shape id を取る
    sid = max(int(m) for m in re.findall(r'<p:cNvPr id="(\d+)"', xml)) + 1

    # 3) `[QR]` の文字を消す（枠そのものは残す。罫線が QR の額縁になる）
    xml_new = xml.replace(qr_sp, qr_sp.replace("<a:t>[QR]</a:t>", "<a:t></a:t>"))
    assert xml_new != xml, "[QR] の消去に失敗"

    # 4) <p:pic> を spTree の最後に足す（最後 = 最前面）
    pic = pic_xml(sid, "rId5", ox, oy, cx, cy)
    xml_new = xml_new.replace("</p:spTree>", pic + "</p:spTree>")
    assert pic in xml_new

    # 書き出し。**エントリを1つ増やすだけ**で他は元のバイト列をそのまま写す
    # 🔴 `zin.getinfo()` の ZipInfo をそのまま writestr に渡してはいけない。
    # writestr はその ZipInfo を書き換える（header_offset・CRC）ので、
    # **読み出し元 zin のメタデータが壊れて以降 read できなくなる。**
    # 変更するエントリは CRC が食い違っても壊れる。両方の理由で、全エントリ
    # について新しい ZipInfo を作る。
    before = {n: zin.read(n) for n in names}      # 検算用。差し替え前のバイト列
    payload = []
    for n in names:
        info = zin.getinfo(n)
        if n == SLIDE:
            data = xml_new.encode("utf8")
        elif n == RELS:
            data = rels_new.encode("utf8")
        else:
            data = before[n]
        payload.append((n, info.date_time, info.compress_type, info.external_attr, data))

    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zo:
        for n, dt, ct, attr, data in payload:
            fresh = zipfile.ZipInfo(n, date_time=dt)
            fresh.compress_type = ct
            fresh.external_attr = attr
            zo.writestr(fresh, data)
        zo.write(QR, "ppt/media/image3.png")

    # --- 検算 ---
    zo = zipfile.ZipFile(DST)
    assert zo.testzip() is None, "zip が壊れている"
    n_in, n_out = len(names), len(zo.namelist())
    assert n_out == n_in + 1, f"エントリ数 {n_in} → {n_out}（+1 のはず）"
    assert zo.read("ppt/media/image3.png") == open(QR, "rb").read(), "QR 画像が一致しない"
    # 元のバイト列は payload に取ってある（zin は writestr で壊れうるので使わない）
    changed = [n for n in names if before[n] != zo.read(n)]
    print(f"エントリ: {n_in} → {n_out}（image3.png を追加）")
    print(f"変更されたエントリ: {changed}")
    assert changed == [SLIDE, RELS] or set(changed) == {SLIDE, RELS}, changed
    s2 = zo.read(SLIDE).decode("utf8")
    assert zo.read(RELS).decode("utf8").count('Id="rId5"') == 1
    assert "[QR]" not in s2, "[QR] が残っている"
    assert s2.count("<p:pic>") == xml.count("<p:pic>") + 1
    print(f"✓ {os.path.relpath(DST, ROOT)}")
    print(f"  1モジュール {25.4*cx/EMU/45:.2f} mm（余白4モジュール込み・45モジュール角）")


if __name__ == "__main__":
    main()
