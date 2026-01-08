import cv2
import numpy as np

class ImageProcessor:
    def __init__(self):
        # self.crop_center_contour(image_path, output_path)
        self.cropped_image=None
        
    def crop_center_contour(self, image_path, output_path):
        """
        Crops the central contour of the image. If the image is not found, it skips this step.
        
        :param image_path: Path to the input image.
        :param output_path: Path to save the cropped image.
        :return: Path to the cropped image or None if an error occurs.
        """
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Image not found at {image_path}. Skipping cropping step.")
                return None  # Skip this step and continue the next process

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Use edge detection to detect the central region
            edges = cv2.Canny(gray, 50, 150)

            # Find contours in the edges
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                print("No contours found in the image. Skipping cropping step.")
                return None

            largestContour = None
            maxArea = float("-inf")
            for contour in contours:
                # Calculate the bounding box of the contour
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate the contour area
                area = w * h
                if area > maxArea:
                    maxArea = area
                    largestContour = contour

            if largestContour is None:
                print("No valid contour found. Skipping cropping step.")
                return None

            # Get the bounding box of the largest contour
            x, y, w, h = cv2.boundingRect(largestContour)

            # Crop the region
            cropped_image = image[y:y+h, x:x+w]

            # Save the cropped image
            cv2.imwrite(output_path, cropped_image)
            print(f"Cropped image saved at: {output_path}")
            
            return output_path  # Successfully processed image

        except Exception as e:
            print(f"Error in cropping image: {e}. Skipping cropping step.")
            return None  # Allow next process to continue

# Example usage
# image_processor = ImageProcessor()
