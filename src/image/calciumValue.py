import pymupdf as fitz  # PyMuPDF
from pdf2image import convert_from_path
import re
import cv2
import numpy as np
import requests
import tempfile
from io import BytesIO
import easyocr
from PIL import ImageEnhance, ImageFilter, Image
from .fineTuneImage import ImageProcessor
import os


class desired_image:
    def __init__(self, pdf_url=None, pdf_path=None, regex_patterns=None, crop_height=800, x_padding=300,
                 highlighted_pdf_path='highlighted_pdf.pdf', output_image_path='output_image.png', temp_image_path='temp_page_image.png'):
        """
        Initialize the class with the required parameters and start processing.
        :param pdf_url: URL of the PDF.
        :param pdf_path: Local path of the PDF.
        :param regex_patterns: List of regex patterns to highlight.
        :param crop_height: Height of the crop area below the highlighted text.
        :param x_padding: Padding to add on either side of the cropped region.
        :param highlighted_pdf_path: Path to save the highlighted PDF.
        :param output_image_path: Path to save the cropped image.
        :param temp_image_path: Path to save the temporary image for processing.
        """
        self.pdf_url = pdf_url
        self.pdf_path = pdf_path
        self.regex_patterns = regex_patterns or []
        self.crop_height = crop_height
        self.x_padding = x_padding
        self.highlighted_pdf_path = highlighted_pdf_path
        self.output_image_path = output_image_path
        self.temp_image_path = temp_image_path
        self.extracted_text = ""
        self.calcium_score = None

        # Automatically process the PDF when the object is created
        self.cropped_output = self.process()
        

    def fetch_pdf(self):
        """
        Fetch the PDF from a URL or use the local file path.
        :return: Path to the temporary or local PDF file.
        """
        if self.pdf_url:
            print(f"Fetching PDF from URL: {self.pdf_url}")
            response = requests.get(self.pdf_url)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.write(response.content)
                temp_file.close()
                print(f"PDF downloaded and saved temporarily at: {temp_file.name}")
                return temp_file.name
            else:
                print(f"Failed to fetch PDF from URL: {self.pdf_url}, Status Code: {response.status_code}")
                return None
        elif self.pdf_path:
            return self.pdf_path
        else:
            print("Either 'pdf_path' or 'pdf_url' must be provided.")
            return None

    def highlight_text_with_regex(self, pdf_path):
        """
        Highlight the target text in the PDF using regex patterns.
        :param pdf_path: Path to the PDF file.
        :return: Page number with the highlighted text.
        """
        doc = fitz.open(pdf_path)
        regex_list = [re.compile(pattern, re.IGNORECASE) for pattern in self.regex_patterns]

        for page_num in range(2, len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            matches_found = False

            for regex in regex_list:
                matches = [(m.start(), m.end()) for m in regex.finditer(text)]

                if matches:
                    matches_found = True
                    for start, end in matches:
                        match_text = text[start:end]
                        search_instances = page.search_for(match_text)
                        for rect in search_instances:
                            highlight = page.add_highlight_annot(rect)
                            highlight.set_colors(stroke=(0, 1, 0))  # Green highlight
                            highlight.update()

            if matches_found:
                doc.save(self.highlighted_pdf_path)
                print(f"Highlighted PDF saved at: {self.highlighted_pdf_path}")
                return page_num

        # print(f"No matches for regex patterns {self.regex_patterns} found in the PDF.")
        return None


    def detect_highlight_and_crop(self, image_path):
        """
        Detect the highlighted text region in the image and crop the area below it.
        :param image_path: Path to the input image.
        :return: Path to the cropped image.
        """
        image = cv2.imread(image_path)
        if image is None:
            print(f"Image not found at {image_path}")
            return None

        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([35, 50, 50])
        upper_hsv = np.array([85, 255, 255])
        mask = cv2.inRange(hsv_image, lower_hsv, upper_hsv)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # print("No highlighted region found in the image.")
            return None

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        crop_x_start = max(0, x - self.x_padding)
        crop_x_end = min(image.shape[1], x + w + self.x_padding)
        crop_y_start = y + h
        crop_y_end = min(image.shape[0], crop_y_start + self.crop_height)
        cropped_image = image[crop_y_start:crop_y_end, crop_x_start:crop_x_end]

        cv2.imwrite(self.output_image_path, cropped_image)
        # print(f"Cropped image saved at: {self.output_image_path}")
        ImageProcessor().crop_center_contour(image_path=self.output_image_path, output_path=self.output_image_path)

        return self.output_image_path


    def extract_text_with_easyocr(self, image_path):
        """
        Extract text from the given image file using EasyOCR.
        :param image_path: Path to the local image file.
        :return: Extracted text.
        """
        if not image_path:
            print("No image path provided for text extraction.")
            return ""

        reader = easyocr.Reader(['en'])
        try:
            image = Image.open(image_path)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.5)
            image = image.convert("L").filter(ImageFilter.MedianFilter(size=3))
            image = image.filter(ImageFilter.SHARPEN)
            image_np = np.array(image)
            text = reader.readtext(image_np, detail=0)
            extracted_text = "".join(text)
            # print(extracted_text)

            # Extract Calcium Score from text
            calcium_score_matches = re.findall(r"Total\s*:\s*([\d.]+)|Total\s*([\d.]+)|Total\s+\w*\s*\s*([\d.]+)|Total\s*Calcium\s*:\s*([\d.]+)", extracted_text)
            if calcium_score_matches:
                self.calcium_score = next(filter(None, calcium_score_matches[0]), None)
                
            return extracted_text
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return ""
        
    def process(self):
        """
        Orchestrates the entire process of highlighting, cropping, saving, uploading, and extracting text.
        """
    
        pdf_path = self.fetch_pdf()
        if not pdf_path:
            print("PDF could not be fetched. Stopping the process.")
            return None

        page_num = self.highlight_text_with_regex(pdf_path)
        if page_num is None:
            print("No matches found in the PDF. Stopping the process.")
            return None

        images = convert_from_path(self.highlighted_pdf_path, first_page=page_num + 1, last_page=page_num + 1)
        images[0].save(self.temp_image_path)
        cropped_image_path = self.detect_highlight_and_crop(self.temp_image_path)
        if(self.highlighted_pdf_path):
            os.remove(self.highlighted_pdf_path)
        if(self.temp_image_path):
            os.remove(self.temp_image_path)
        if not cropped_image_path:
            print("Cropped image not available. Stopping the process.")
            return None

        # Extract text from the uploaded image
        extracted_text = self.extract_text_with_easyocr(cropped_image_path)
        self.extracted_text = extracted_text
        return extracted_text

# # Example Usage
# if __name__ == "__main__":
#     pdf_path = '/mnt/nvme_disk2/User_data/nb57077k/cardiovision/phase1/Bicuspid.pdf'
#     regex_patterns = [r'(?i)aortic valve calcification']

#     processor = desired_image(
#         pdf_path=pdf_path,
#         regex_patterns=regex_patterns
#     )

#     # print("Cropped Image URL:", processor.cropped_output)
#     # print("Extracted Text:", processor.extracted_text)
#     print("Calcium Score:", processor.calcium_score)
