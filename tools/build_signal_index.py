"""
Builds signal_index.json: every text label on every diagram PDF, with its
bounding box in PDF point space, so the viewer can let a user tap a label
(e.g. "BB1") and jump to every other place across all diagrams where the
same label appears.

Run: python tools/build_signal_index.py
Requires: pip install pymupdf
"""
import fitz
import json
import re
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def normalize(text):
    # "BB 1", "BB_1", "BB-1" -> "BB1" so lookups match regardless of how
    # the CAD export happened to space/join a label's sub-lines.
    return re.sub(r'[\s_\-./]+', '', text).upper()


def extract_labels(page):
    # get_text('words') returns coordinates in the page's raw/unrotated
    # mediabox space, NOT the rotated space that get_pixmap()/pdf.js render
    # into. These CAD-exported drawings are full of 90/270 degree page
    # rotations, so every bbox must be pushed through rotation_matrix to
    # line up with what the viewer (and a human) actually sees on screen.
    rot_matrix = page.rotation_matrix

    words = page.get_text('words')  # (x0,y0,x1,y1,text,block_no,line_no,word_no)
    groups = {}
    for x0, y0, x1, y1, text, block_no, line_no, word_no in words:
        key = (block_no, line_no)
        groups.setdefault(key, []).append((word_no, x0, y0, x1, y1, text))

    labels = []
    for key, items in groups.items():
        items.sort(key=lambda it: it[0])
        text = ' '.join(it[5] for it in items)
        x0 = min(it[1] for it in items)
        y0 = min(it[2] for it in items)
        x1 = max(it[3] for it in items)
        y1 = max(it[4] for it in items)
        norm = normalize(text)
        if not norm:
            continue
        rect = fitz.Rect(x0, y0, x1, y1) * rot_matrix
        labels.append({
            'text': text,
            'norm': norm,
            'bbox': [round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1)],
        })
    return labels


def main():
    index = []
    pdf_files = sorted(glob.glob(os.path.join(ROOT, '*.pdf')))
    for path in pdf_files:
        fname = os.path.basename(path)
        doc = fitz.open(path)
        for page_num, page in enumerate(doc, start=1):
            rect = page.rect
            labels = extract_labels(page)
            if not labels:
                continue
            index.append({
                'file': fname,
                'page': page_num,
                'pageWidth': round(rect.width, 1),
                'pageHeight': round(rect.height, 1),
                'labels': labels,
            })
        print(f'{fname}: {doc.page_count} pages indexed')

    out_path = os.path.join(ROOT, 'signal_index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))

    total_labels = sum(len(p['labels']) for p in index)
    print(f'Wrote {out_path} ({total_labels} labels across {len(index)} pages)')


if __name__ == '__main__':
    main()
