import cloudinary
import cloudinary.uploader

class CloudinaryUploader:
    def __init__(self, file_path = 'output_image.png'):
        """
        Initializes the CloudinaryUploader with the necessary credentials and uploads the file.
        :param cloud_name: Cloudinary cloud name.
        :param api_key: Cloudinary API key.
        :param api_secret: Cloudinary API secret.
        :param file_path: Path to the local file to upload.
        """
        cloudinary.config(
            cloud_name = 'ddiv6zknz',
            api_key = '583371225574577',
            api_secret = 'noZQfCIf3fvBaV-fEAa0PSqolt4'
        )
        self.file_url = self.upload_file(file_path)

    def upload_file(self, file_path):
        """
        Uploads a file to Cloudinary and returns the file URL.
        :param file_path: Path to the local file.
        :return: URL of the uploaded file.
        """
        try:
            response = cloudinary.uploader.upload(file_path, resource_type='raw', format = 'N/A')
            file_url = response.get('url')
            print(f"File uploaded successfully to Cloudinary: {file_url}")
            return file_url
        except Exception as e:
            print(f"Error uploading file to Cloudinary: {e}")
            return None


# if __name__ == "__main__":
#       # Replace with your file path

#     uploader = CloudinaryUploader()
#     print(f"Uploaded File URL: {uploader.file_url}")