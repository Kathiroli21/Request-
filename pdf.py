import os
import fitz
import math

pdf_folder = "pdfs"
output_pdf = "merged_with_clickable_index.pdf"

def clean_title(fname):
    name = os.path.splitext(fname)[0]
    parts = name.split("_", 1)
    if parts[0].isdigit() and len(parts) > 1:
        return parts[1].replace("-", " ").strip()
    import re
    return re.sub(r'^\d+[\._\-\s]*', '', name).strip()

files = sorted(
    [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")],
    key=lambda x: int(os.path.splitext(x)[0])
)

merged = fitz.open()
index_page = merged.new_page(width=595, height=842)
page_offsets = {}
current_page_index = 1
for i, fname in enumerate(files, start=1):
    fp = os.path.join(pdf_folder, fname)
    doc = fitz.open(fp)
    page_offsets[i] = current_page_index
    current_page_index += doc.page_count
    doc.close()

margin_left = 40
margin_top = 60
line_height = 18
font_size_title = 20
font_size_entry = 12
index_page.insert_text((margin_left, margin_top),
                       "Index / Table of Contents",
                       fontsize=font_size_title,
                       fontname="helv",
                       fill=(0, 0, 0))
y = margin_top + 30
entries_per_page = math.floor((842 - (y + 40)) / line_height)
entry_rects = []
current_index_page_number = 0
entry_count = 0

for i, fname in enumerate(files, start=1):
    title = f"{i}. {clean_title(fname)}"
    if entry_count >= entries_per_page:
        index_page = merged.new_page(width=595, height=842)
        current_index_page_number += 1
        y = margin_top
        index_page.insert_text((margin_left, y),
                               "Index (cont.)",
                               fontsize=font_size_title,
                               fontname="helv",
                               fill=(0, 0, 0))
        y += 30
        entry_count = 0
    index_page.insert_text((margin_left, y),
                           title,
                           fontsize=font_size_entry,
                           fontname="helv",
                           fill=(0, 0, 0))
    text_width = fitz.get_text_length(title, fontsize=font_size_entry, fontname="helv")
    x0 = margin_left
    y0 = y - 2
    x1 = margin_left + max(300, text_width + 10)
    y1 = y + 12
    target_page = page_offsets[i]
    entry_rects.append((current_index_page_number, (x0, y0, x1, y1), target_page))
    y += line_height
    entry_count += 1

for fname in files:
    fp = os.path.join(pdf_folder, fname)
    merged.insert_pdf(fitz.open(fp))

num_index_pages = current_index_page_number + 1
for idx_page_rel, rect, target_page in entry_rects:
    abs_index_page = idx_page_rel
    page = merged[abs_index_page]
    x0, y0, x1, y1 = rect
    page.insert_link({
        "kind": fitz.LINK_GOTO,
        "from": fitz.Rect(x0, y0, x1, y1),
        "page": target_page
    })

merged.save(output_pdf)
merged.close()
print(f"✅ Created merged PDF with clickable index: {output_pdf}")