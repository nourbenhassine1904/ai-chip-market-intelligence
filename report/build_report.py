"""Build the Phase 9B Word report from Markdown using standard-library OOXML.

This document-only builder has no model imports or scientific output writes.
Use --refresh-tables only to redisplay archived CSV cells and regenerate the
Phase 9B traceability file. The canonical prose is report/rapport_final.md.
"""

import argparse
import hashlib
import re
import struct
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from report_sources import ROOT, markdown_table, tables, trace_csv

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}
for prefix, url in NS.items():
    ET.register_namespace(prefix, url)


def element(tag, attributes=None, text=None):
    prefix, local = tag.split(":")
    node = ET.Element(f"{{{NS[prefix]}}}{local}")
    for key, value in (attributes or {}).items():
        if ":" in key:
            p, k = key.split(":")
            key = f"{{{NS[p]}}}{k}"
        node.set(key, str(value))
    node.text = text
    return node


def child(parent, tag, attributes=None, text=None):
    node = element(tag, attributes, text)
    parent.append(node)
    return node


def xml(node):
    return ET.tostring(node, encoding="utf-8", xml_declaration=True)


def run(parent, text, bold=False, code=False, italic=False):
    node = child(parent, "w:r")
    props = child(node, "w:rPr")
    if bold:
        child(props, "w:b")
    if italic:
        child(props, "w:i")
    if code:
        child(props, "w:sz", {"w:val": 18})
    t = child(node, "w:t", text=text)
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def simple_math(text):
    node = element("m:r")
    child(node, "m:t", text=text)
    return node


def sub(base, index, superscript=None):
    node = element("m:sSubSup" if superscript else "m:sSub")
    child(node, "m:e").append(simple_math(base))
    child(node, "m:sub").append(simple_math(index))
    if superscript:
        child(node, "m:sup").append(simple_math(superscript))
    return node


def equation(name):
    para = element("m:oMathPara")
    props = child(para, "m:oMathParaPr")
    child(props, "m:jc", {"m:val": "center"})
    math = child(para, "m:oMath")
    expressions = {
        "log_return": [sub("r", "t"), simple_math(" = 100 [ ln("), sub("P", "t"),
                       simple_math(") − ln("), sub("P", "t−1"), simple_math(") ]")],
        "arima": [simple_math("Φ(B) Δᵈ "), sub("y", "t"),
                  simple_math(" = c + Θ(B) "), sub("ε", "t")],
        "var": [sub("r", "t"), simple_math(" = c + ")],
        "garch": [sub("σ", "t", "2"), simple_math(" = ω + α "), sub("ε", "t−1", "2"),
                  simple_math(" + β "), sub("σ", "t−1", "2")],
    }
    for part in expressions[name]:
        math.append(part)
    if name == "var":
        summation = child(math, "m:nary")
        nprops = child(summation, "m:naryPr")
        child(nprops, "m:chr", {"m:val": "∑"})
        child(nprops, "m:limLoc", {"m:val": "undOvr"})
        child(summation, "m:sub").append(simple_math("i=1"))
        child(summation, "m:sup").append(simple_math("p"))
        expr = child(summation, "m:e")
        expr.extend([sub("A", "i"), sub("r", "t−i")])
        math.extend([simple_math(" + "), sub("u", "t")])
    return para


class Document:
    def __init__(self):
        self.doc = element("w:document")
        self.body = child(self.doc, "w:body")
        self.rels = [("styles", "styles.xml", "styles"), ("settings", "settings.xml", "settings"),
                     ("header", "header1.xml", "header"), ("footer", "footer1.xml", "footer")]
        self.media = []
        self.heading_id = 0

    def paragraph(self, text="", style="Normal", align=None, keep=False):
        p = child(self.body, "w:p")
        props = child(p, "w:pPr")
        child(props, "w:pStyle", {"w:val": style})
        if align:
            child(props, "w:jc", {"w:val": align})
        if keep:
            child(props, "w:keepNext")
        pattern = r"(\[[^\]]+\]\(https?://[^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)"
        for part in re.split(pattern, text):
            match = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)]+)\)", part)
            if match:
                rid = f"link{len(self.rels)}"
                self.rels.append((rid, match[2], "hyperlink"))
                link = child(p, "w:hyperlink", {"r:id": rid})
                run(link, match[1])
                # Display the exact URL in bibliography and annex reference links.
                run(p, " (" + match[2] + ")", code=True)
            else:
                run(p, part.strip("*`") if part.startswith(("*", "`")) else part,
                    bold=part.startswith("**"), code=part.startswith("`"),
                    italic=part.startswith("*") and not part.startswith("**"))
        if style in ("Heading1", "Heading2"):
            self.heading_id += 1
            bookmark = element("w:bookmarkStart", {"w:id": self.heading_id,
                                                   "w:name": f"section{self.heading_id}"})
            p.insert(1, bookmark)
            child(p, "w:bookmarkEnd", {"w:id": self.heading_id})
        return p

    def pagebreak(self):
        p = child(self.body, "w:p")
        props = child(p, "w:pPr")
        child(props, "w:spacing", {"w:before": 0, "w:after": 0, "w:line": 1, "w:lineRule": "exact"})
        r = child(p, "w:r")
        child(child(r, "w:rPr"), "w:sz", {"w:val": 1})
        child(r, "w:br", {"w:type": "page"})

    def table(self, rows):
        count = len(rows[0])
        widths = {
            4: [2900, 1550, 2300, 2300],
            5: [2300, 1500, 1500, 1750, 2000],
            6: [2300, 700, 1550, 1500, 1500, 1500],
        }[count]
        if rows[0][0] == "Langue / loi":
            widths = [2700, 1200, 1200, 1200, 1300, 1450]
        if rows[0][0] == "Série":
            widths = [1400, 1600, 1450, 1450, 3150]
        t = child(self.body, "w:tbl")
        props = child(t, "w:tblPr")
        child(props, "w:tblW", {"w:w": sum(widths), "w:type": "dxa"})
        child(props, "w:tblLayout", {"w:type": "fixed"})
        borders = child(props, "w:tblBorders")
        for tag in ["top", "left", "bottom", "right", "insideH", "insideV"]:
            child(borders, "w:" + tag, {"w:val": "single", "w:sz": 4, "w:color": "D9D9D9"})
        margins = child(props, "w:tblCellMar")
        for tag, val in [("top", 60), ("bottom", 60), ("left", 90), ("right", 90)]:
            child(margins, "w:" + tag, {"w:w": val, "w:type": "dxa"})
        grid = child(t, "w:tblGrid")
        for width in widths:
            child(grid, "w:gridCol", {"w:w": width})
        for index, row in enumerate(rows):
            tr = child(t, "w:tr")
            trprops = child(tr, "w:trPr")
            child(trprops, "w:cantSplit")
            if index == 0:
                child(trprops, "w:tblHeader")
            for i, value in enumerate(row):
                cell = child(tr, "w:tc")
                cp = child(cell, "w:tcPr")
                child(cp, "w:tcW", {"w:w": widths[i], "w:type": "dxa"})
                child(cp, "w:vAlign", {"w:val": "center"})
                child(cp, "w:shd", {"w:fill": "DCE6EF" if index == 0 else ("F4F6F8" if index % 2 == 0 else "FFFFFF")})
                p = child(cell, "w:p")
                pp = child(p, "w:pPr")
                child(pp, "w:pStyle", {"w:val": "TableText"})
                child(pp, "w:jc", {"w:val": "left" if i == 0 else "center"})
                run(p, value, bold=index == 0)

    def picture(self, path, description):
        data = path.read_bytes()
        width, height = struct.unpack(">II", data[16:24])
        cx = 5600000  # About 15.55 cm, within A4 margins.
        cy = int(cx * height / width)
        maximum_height = 3100000 if "Annexe" not in description else 3000000
        if "phase7_rmse" in path.name:
            maximum_height = 2200000
        if cy > maximum_height:
            cx = int(cx * maximum_height / cy)
            cy = maximum_height
        index = len(self.media) + 1
        rid = f"image{index}"
        self.media.append((f"image{index}.png", data))
        self.rels.append((rid, f"media/image{index}.png", "image"))
        p = self.paragraph(align="center", keep=True)
        drawing = child(child(p, "w:r"), "w:drawing")
        inline = child(drawing, "wp:inline", {"distT": 0, "distB": 0, "distL": 0, "distR": 0})
        child(inline, "wp:extent", {"cx": cx, "cy": cy})
        child(inline, "wp:docPr", {"id": index, "name": path.name, "descr": description})
        child(inline, "wp:cNvGraphicFramePr")
        graphic = child(inline, "a:graphic")
        gd = child(graphic, "a:graphicData", {"uri": NS["pic"]})
        pic = child(gd, "pic:pic")
        nv = child(pic, "pic:nvPicPr")
        child(nv, "pic:cNvPr", {"id": 0, "name": path.name})
        child(nv, "pic:cNvPicPr")
        fill = child(pic, "pic:blipFill")
        child(fill, "a:blip", {"r:embed": rid})
        child(child(fill, "a:stretch"), "a:fillRect")
        sp = child(pic, "pic:spPr")
        transform = child(sp, "a:xfrm")
        child(transform, "a:off", {"x": 0, "y": 0})
        child(transform, "a:ext", {"cx": cx, "cy": cy})
        child(child(sp, "a:prstGeom", {"prst": "rect"}), "a:avLst")

    def save(self, path):
        sect = child(self.body, "w:sectPr")
        child(sect, "w:headerReference", {"w:type": "default", "r:id": "header"})
        child(sect, "w:footerReference", {"w:type": "default", "r:id": "footer"})
        child(sect, "w:pgSz", {"w:w": 11906, "w:h": 16838})
        child(sect, "w:pgMar", {"w:top": 1417, "w:right": 1417, "w:bottom": 1417,
                               "w:left": 1417, "w:header": 650, "w:footer": 650, "w:gutter": 0})
        child(sect, "w:titlePg")
        header = element("w:hdr")
        p = child(header, "w:p")
        child(child(p, "w:pPr"), "w:pStyle", {"w:val": "Caption"})
        run(p, "TEK-UP | AI-Chip Market Intelligence | 2026/2027")
        footer = element("w:ftr")
        p = child(footer, "w:p")
        child(child(p, "w:pPr"), "w:jc", {"w:val": "right"})
        field = child(p, "w:fldSimple", {"w:instr": "PAGE"})
        run(field, "1")
        styles = element("w:styles")
        defaults = child(styles, "w:docDefaults")
        rpr = child(child(defaults, "w:rPrDefault"), "w:rPr")
        child(rpr, "w:rFonts", {"w:ascii": "Times New Roman", "w:hAnsi": "Times New Roman"})
        child(rpr, "w:sz", {"w:val": 22})
        child(rpr, "w:color", {"w:val": "000000"})
        child(rpr, "w:lang", {"w:val": "fr-FR"})
        definitions = [("Normal", 22, False, 60), ("Title", 36, True, 240),
                       ("Heading1", 30, True, 180), ("Heading2", 24, True, 120),
                       ("Caption", 18, False, 90), ("TableText", 20, False, 0),
                       ("Reference", 20, False, 150), ("TOC1", 22, False, 100),
                       ("TOC2", 20, False, 60)]
        for name, size, bold, after in definitions:
            st = child(styles, "w:style", {"w:type": "paragraph", "w:styleId": name})
            child(st, "w:name", {"w:val": {"Heading1": "heading 1", "Heading2": "heading 2"}.get(name, name)})
            if name != "Normal":
                child(st, "w:basedOn", {"w:val": "Normal"})
            child(st, "w:next", {"w:val": "Normal"})
            pp = child(st, "w:pPr")
            spacing = child(pp, "w:spacing", {"w:after": after, "w:line": 276 if name != "TableText" else 240, "w:lineRule": "auto"})
            child(pp, "w:widowControl")
            if name.startswith("Heading"):
                child(pp, "w:keepNext")
                spacing.set(f"{{{NS['w']}}}before", "100")
                child(pp, "w:outlineLvl", {"w:val": int(name[-1])-1})
            rp = child(st, "w:rPr")
            child(rp, "w:sz", {"w:val": size})
            child(rp, "w:color", {"w:val": "000000"})
            if bold:
                child(rp, "w:b")
        settings = element("w:settings")
        child(settings, "w:updateFields", {"w:val": "true"})
        child(settings, "w:defaultTabStop", {"w:val": 720})
        child(settings, "w:doNotAutoCompressPictures")
        relationships = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        for rid, target, kind in self.rels:
            escaped = target.replace("&", "&amp;")
            mode = ' TargetMode="External"' if kind == "hyperlink" else ""
            relationships += (f'<Relationship Id="{rid}" Target="{escaped}" '
                              f'Type="{NS["r"]}/{kind}"{mode}/>')
        relationships += "</Relationships>"
        content_types = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                         '<Default Extension="xml" ContentType="application/xml"/>'
                         '<Default Extension="png" ContentType="image/png"/>')
        for part, kind in [("document", "document"), ("styles", "styles"), ("settings", "settings"),
                           ("header1", "header"), ("footer1", "footer")]:
            if part == "document":
                kind = "document.main"
            content_types += (f'<Override PartName="/word/{part}.xml" '
                              f'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}+xml"/>')
        content_types += "</Types>"
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             f'<Relationship Id="doc" Type="{NS["r"]}/officeDocument" Target="word/document.xml"/></Relationships>')
            for name, node in [("document", self.doc), ("styles", styles), ("settings", settings),
                               ("header1", header), ("footer1", footer)]:
                archive.writestr(f"word/{name}.xml", xml(node))
            archive.writestr("word/_rels/document.xml.rels", relationships)
            for name, data in self.media:
                archive.writestr("word/media/" + name, data)


def build(source, target):
    doc = Document()
    lines = source.splitlines()
    i = 0
    front = True
    references = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "<!-- pagebreak -->":
            doc.pagebreak()
        elif line == "<!-- toc -->":
            p = doc.paragraph()
            field = child(p, "w:fldSimple", {"w:instr": 'TOC \\o "1-2" \\h \\z \\u'})
            run(field, "Sommaire actualisé par Word lors du rendu")
        elif line.startswith("<!-- equation:"):
            name = re.fullmatch(r"<!-- equation: (\w+) -->", line)[1]
            p = doc.paragraph()
            p.append(equation(name))
        elif line.startswith("<!--"):
            pass
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [part.strip() for part in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", part) for part in row):
                    rows.append(row)
                i += 1
            doc.table(rows)
            continue
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[([^\]]+)\]\(([^)]+)\)", line)
            doc.picture((ROOT / "report" / match[2]).resolve(), match[1])
        elif line.startswith("# "):
            title = line[2:]
            if front and title != "Sommaire":
                doc.paragraph(title, "Title", align="center")
            elif title == "Sommaire":
                doc.paragraph(title, "Title")
                front = False
            else:
                front = False
                references = title == "Références"
                doc.paragraph(title, "Heading1")
        elif line.startswith("## "):
            front = False
            doc.paragraph(line[3:], "Heading2")
        else:
            style = "Caption" if line.startswith(("Figure ", "Tableau ", "Source", "Sources")) else "Normal"
            if references:
                style = "Reference"
            doc.paragraph(line, style, align="center" if front else None)
        i += 1
    doc.save(target)


def refresh_tables(source):
    for name, (headers, rows, _) in tables().items():
        start = f"<!-- table: {name} -->"
        end = f"<!-- endtable: {name} -->"
        replacement = start + "\n\n" + markdown_table(headers, rows) + "\n\n" + end
        if end in source:
            source = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _, value=replacement: value,
                            source, flags=re.DOTALL)
        else:
            source = source.replace(start, replacement)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-tables", action="store_true")
    args = parser.parse_args()
    path = ROOT / "report/rapport_final.md"
    source = path.read_text(encoding="utf-8")
    if args.refresh_tables:
        source = refresh_tables(source)
        path.write_text(source, encoding="utf-8", newline="\n")
        (ROOT / "docs/phase9b_results_traceability.csv").write_text(trace_csv(), encoding="utf-8", newline="\n")
    elif refresh_tables(source) != source:
        raise ValueError("Canonical Markdown tables differ from archived CSVs; review before refreshing")
    build(source, ROOT / "report/rapport_final.docx")
    print("DOCX built from Markdown; source SHA256=" + hashlib.sha256(path.read_bytes()).hexdigest())
    print("No models executed. Real page count requires the Word rendering step.")


if __name__ == "__main__":
    main()
