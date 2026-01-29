import boto3
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file


# dotenv_path = "DoCker/.env"
load_dotenv()

# Configure AWS credentials and S3 bucket
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID_TV")
print(AWS_ACCESS_KEY)
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY_TV")
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_TV")
AWS_REGION = os.getenv("AWS_S3_REGION_TV", "ap-south-1")
# print(AWS_ACCESS_KEY)

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

class S3Uploader:
    def __init__(self, s3_folder,file_path,  content_type='application/octet-stream'):
        """
        Initializes the S3Uploader with the necessary credentials and uploads the file.
        """
        self.file_url = self.upload_file(file_path, s3_folder, content_type)

    def upload_file(self, file_path, s3_folder, content_type):
        """Uploads a file to AWS S3 and returns the file URL."""
        object_name = os.path.join(s3_folder, os.path.basename(file_path))
        try:
            s3_client.upload_file(
                file_path, S3_BUCKET_NAME, object_name,
                ExtraArgs={'ContentType': content_type}
            )
            file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
            print(f"File uploaded successfully to S3: {file_url}")
            if os.path.exists(file_path):
                print(file_path)
                os.remove(file_path)
            return file_url
        except FileNotFoundError:
            print("The file was not found.")
            return None
        except NoCredentialsError:
            print("Credentials not available.")
            return None
        except PartialCredentialsError:
            print("Incomplete credentials provided.")
            return None
        except Exception as e:
            print(f"Error uploading file to S3: {e}")
            return None

# Example usage
# a = S3Uploader(s3_folder= 'TAVIVision/calcificaltion_image',file_path="/mnt/nvme_disk2/User_data/nb57077k/cardiovision/phase1/output_highlighted_t.pdf", content_type='image/png')
# print(a.file_url)
