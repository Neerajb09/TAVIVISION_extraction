from flask import Flask, request, jsonify
import time
import os
from src.pdf.valueExtraction import PDFExtractor # for extracting the values from the pdf 
from src.logics import ConditionEvaluator # for evaluating the the condition for generating the report
from src.image.ICD import PDFHighlighterAndCropper # crop the image label ICD and crop and highlight the area below it # not used in below code 
from src.image.valueFromImage import YellowShadeOCR 
from src.image.calcificationImage import Calcification_image 
from src.image.fineTuneImage import ImageProcessor
from src.upload.s3 import S3Uploader
import uuid
import torch
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import logging
os.environ["CUDA_VISIBLE_DEVICES"] = "1"  


app = Flask(__name__)


@app.route('/ping', methods=['GET'])
def ping():
    return {"status": "Healthy"}


@app.route('/invocations', methods=['POST'])
def handle_request():
    """
    AWS SageMaker inference endpoint that supports multiple tasks.
    Expects JSON input with a `task` parameter.
    """
    data = request.json

    # Validate input
    if "task" not in data:
        return jsonify({"error": "Missing 'task' parameter"}), 400

    task = data["task"]

    if task == "extract_pdf":
        return extract_pdf()
    elif task == "fetch_report":
        return fetch_report()
    elif task == "check-hardware":
        return check_hardware()
    else:
        return jsonify({"error": "Invalid task type"}), 400
    
def check_hardware():
    gpu_available = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if gpu_available else 0
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else "No GPU"

    return {
        "GPU Available": gpu_available,
        "GPU Count": gpu_count,
        "GPU Name": gpu_name,
        "Processor": "GPU" if gpu_available else "CPU"
    }

    
def extract_pdf():
    """
    API endpoint to extract values from a PDF URL.
    Expects a JSON payload with 'pdf_url'.
    """
    unique_id = str(uuid.uuid4())
	
    data = request.json
    if not data or 'pdf_url' not in data:
        return jsonify({"error": "Invalid request. 'pdf_url' is required."}), 400

    pdf_url = data['pdf_url']
    start_time = time.time()

    try:
        # Initialize the PDFExtractor with the given URL
        
        report_extractor = PDFExtractor(pdf_url=pdf_url, unique_id=unique_id)
        output_pdf_path = unique_id+'.pdf'
        extracted_values = report_extractor.run_extraction(output_pdf_path=output_pdf_path)
        icd_values = {}
        
        def process_icd(image_suffix, regex_patterns, s3_folder):
            output_image_path = f"{unique_id}_{image_suffix}.png"
            temp_image_path = f"{unique_id}temp_image_path_{image_suffix}.png"
            highlighted_pdf_path = f"{unique_id}highlighted_pdf_{image_suffix}.pdf"

            # Create a new instance inside the function to ensure thread safety
            gg = PDFHighlighterAndCropper(pdf_url)
            gg.process(temp_image_path=temp_image_path, regex_patterns=regex_patterns, highlighted_pdf_path=highlighted_pdf_path, output_image_path=output_image_path)

            # Run YellowShadeOCR in parallel
            with ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(YellowShadeOCR().run, output_image_path, f"{unique_id}_yellow_shade_{image_suffix}.png")
                value = future.result()  # Wait for the result
                    
            ImageProcessor().crop_center_contour(image_path=output_image_path, output_path=output_image_path)
                
            file_url = S3Uploader(s3_folder=f'TAVIVision/{s3_folder}', file_path=output_image_path).file_url
            
            if(value != -1):    
                return {f'{image_suffix}Img': file_url, image_suffix: value}
            else:
                return {f'{image_suffix}Img': file_url, image_suffix: "Image Not Found"}
            
        if(extracted_values["Aortic Valve Anatomy Type"] is not None):                    
            if 'bicuspid' in extracted_values["Aortic Valve Anatomy Type"].lower():
                icd_tasks = [
                    ('icd4mm', [r'ICD @4mm', r'Inter commisural distance @4mm', r'ICD @ 4mm',r'ICD\s*4\s*mm',r"(?i)(?<![A-Za-z])((?:ICD|Inter[\s-]?commiss?ural[\s-]?distance)){e<=1}\s*[:@-]?\s*4(?:[.,]\d+)?\s*mm(?![A-Za-z])"], 'icd4mm'),
                    ('icd6mm', [r'ICD @6mm', r'Inter commisural distance @6mm', r'ICD @ 6mm',r'ICD\s*6\s*mm',r"(?i)(?<![A-Za-z])((?:ICD|Inter[\s-]?commiss?ural[\s-]?distance)){e<=1}\s*[:@-]?\s*6(?:[.,]\d+)?\s*mm(?![A-Za-z])"], 'icd6mm'),
                    ('icd8mm', [r'ICD @8mm', r'Inter commisural distance @8mm', r'ICD @ 8mm',r'ICD\s*8\s*mm',r"(?i)(?<![A-Za-z])((?:ICD|Inter[\s-]?commiss?ural[\s-]?distance)){e<=1}\s*[:@-]?\s*8(?:[.,]\d+)?\s*mm(?![A-Za-z])"], 'icd8mm')
                ]

                num_workers = 30
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    results = executor.map(lambda args: process_icd(*args), icd_tasks)    
                for result in results:
                    if(result is not None):
                        icd_values.update(result)
                    

        icd_values['aorticValveCalcificationImage'] = extracted_values['aorticValveCalcificationImage']
        del extracted_values['aorticValveCalcificationImage']
        end_time = time.time()
        execution_time = end_time - start_time


        # Return the extracted values as a JSON response
        return jsonify({
            "status": "success",
            "extracted_values": extracted_values,
            "icd_values": icd_values,
            "execution_time": f"{execution_time:.2f} seconds"
        })

    except Exception as e:
        # Handle errors
        return jsonify({"error": str(e)}), 500

def fetch_report():
    data = request.json['report']
    # print(data)
    evaluator = ConditionEvaluator(data)
    results_table = evaluator.generate_results_table()

    # Convert DataFrame to a list of dictionaries
    # results_json = results_table.to_dict(orient='records')
    return jsonify({"results": results_table})


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    multiprocessing.set_start_method('spawn', force=True)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)


