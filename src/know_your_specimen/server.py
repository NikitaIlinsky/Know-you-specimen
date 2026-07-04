"""FastAPI server for the Know Your Specimen image analysis API."""

import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from know_your_specimen.config import config
from know_your_specimen.segmentation.talk_percentage import process_file

app = FastAPI(title="Know Your Specimen API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        stats = process_file(temp_path, config)
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


# ---------------------------------------------------------------------------
# Static file serving for the Vue.js frontend (production mode)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_STATIC_DIR = os.path.join(_PROJECT_ROOT, "frontend", "dist")

if os.path.isdir(_STATIC_DIR):
    # Mount /assets so Vite-built JS/CSS are served correctly
    assets_dir = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def _favicon() -> FileResponse:
        """Serve favicon from the Vue build output."""
        path = os.path.join(_STATIC_DIR, "favicon.ico")
        if os.path.isfile(path):
            return FileResponse(path)
        raise HTTPException(status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _serve_spa(full_path: str) -> FileResponse:
        """Catch-all that serves index.html for SPA client-side routing.

        Only reached when no API route matches the path.
        """
        index_path = os.path.join(_STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")
