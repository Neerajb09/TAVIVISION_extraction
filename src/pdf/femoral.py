import pdfplumber
import re
from pdf2image import convert_from_path, convert_from_bytes
import requests
from io import BytesIO
import logging

class femoralExtractor:
    def __init__(self, pdf_path=None, pdf_url=None):
        self.pdf_path = pdf_path
        self.pdf_url = pdf_url
        self.extracted_text = ""
        self.values = {
            "CIA Right Diameter": None,
            "CIA Left Diameter": None,
            "EIA Right Diameter": None,
            "EIA Left Diameter": None,
            "FA Right Diameter": None,
            "FA Left Diameter": None,
        }
        
        self.vessel_patterns = {
            "CIA": r"Common\s+Iliac\s+Ø\s*Min:\s*([\d.]+)\s*mm",
            "EIA": r"External\s+Iliac\s+Ø\s*Min:\s*([\d.]+)\s*mm",
            "FA":  r"Femoral\s+Ø\s*Min:\s*([\d.]+)\s*mm",
        }

    # ---------------------------
    #  FETCH PDF
    # ---------------------------
    def fetch_pdf_content(self):
        if self.pdf_url:
            try:
                response = requests.get(self.pdf_url)
                if response.status_code == 200:
                    return BytesIO(response.content)
                else:
                    raise ValueError("Failed to fetch PDF from URL")
            except Exception as e:
                raise

        elif self.pdf_path:
            return self.pdf_path

        else:
            raise ValueError("Either pdf_path or pdf_url must be provided.")

    # ---------------------------
    #  EXTRACT TEXT
    # ---------------------------
    def extract_text(self, pdf_content):
        pdf_bytes = pdf_content.read() if self.pdf_url else None
        page_text = ""

        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) if self.pdf_url else pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[2:], start=3):
                    extracted = page.extract_text() or ""
                    page_text += extracted + "\n"
        except Exception as e:
            raise

        self.extracted_text = page_text
        return page_text

    # ---------------------------
    #  EXTRACT NUMERIC VALUES
    # ---------------------------
    def extract_values(self, text):

        for vessel, pattern in self.vessel_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)

            if len(matches) >= 1:
                self.values[f"{vessel} Right Diameter"] = float(matches[0])

            if len(matches) >= 2:
                self.values[f"{vessel} Left Diameter"] = float(matches[1])

            if len(matches) == 0:
                print("No value found for {vessel}")


    # ---------------------------
    #  MAIN PIPELINE
    # ---------------------------
    def run_extraction(self):
        try:
            pdf_content = self.fetch_pdf_content()
            text = self.extract_text(pdf_content)
            self.extract_values(text)
            return self.values            
        except Exception as e:
            raise

    def get_extracted_values(self):
        return self.values



if __name__ == "__main__":
    # Example PDF URL
    pdf_url = "https://cardio-vision.s3.ap-south-1.amazonaws.com/pdfs/06929f77-625c-4087-8002-82ec2bafebe0.pdf"

    # Create extractor object
    report_extractor = femoralExtractor(pdf_url=pdf_url)

    # Run extraction
    extracted_values = report_extractor.run_extraction()

    # Print extracted values
    print("\n---- EXTRACTED VALUES ----")
    for key, value in extracted_values.items():
        if "Diameter" in key or "Height" in key:
            print(f"{key}: {value} mm")
        else:
            print(f"{key}: {value}")


