from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data")
SUMMARY_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_summary")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_processed")
FEATURE_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_feature")
DATA_ML_DIR = os.path.join(BASE_DIR, "..", "data", "data_ml")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SUMMARY_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(FEATURE_DATA_DIR, exist_ok=True)
os.makedirs(DATA_ML_DIR, exist_ok=True)

def get_next_file_number():
    """Generate the next file number based on existing files in DATA_DIR."""
    existing_files = [f for f in os.listdir(DATA_DIR) if f.startswith('current_') and f.endswith('.csv')]
    if not existing_files:
        return 1
    numbers = [int(f.replace('current_', '').replace('.csv', '')) for f in existing_files]
    return max(numbers) + 1 if numbers else 1

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_number = get_next_file_number()
        new_filename = f"current_{file_number}.csv"
        file_path = os.path.join(DATA_DIR, new_filename)
        logger.info(f"Uploading file as: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return JSONResponse(status_code=200,
                           content={"message": "File uploaded successfully", "filename": new_filename})
    except Exception as e:
        logger.error(f"Error uploading file {file.filename}: {str(e)}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/get_summary")
async def get_summary():
    try:
        logger.info(f"Reading summaries from: {SUMMARY_DATA_DIR}")
        summaries = []
        if not os.path.exists(SUMMARY_DATA_DIR):
            logger.error(f"Summary directory does not exist: {SUMMARY_DATA_DIR}")
            return JSONResponse(status_code=404, content={"message": "Summary directory not found"})

        def _num(name: str) -> int:
            try:
                return int(name.replace("summary_data_", "").replace(".csv", ""))
            except Exception:
                return -1

        files = sorted(
            [f for f in os.listdir(SUMMARY_DATA_DIR) if f.startswith("summary_data_") and f.endswith(".csv")],
            key=_num, reverse=True
        )
        logger.info(f"Found {len(files)} summary files: {files}")

        def safe_get(df, col, default="N/A"):
            if col in df.columns and not df.empty:
                val = df[col].iloc[0]
                if pd.notna(val):
                    return str(val)
            return default

        for filename in files:
            file_path = os.path.join(SUMMARY_DATA_DIR, filename)
            logger.info(f"Processing summary file: {file_path}")
            try:
                df = pd.read_csv(file_path)
                summary = {
                    "filename": filename,
                    "summary_defect":  safe_get(df, "summary_defect"),
                    "summary_severity": safe_get(df, "summary_severity"),
                    "additional_note": safe_get(df, "additional_note"),
                    "analysis_time":   safe_get(df, "analysis_time"),
                }
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Error reading summary file {file_path}: {str(e)}")
                continue

        return JSONResponse(status_code=200, content={"summaries": summaries})
    except Exception as e:
        logger.error(f"Error in get_summary: {str(e)}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/download_summary/{filename}")
async def download_summary(filename: str):
    file_path = os.path.join(SUMMARY_DATA_DIR, filename)
    logger.info(f"Downloading file: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type='text/csv')
    logger.error(f"File not found: {file_path}")
    return JSONResponse(status_code=404, content={"message": "File not found"})

@app.get("/get_uploaded_files")
async def get_uploaded_files():
    try:
        logger.info(f"Reading uploaded files from: {DATA_DIR}")
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        logger.info(f"Found {len(files)} uploaded files: {files}")
        return JSONResponse(status_code=200, content={"files": files})
    except Exception as e:
        logger.error(f"Error in get_uploaded_files: {str(e)}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.delete("/delete_file/{filename}")
@app.delete("/delete_file/{filename}")
async def delete_file(filename: str):
    try:
        file_number = filename.split('_')[-1].replace('.csv', '')
        directories = [
            (DATA_DIR,        f"current_{file_number}.csv"),
            (SUMMARY_DATA_DIR, filename),
            (PROCESSED_DATA_DIR, f"processed_{file_number}.csv"),
            (FEATURE_DATA_DIR,   f"feature_data_{file_number}.csv"),
            (DATA_ML_DIR,        f"ml_data_{file_number}.csv"),  # <-- добавили
        ]
        deleted = False
        for directory, fname in directories:
            file_path = os.path.join(directory, fname)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                deleted = True
        if deleted:
            return JSONResponse(status_code=200, content={"message": f"File {filename} and related files deleted successfully"})
        else:
            logger.error(f"File not found: {filename}")
            return JSONResponse(status_code=404, content={"message": f"File {filename} not found"})
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        return JSONResponse(status_code=500, content={"message": str(e)})

app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "..", "public"), html=True), name="public")