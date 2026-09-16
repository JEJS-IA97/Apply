import pdfplumber
import os
import glob

cv_dir = os.path.join(os.path.dirname(__file__), "cvs")
pdfs = glob.glob(os.path.join(cv_dir, "*.pdf"))

for pdf_path in pdfs:
    name = os.path.basename(pdf_path)
    print(f"\n{'='*60}")
    print(f"CV: {name}")
    print('='*60)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            print(text[:3000])
            if len(text) > 3000:
                print(f"\n... ({len(text)} total chars)")
    except Exception as e:
        print(f"Error: {e}")
