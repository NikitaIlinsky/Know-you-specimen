"""FastAPI server for the Know Your Specimen image analysis API."""

import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.know_your_specimen.config import config
from src.know_your_specimen.segmentation.talk_percentage import process_file

app = FastAPI(title="Know Your Specimen API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    """Upload a specimen image, run talc-detection analysis, return stats + artifact URLs.

    Accepts a multipart file upload and returns a JSON response containing
    segmentation statistics and URLs to the generated output artifacts
    (annotated image, binary mask, and stats JSON).
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="No filename provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in config.allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(config.allowed_extensions)}",
        )

    # Save uploaded file with a unique name to avoid collisions
    unique_id = uuid.uuid4().hex[:12]
    safe_name = f"{unique_id}{ext}"
    temp_path = os.path.join(config.output_dir, safe_name)

    os.makedirs(config.output_dir, exist_ok=True)
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {exc}")

    # Run the existing analysis pipeline
    try:
        stats = process_file(temp_path, config.output_dir, config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
    finally:
        # Always clean up the temporary input file
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if stats is None:
        raise HTTPException(
            status_code=422,
            detail="Failed to process image: file is unreadable or invalid.",
        )

    base = os.path.splitext(safe_name)[0]
    return {
        "stats": stats,
        "artifacts": {
            "annotated_image": f"/api/v1/output/{base}_talk.jpg",
            "mask_image": f"/api/v1/output/{base}_talk_mask.png",
            "stats_json": f"/api/v1/output/{base}_talk_stats.json",
        },
    }


@app.get("/api/v1/output/{filename}")
async def get_output(filename: str) -> FileResponse:
    """Serve a generated artifact file from the output directory."""
    file_path = os.path.join(config.output_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)
