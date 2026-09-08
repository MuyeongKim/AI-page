"""Build the Korean user manual PDF from its editable Markdown source."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mypackage.version import CURRENT_RELEASE  # noqa: E402

INK = colors.HexColor('#183b3a')
TEAL = colors.HexColor('#117871')
MUTED = colors.HexColor('#516564')
PALE = colors.HexColor('#ecf7f3')
LINE = colors.HexColor('#d5e3df')
WIDTH = A4[0] - 84


def inline(text: str) -> str:
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text


def styles():
    body = ParagraphStyle(
        'Body', fontName='Manual', fontSize=10.2, leading=15,
        textColor=INK, wordWrap='CJK', spaceAfter=6,
    )
    return {
        'body': body,
        'title': ParagraphStyle(
            'Title', parent=body, fontName='ManualBold', fontSize=24,
            leading=33, spaceBefore=7, spaceAfter=13,
        ),
        'h2': ParagraphStyle(
            'Section', parent=body, fontName='ManualBold', fontSize=21,
            leading=29, spaceAfter=12, keepWithNext=True,
        ),
        'cover_h2': ParagraphStyle(
            'CoverHeading', parent=body, fontName='ManualBold', fontSize=13,
            leading=19, spaceBefore=8, spaceAfter=6, keepWithNext=True,
        ),
        'h3': ParagraphStyle(
            'Heading', parent=body, fontName='ManualBold', fontSize=12.1,
            leading=18, textColor=TEAL, spaceBefore=7,
            spaceAfter=5, keepWithNext=True,
        ),
        'step': ParagraphStyle(
            'Step', parent=body, leftIndent=17, firstLineIndent=-17,
            spaceAfter=5,
        ),
        'cell': ParagraphStyle(
            'Cell', parent=body, fontSize=9.4, leading=13.7, spaceAfter=0,
        ),
        'headcell': ParagraphStyle(
            'HeadCell', parent=body, fontName='ManualBold', fontSize=9.4,
            leading=13.7, textColor=colors.white, spaceAfter=0,
        ),
        'note': ParagraphStyle(
            'Note', parent=body, fontSize=9.6, leading=15, spaceAfter=0,
        ),
        'caption': ParagraphStyle(
            'Caption', parent=body, fontSize=8.4, leading=12,
            textColor=MUTED, spaceAfter=9,
        ),
        'tocpage': ParagraphStyle(
            'TocPage', parent=body, fontSize=9, leading=12,
            alignment=TA_CENTER, spaceAfter=0,
        ),
    }


def table_from_lines(lines, style, page):
    rows = [[cell.strip() for cell in row.strip('|').split('|')] for row in lines]
    rows = [r for r in rows if not all(re.fullmatch(r':?-+:?', c) for c in r)]
    first_column = 0.30 if page != 1 else 0.84
    if page == 11:
        first_column = 0.29
    widths = [WIDTH * first_column, WIDTH * (1 - first_column)]
    cells = []
    for index, row in enumerate(rows):
        cell_text = [inline(cell) for cell in row]
        if page == 1 and index > 0:
            cell_text = [f'<link href="#page{row[1]}">{cell}</link>' for cell in cell_text]
        cells.append([
            Paragraph(cell, style['headcell' if index == 0 else 'cell'])
            for cell in cell_text
        ])
    tab = Table(cells, colWidths=widths, hAlign='LEFT', repeatRows=1)
    pad = 4 if page == 1 else 5
    tab.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), pad),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
        ('LINEBELOW', (0, 0), (-1, -1), 0.35, LINE),
    ]))
    return [tab, Spacer(1, 9)]


def section_flowables(section, style, page):
    story = []
    lines = section.strip().splitlines()
    cursor = 0
    while cursor < len(lines):
        text = lines[cursor].strip()
        cursor += 1
        if not text:
            continue
        if text.startswith('|'):
            table_lines = [text]
            while cursor < len(lines) and lines[cursor].strip().startswith('|'):
                table_lines.append(lines[cursor].strip())
                cursor += 1
            story.extend(table_from_lines(table_lines, style, page))
        elif text.startswith('!['):
            match = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', text)
            if not match:
                raise ValueError(f'Invalid image: {text}')
            path = (ROOT / 'docs' / match.group(2)).resolve()
            picture = Image(str(path))
            scale = min(WIDTH / picture.imageWidth, 385 / picture.imageHeight)
            picture.drawWidth = picture.imageWidth * scale
            picture.drawHeight = picture.imageHeight * scale
            picture.hAlign = 'CENTER'
            story.extend([picture, Spacer(1, 7)])
        elif text.startswith('# '):
            title = inline(text[2:]).replace('Stay Up AI ', 'Stay Up AI<br/>', 1)
            story.append(Paragraph(title, style['title']))
        elif text.startswith('## '):
            key = 'cover_h2' if page == 1 else 'h2'
            story.append(Paragraph(inline(text[3:]), style[key]))
        elif text.startswith('### '):
            story.append(Paragraph(inline(text[4:]), style['h3']))
        elif text.startswith('> '):
            box = Table([[Paragraph(inline(text[2:]), style['note'])]], colWidths=[WIDTH])
            box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), PALE),
                ('LINEBEFORE', (0, 0), (0, -1), 3, TEAL),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(KeepTogether([box, Spacer(1, 10)]))
        elif re.match(r'^\d+\. ', text) or text.startswith('- '):
            label = text if not text.startswith('- ') else '• ' + text[2:]
            story.append(Paragraph(inline(label), style['step']))
        elif text.startswith('*') and text.endswith('*') and not text.startswith('**'):
            story.append(Paragraph(inline(text[1:-1]), style['caption']))
        else:
            story.append(Paragraph(inline(text), style['body']))
    return story


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', default='C:/Windows/Fonts/malgun.ttf')
    parser.add_argument('--bold-font', default='C:/Windows/Fonts/malgunbd.ttf')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('Manual', args.font))
    pdfmetrics.registerFont(TTFont('ManualBold', args.bold_font))
    pdfmetrics.registerFontFamily('Manual', normal='Manual', bold='ManualBold')
    source = ROOT / 'docs' / '사용설명서.md'
    content = source.read_text(encoding='utf-8')
    version_match = re.search(r'대상 버전 (V[\d.]+)', content)
    version = CURRENT_RELEASE.display_version
    if version_match is None or version_match.group(1) != version:
        raise ValueError(f'사용설명서의 대상 버전을 현재 앱 버전 {version}에 맞춰 주세요.')
    output = args.output or ROOT / 'output' / 'pdf' / f'Stay-Up-AI-사용설명서-{version}.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    sections = content.split('<!-- pagebreak -->')
    total = len(sections)
    style = styles()
    story = []
    for index, section in enumerate(sections, 1):
        if index > 1:
            story.append(PageBreak())
        story.extend(section_flowables(section, style, index))

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.bookmarkPage(f'page{doc.page}')
        if doc.page <= total:
            heading = sections[doc.page - 1].strip().splitlines()[0].lstrip('# ')
            canvas.addOutlineEntry(heading, f'page{doc.page}', level=0)
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(2)
        canvas.line(42, A4[1] - 34, A4[0] - 42, A4[1] - 34)
        canvas.setFillColor(MUTED)
        canvas.setFont('Manual', 8)
        canvas.drawString(42, A4[1] - 25, 'STAY UP AI  /  처음 사용자를 위한 사용설명서')
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(42, 39, A4[0] - 42, 39)
        canvas.drawString(42, 25, f'{version}  |  Windows EXE 기준')
        canvas.drawRightString(A4[0] - 42, 25, f'{doc.page} / {total}')
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=42, leftMargin=42,
        topMargin=53, bottomMargin=53,
        title='Stay Up AI 객체 탐지 프로그램 사용설명서',
        author='Stay Up AI', subject=f'처음 사용자를 위한 Windows 사용설명서 {version}',
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    from pypdf import PdfReader
    reader = PdfReader(output)
    if len(reader.pages) != total:
        raise RuntimeError(
            f'Page overflow: expected {total} pages, got {len(reader.pages)}. '
            'Revise the layout before delivery.'
        )
    print(f'Created {output} ({len(reader.pages)} pages)')


if __name__ == '__main__':
    main()
