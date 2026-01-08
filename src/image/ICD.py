import fitz  # PyMuPDF
from pdf2image import convert_from_path
import regex as re
import cv2
import numpy as np
import requests
import tempfile
import os
from io import BytesIO

class PDFHighlighterAndCropper:
    def __init__(self, pdf_url= None, pdf_path = None):
        self.pdf_url = pdf_url
        self.pdf_path1 = pdf_path
        self.crop_height = 800
        self.x_padding = 400
        self.pdf_path = self.fetch_pdf()
        
    def fetch_pdf(self):
        
        if self.pdf_url:
            print(f"Fetching PDF from URL: {self.pdf_url}")
            response = requests.get(self.pdf_url)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name
            else:
                raise ValueError(f"Failed to fetch PDF from URL: {self.pdf_url}, Status Code: {response.status_code}")
        elif self.pdf_path1:
            return self.pdf_path1
        else:
            raise ValueError("Either 'pdf_path' or 'pdf_url' must be provided.")

    def highlight_text_with_regex(self, pdf_path, regex_patterns,highlighted_pdf_path):
        doc = fitz.open(pdf_path)
        regex_list = [re.compile(pattern, re.IGNORECASE) for pattern in regex_patterns]

        for page_num in range(1, len(doc)):
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
                doc.save(highlighted_pdf_path)
                print(f"Highlighted PDF saved at: {highlighted_pdf_path}")
                return page_num

        print(f"No matches for regex patterns {regex_patterns} found in the PDF.")
        return None
    
    def detect_highlight_and_crop(self, image_path,output_image_path):
        """
        Detect the highlighted text region in the image and crop the area below it.
        :param image_path: Path to the input image.
        :return: Paths to the cropped image and marked image.
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

        center_x = x + w // 2
        center_y = y + h // 2
        cv2.circle(image, (center_x, center_y), radius=10, color=(255, 0, 0), thickness=-1)

        crop_x_start = max(0, x - self.x_padding)
        crop_x_end = min(image.shape[1], x + w + self.x_padding)
        crop_y_start = y + h
        crop_y_end = min(image.shape[0], crop_y_start + self.crop_height)
        cropped_image = image[crop_y_start:crop_y_end, crop_x_start:crop_x_end]

        marked_output_path = "marked_" + output_image_path
        cv2.imwrite(marked_output_path, image)
        print(f"Marked image saved at: {marked_output_path}")

        cv2.imwrite(output_image_path, cropped_image)
        print(f"Cropped image saved at: {output_image_path}")
        if os.path.exists(marked_output_path):
                # print(file_path)
                os.remove(marked_output_path)
        return output_image_path

    def process(self,temp_image_path,regex_patterns,highlighted_pdf_path,output_image_path):
        """
        Orchestrates the entire process of highlighting, cropping, and saving results.
        """
        page_num = self.highlight_text_with_regex(self.pdf_path,regex_patterns,highlighted_pdf_path)
        if page_num is not None :
            images = convert_from_path(highlighted_pdf_path, first_page=page_num + 1, last_page=page_num + 1)
            images[0].save(temp_image_path)
            output = self.detect_highlight_and_crop(temp_image_path,output_image_path)
            os.remove(highlighted_pdf_path)
            os.remove(temp_image_path)
            # print(output)
            return output
        
        
        
# if __name__ == "__main__":
#     pdf_path = 'https://kanpur-tavivision-v1.s3.ap-south-1.amazonaws.com/pdfs/900e7007-2d95-4fae-84c8-34723739bd2c.pdf'
#     regex_patterns = [r'ICD @4mm', r'Inter commisural distance @4mm', r'ICD @ 4mm']
    
#     processor = PDFHighlighterAndCropper(pdf_url=pdf_path)
    
#     highlighted_pdf_path = 'highlighted_pdf.pdf'
#     temp_image_path = 'temp_page_image.png'
#     output_path = 'output_image.png'
#     cropped_image_path = processor.process(
#         temp_image_path=temp_image_path,
#         regex_patterns=regex_patterns,
#         highlighted_pdf_path=highlighted_pdf_path,
#         output_image_path=output_path
#     )
    
    # if cropped_image_path:
    #     print(f"Cropped image saved at: {cropped_image_path}")