import os
from PyPDF2 import PdfMerger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

pdf_folder = "pdfs"
output_pdf = "merged_with_index.pdf"

pdf_files = sorted(
    [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")],
    key=lambda x: int(os.path.splitext(x)[0])
)

index_pdf = "index_page.pdf"
c = canvas.Canvas(index_pdf, pagesize=A4)
width, height = A4
c.setFont("Helvetica-Bold", 18)
c.drawString(200, height - 50, "Index Page")
c.setFont("Helvetica", 12)

y = height - 100
for i, file in enumerate(pdf_files, start=1):
    title = f"{i}. {os.path.splitext(file)[0]}"
    c.drawString(100, y, title)
    y -= 20
    if y < 50:
        c.showPage()
        y = height - 50
c.save()

merger = PdfMerger()
merger.append(index_pdf)
page_offset = 1
for i, file in enumerate(pdf_files, start=1):
    filepath = os.path.join(pdf_folder, file)
    merger.append(filepath)
    merger.add_outline_item(f"{i}. {file}", page_offset)
    page_offset += 1

merger.write(output_pdf)
merger.close()
print(f"{output_pdf} created successfully.")