import time
import tempfile
import os
import numpy as np
import pandas as pd
import pdfplumber
import re
from pdf2image import convert_from_path, convert_from_bytes
from PIL import ImageEnhance, ImageFilter
import fitz
import requests
from io import BytesIO
from ..upload.s3 import S3Uploader
from ..image.calciumValue import desired_image
import uuid

class PDFExtractor:
    def __init__(self, pdf_path=None, pdf_url=None, unique_id=None):
        self.pdf_path = pdf_path
        self.pdf_url = pdf_url
        self.unique_id = unique_id
        self.extracted_text = ""
        self.values = {
            "url": None,
            "STJ Diameter": None,
            "Annulus Diameter": None,
            "Annulus Area": None,
            "Annulus Perimeter": None,
            "Annulus Perimeter Derived Diameter": None,
            "LVOT Diameter": None,
            "Asc Aorta Diameter": None,
            "RCA Height": None,
            "LCA Height": None,
            "SOV Height": None,
            "SOV Left Diameter": None,
            "SOV Right Diameter": None,
            "SOV Non Diameter": None,
            "Aortic Valve Anatomy Type": None,
            "Calcium Score": None,
        }
        self.patterns = {
            "STJ Diameter": r"STJ\s*Ø(?:\s*\d+(?:\.\d+)?%)?:\s*([\d.]+)\s*mm",
            "Annulus Diameter": r"Area\s*Derived\s*Ø:\s*([\d.]+)\s*mm",
            "Annulus Area": r"Area:\s*([\d.]+)\s*mm²",
            "Annulus Perimeter": r"Perimeter:\s*([\d.]+)\s*mm",
            "Annulus Perimeter Derived Diameter": r"Perimeter\s*Derived\s*Ø:\s*([\d.]+)\s*mm",
            "LVOT Diameter": r"LVOT\s*Ø(?:\s*\d+(?:\.\d+)?%)?:\s*([\d.]+)\s*mm",
            "Asc Aorta Diameter": r"Asc.\s*Aorta\s*Ø(?:\s*\d+(?:\.\d+)?%)?:\s*([\d.]+)\s*mm",
            "RCA Height": r"RCA\s*Height(?:\s*\d+(?:\.\d+)?%)?\s*:\s*([\d.]+)\s*mm",
            "LCA Height": r"LCA\s*Height(?:\s*\d+(?:\.\d+)?%)?\s*:\s*([\d.]+)\s*mm",
            "SOV Height": r"Sinus\s*of\s*Valsalva\s*Height(?:\s*\d+(?:\.\d+)?%)?\s*([\d.]+)\s*mm",
            "SOV Left Diameter": r"Left(?:\s*\d+(?:\.\d+)?%)?\s*:\s*([\d.]+)\s*mm",
            "SOV Right Diameter": r"Right(?:\s*\d+(?:\.\d+)?%)?\s*:\s*([\d.]+)\s*mm",
            "SOV Non Diameter": r"Non(?:\s*\d+(?:\.\d+)?%)?\s*:\s*([\d.]+)\s*mm",
            "Aortic Valve Anatomy Type": r"([A-Za-z0-9\s]+(?:\s+[A-Za-z0-9]+)*)\s+Aortic\s+Valve",
            "Calcium Score": [r"Total\s*:\s*([\d.]+)", r"Total\s+\w*\s*:\s*([\d.]+)", r'Total\s*Calcium\s*[^0-9]*([\d,\.]+)',r'Total\s*[^0-9]*([\d,\.]+)'],
        }

    def fetch_pdf_content(self):
        """
        Fetch the PDF content from a URL or local file.
        """
        if self.pdf_url:
            response = requests.get(self.pdf_url)
            if response.status_code == 200:
                return BytesIO(response.content)
            else:
                raise ValueError(f"Failed to fetch PDF from URL: {self.pdf_url}")
        elif self.pdf_path:
            return self.pdf_path
        else:
            raise ValueError("Either 'pdf_path' or 'pdf_url' must be provided.")

    def extract_text(self, pdf_content):
        """
        Extract text from the PDF using pdfplumber for faster processing.
        """
        pdf_bytes = pdf_content.read() if self.pdf_url else None
        page_text = ""

        # Use pdfplumber to extract text directly from the PDF
        with pdfplumber.open(BytesIO(pdf_bytes)) if self.pdf_url else pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages[:2]:  # Process the first 2 pages for optimization
                page_text += page.extract_text() + "\n" or ""
                print("before normalizing_____________",page_text)
                page_text = page_text.replace("\u00A0", " ")
                print("after normaizing________________",page_text)
        self.extracted_text = page_text  # Store the extracted text
        return page_text

    def extract_calcium(self) :
        regex_patterns = [r'(?i)aortic valve calcification']
        
        processor = desired_image(
            pdf_url=self.pdf_url,
            regex_patterns=regex_patterns,
            highlighted_pdf_path=f"{self.unique_id}_highlighted_pdf_calcium.pdf",
            output_image_path=f"{self.unique_id}_output_image_calcium.png",
            temp_image_path=f"{self.unique_id}_temp_page_image_calcium.png"
        )
        self.values['aorticValveCalcificationImage']=S3Uploader(s3_folder='TAVIVision/calcificaltion_image',file_path=f"{self.unique_id}_output_image_calcium.png", content_type = 'image/png').file_url
        if os.path.exists(f"{self.unique_id}_output_image_calcium.png"):
            os.remove(f"{self.unique_id}_output_image_calcium.png")
        print("Cropped Image URL:", processor.cropped_output)
        print("Extracted Text:", processor.extracted_text)
        print("Calcium Score:", processor.calcium_score)
        return processor.calcium_score

    
    @staticmethod
    def preprocess_image(image):
        """
        Enhance and preprocess the image for better OCR results.
        """
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)
        return image.convert("L").filter(ImageFilter.SHARPEN)
    
    def clean_extracted_text(self, match):
        cleaned_text = re.sub(r'[\n\r\x0c]+', ' ', match)
        cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
        cleaned_text = re.sub(r'(Aortic\s+Valve).*', r'\1', cleaned_text)
        cleaned_text = re.split(r'aortic valve', cleaned_text, flags=re.IGNORECASE)[0]
        # print(cleaned_text)
        return cleaned_text.strip()

    def extract_first_comment(self, text: str) -> str:
        """
        Extract the first comment from the 'Comment' or 'Comments' section.
        """
        matches = re.split(r"(?i)Comment[s]?:", text)
        
        if len(matches) >= 3:  # index 0 = before first comment, index 1 = first comment, index 2 = second comment
            second_comment_block = matches[2].strip()
            # Take the first line of the second comment section
            first_line = second_comment_block.splitlines()[0].strip()
            return self.clean_extracted_text(first_line)
        return None

    def extract_values(self, text):
        """
        Extract key-value pairs from the extracted text using patterns.
        """
        for key, pattern in self.patterns.items():
            if key == "Calcium Score":
               self.values[key]=self.extract_calcium()
            else : 
                match = re.findall(pattern, text, re.IGNORECASE)
                if match:
                    if key == "Aortic Valve Anatomy Type":
                        comment_text = self.extract_first_comment(text)
                        if comment_text:
                            self.values[key] = comment_text

                    else:
                        self.values[key] = match[0]


    def highlight_values_in_pdf(self, output_pdf_path):

        if self.pdf_url:
            pdf_content = self.fetch_pdf_content()
            temp_pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_pdf_file.write(pdf_content.read())
            temp_pdf_file.close()
            pdf_path = temp_pdf_file.name
        else:
            pdf_path = self.pdf_path
        # Define a color map for each key
        color_map = {
            "Annulus Area": (0.73, 0.93, 0.96),                     # lighter 8eecf5
            "Annulus Perimeter": (0.73, 0.94, 0.97),                # lighter 90dbf4
            "Annulus Perimeter Derived Diameter": (0.91, 0.79, 1.0), # lighter deaaff
            "STJ Diameter": (1.0, 0.88, 0.89),                      # lighter ffcfd2
            "Annulus Diameter": (0.80, 0.82, 1.0),                  # lighter d8bbff
            "LVOT Diameter": (1.0, 0.93, 0.87),                     # lighter fde4cf
            "RCA Height": (0.94, 0.81, 0.63),                       # lighter e7bc91
            "LCA Height": (0.97, 0.88, 0.78),                       # lighter f3d5b5
            "SOV Left Diameter": (0.99, 0.91, 0.90),                # lighter fae1dd
            "SOV Right Diameter": (0.996, 0.88, 0.85),              # lighter fcd5ce
            "SOV Non Diameter": (1.0, 0.82, 0.77),                  # lighter fec5bb
            "SOV Height": (1.0, 0.94, 0.90),                        # lighter ffe5d9
            "Asc Aorta Diameter": (0.98, 0.97, 0.80),               # lighter cfbaf0
            "Aortic Valve Anatomy Type": (0.83, 0.99, 0.86)         # lighter b9fbc0
        }

        # Open the original PDF
        doc = fitz.open(pdf_path)

        # Iterate through each page
        for page_num in range(3):
            page = doc[page_num]
            page_text = page.get_text("text")  # Extract the full text from the page
            # print(page_text)
            # For each key in pattern dictionary, search for the corresponding value or pattern
            for key, value in self.values.items():
                if key != "Calcium Score":
                    if value is not None:
                        # Prepare the value to find (adding ' mm' for Diameter and Height)
                        value_to_find = f"{value} mm" if "Diameter" in key or "Height" in key else str(value)
                        
                        # Search for the value text in the page
                        text_instances = page.search_for(value_to_find)
                        
                        # Check if the pattern exists for this key
                        pattern = self.patterns.get(key)
                        if pattern:
                            # Search for pattern matches in the page text
                            pattern_instances = list(re.finditer(pattern, page_text))

                            # Iterate through all pattern matches and check if the value is part of the same line
                            for match in pattern_instances:
                                matched_text = match.group()

                                # If the matched text contains the value (both pattern and value match), highlight the line
                                if value_to_find in matched_text:
                                    pattern_instances_coords = page.search_for(matched_text)

                                    # Highlight the coordinates where both value and pattern match
                                    for inst in pattern_instances_coords:
                                        # Use the color from the color map
                                        highlight_color = color_map.get(key, (1, 1, 1))  # Default to white if key not in map
                                        highlight = page.add_highlight_annot(inst)
                                        highlight.set_colors(stroke=highlight_color)
                                        highlight.update()
        print(output_pdf_path)
        # Save the output PDF with highlights
        doc.save(output_pdf_path)
        doc.close()

    def run_extraction(self, output_pdf_path="highlighted_output.pdf"):
        pdf_content = self.fetch_pdf_content()
        page_text = self.extract_text(pdf_content)
        self.extract_values(page_text)
        self.highlight_values_in_pdf(output_pdf_path)
        self.values["url"] = S3Uploader(s3_folder='TAVIVision/highlighted_pdf_report/',file_path = output_pdf_path, content_type='application/pdf').file_url
        return self.values
    



# pdf_url = "https://tavivision.s3.ap-south-1.amazonaws.com/pdfs/Bicuspid1a+report_ECG_PS49SE014_Landmark_Corelab+1.pdf"
# # pdf_path = "/home/neeraj/Bicuspid.pdf"
# start_time = time.time()
# # report_extractor = PDFExtractor(pdf_path=pdf_path)
# report_extractor = PDFExtractor(pdf_url=pdf_url)
# # report_extractor.extract_text_from_pdf()
# extracted_values = report_extractor.run_extraction()
# unique_id = str(uuid.uuid4())
# output_pdf_path = unique_id+".pdf"
# report_extractor.highlight_values_in_pdf(output_pdf_path=output_pdf_path)

# for key, value in extracted_values.items():
#    print(f"{key}: {value} mm" if "Diameter" in key or "Height" in key else f"{key}: {value}")
