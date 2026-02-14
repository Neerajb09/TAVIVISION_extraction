import requests
import concurrent.futures
import time

URL = "http://3.109.76.49:8000/invocations"

payload = {
    "task": "extract_pdf",
    "pdf_url": "https://tavivision.s3.ap-south-1.amazonaws.com/pdfs/Bicuspid1a+report_ECG_PS49SE014_Landmark_Corelab+1.pdf"
}

def send_request(i):
    start = time.time()
    try:
        r = requests.post(URL, json=payload, timeout=120)
        return i, r.status_code, time.time() - start
    except Exception as e:
        return i, "ERROR", str(e)

# 🔥 Change workers for concurrency
CONCURRENT_USERS = 10   # 10 requests in parallel

with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
    futures = [executor.submit(send_request, i) for i in range(10)]

    for f in concurrent.futures.as_completed(futures):
        print(f.result())
