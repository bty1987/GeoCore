#!/usr/bin/env python3
"""PDF → 逐页 PNG 渲染质检。用法: python3 render_pages.py <file.pdf> [输出目录]
依赖: pip install pypdfium2
"""
import sys
import pathlib
import pypdfium2 as pdfium

pdf_path = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pdf_path.parent / (pdf_path.stem + "-pages")
out.mkdir(parents=True, exist_ok=True)
doc = pdfium.PdfDocument(str(pdf_path))
for i, page in enumerate(doc):
    page.render(scale=110 / 72).to_pil().save(out / f"page-{i + 1:02d}.png")
print(f"rendered {len(doc)} pages -> {out}")
