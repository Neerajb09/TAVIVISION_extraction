import fitz  # PyMuPDF
from pdf2image import convert_from_path
import re
import cv2
import numpy as np
import requests
import tempfile
from io import BytesIO
import os


class Calcification_image:
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
                raise ValueError(f"Failed to fetch PDF from URL: {self.pdf_url}, Status Code: {response.status_code}")
        elif self.pdf_path:
            return self.pdf_path
        else:
            raise ValueError("Either 'pdf_path' or 'pdf_url' must be provided.")

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
        print(f"No matches for regex patterns {self.regex_patterns} found in the PDF.")
        return None

    def detect_highlight_and_crop(self, image_path):
        """
        Detect the highlighted text region in the image and crop the area below it.
        :param image_path: Path to the input image.
        :return: Path to the cropped image.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Image not found at {image_path}")

        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([35, 50, 50])
        upper_hsv = np.array([85, 255, 255])
        mask = cv2.inRange(hsv_image, lower_hsv, upper_hsv)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No highlighted region found in the image.")

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        crop_x_start = max(0, x - self.x_padding)
        crop_x_end = min(image.shape[1], x + w + self.x_padding)
        crop_y_start = y + h
        crop_y_end = min(image.shape[0], crop_y_start + self.crop_height)
        cropped_image = image[crop_y_start:crop_y_end, crop_x_start:crop_x_end]

        cv2.imwrite(self.output_image_path, cropped_image)
        print(f"Cropped image saved at: {self.output_image_path}")

        return self.output_image_path

    def process(self):
        """
        Orchestrates the entire process of highlighting, cropping, saving, and uploading results.
        """
        pdf_path = self.fetch_pdf()
        page_num = self.highlight_text_with_regex(pdf_path)
        if(page_num is not None):
            images = convert_from_path(self.highlighted_pdf_path, first_page=page_num + 1, last_page=page_num + 1)
            if(self.highlighted_pdf_path):
                os.remove(self.highlighted_pdf_path)
            
            images[0].save(self.temp_image_path)
            self.detect_highlight_and_crop(self.temp_image_path)
            if(self.temp_image_path):
                os.remove(self.temp_image_path)




# Usage Example
# if __name__ == "__main__":
#     pdf_path = 'Bicuspid.pdf'
#     regex_patterns = [r'(?i)aortic valve calcification']

#     processor = Calcification_image(
#         pdf_path=pdf_path,
#         regex_patterns=regex_patterns
#     )
#     print(processor.cropped_output)