import os
from PyPDF2 import PdfMerger, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

pdf_folder = "pdfs"
output_pdf = "merged_with_clickable_index.pdf"

pdf_files = sorted(
    [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")],
    key=lambda x: int(os.path.splitext(x)[0])
)

temp_index = "temp_index.pdf"
c = canvas.Canvas(temp_index, pagesize=A4)
width, height = A4
c.setFont("Helvetica-Bold", 18)
c.drawString(200, height - 50, "Index Page")
c.setFont("Helvetica", 12)

y = height - 100
link_positions = []
for i, file in enumerate(pdf_files, start=1):
    title = f"{i}. {os.path.splitext(file)[0]}"
    c.drawString(100, y, title)
    link_positions.append((title, y, i))
    y -= 20
    if y < 50:
        c.showPage()
        y = height - 50
c.save()

merger = PdfMerger()
merger.append(temp_index)

page_offset = 1
page_start_indices = {}

for i, file in enumerate(pdf_files, start=1):
    filepath = os.path.join(pdf_folder, file)
    reader = PdfReader(filepath)
    page_start_indices[i] = page_offset
    merger.append(filepath)
    merger.add_outline_item(f"{i}. {file}", page_offset)
    page_offset += len(reader.pages)

merger.write(output_pdf)
merger.close()

from PyPDF2 import PdfWriter

merged = PdfReader(output_pdf)
writer = PdfWriter()

for page in merged.pages:
    writer.add_page(page)

for title, y, i in link_positions:
    target_page = page_start_indices[i]
    writer.add_link(pagenum=0,  # index page
                    pagedest=target_page,
                    rect=(100, y - 2, 400, y + 12))

with open(output_pdf, "wb") as f:
    writer.write(f)

print("✅ Merged PDF created with clickable index:", output_pdf)