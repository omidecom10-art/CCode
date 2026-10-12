from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from models.schemas import WatermarkRegion
from tools.video_editor import extract_frames, frames_to_video
from utils.file_helpers import ensure_output_dir, temp_dir


def detect_watermark_regions(
    image_path: str,
    search_area: str = "corners",
) -> list[WatermarkRegion]:
    """Detect likely watermark regions using edge detection and contour analysis.

    search_area: 'corners' (logo watermarks), 'bottom' (subtitles), 'all'
    """
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if search_area == "bottom":
        roi_y = int(h * 0.80)
        roi = gray[roi_y:, :]
        offset_y = roi_y
    elif search_area == "corners":
        regions = []
        corner_h, corner_w = int(h * 0.2), int(w * 0.3)
        corners = [
            (0, 0, corner_w, corner_h),
            (w - corner_w, 0, corner_w, corner_h),
            (0, h - corner_h, corner_w, corner_h),
            (w - corner_w, h - corner_h, corner_w, corner_h),
        ]
        for cx, cy, cw, ch in corners:
            roi = gray[cy:cy + ch, cx:cx + cw]
            found = _detect_in_roi(roi, cx, cy)
            regions.extend(found)
        return regions
    else:
        roi = gray
        offset_y = 0

    return _detect_in_roi(roi, 0, offset_y)


def _detect_in_roi(roi: np.ndarray, offset_x: int, offset_y: int) -> list[WatermarkRegion]:
    edges = cv2.Canny(roi, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    dilated = cv2.dilate(edges, kernel, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    roi_area = roi.shape[0] * roi.shape[1]
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < roi_area * 0.005 or area > roi_area * 0.5:
            continue
        confidence = min(1.0, area / (roi_area * 0.05))
        regions.append(WatermarkRegion(
            x=x + offset_x, y=y + offset_y,
            width=w, height=h, confidence=round(confidence, 2),
        ))
    return regions


def detect_subtitles(image_path: str) -> list[WatermarkRegion]:
    """Detect subtitle text in the bottom portion of an image."""
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    roi_y = int(h * 0.75)
    roi = img[roi_y:, :]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < w * 0.1 or bh < 10:
            continue
        regions.append(WatermarkRegion(
            x=x, y=y + roi_y, width=bw, height=bh, confidence=0.8,
        ))
    return regions


def remove_watermark_inpaint(
    image_path: str,
    regions: list[WatermarkRegion],
    output_path: str,
    radius: int = 5,
    method: str = "telea",
) -> str:
    """Remove watermarks/subtitles using OpenCV inpainting."""
    img = cv2.imread(image_path)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)

    padding = 5
    for r in regions:
        x1 = max(0, r.x - padding)
        y1 = max(0, r.y - padding)
        x2 = min(img.shape[1], r.x + r.width + padding)
        y2 = min(img.shape[0], r.y + r.height + padding)
        mask[y1:y2, x1:x2] = 255

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    result = cv2.inpaint(img, mask, radius, flag)
    cv2.imwrite(output_path, result)
    return output_path


def remove_watermark_from_region(
    image_path: str,
    output_path: str,
    x: int, y: int, width: int, height: int,
    radius: int = 5,
) -> str:
    """Remove watermark from a manually specified region."""
    region = WatermarkRegion(x=x, y=y, width=width, height=height, confidence=1.0)
    return remove_watermark_inpaint(image_path, [region], output_path, radius)


def remove_subtitles_from_image(image_path: str, output_path: str) -> str:
    """Auto-detect and remove subtitles from an image."""
    regions = detect_subtitles(image_path)
    if not regions:
        Image.open(image_path).save(output_path)
        return output_path
    return remove_watermark_inpaint(image_path, regions, output_path)


def remove_watermark_from_video(
    input_path: str,
    output_path: str,
    regions: list[WatermarkRegion] | None = None,
    search_area: str = "corners",
    sample_fps: int = 1,
    process_fps: int = 30,
) -> str:
    """Remove watermarks from a video by processing frames."""
    with temp_dir() as tmp:
        frames_dir = str(tmp / "frames")
        processed_dir = str(tmp / "processed")
        Path(frames_dir).mkdir()
        Path(processed_dir).mkdir()

        frames = extract_frames(input_path, frames_dir, fps=process_fps)
        if not frames:
            raise ValueError("No frames extracted from video")

        if regions is None:
            sample_frames = extract_frames(input_path, str(tmp / "samples"), fps=sample_fps)
            all_regions = []
            for sf in sample_frames[:5]:
                all_regions.extend(detect_watermark_regions(sf, search_area))
            if not all_regions:
                raise ValueError("No watermark regions detected")
            regions = _merge_regions(all_regions)

        for frame_path in frames:
            out = str(Path(processed_dir) / Path(frame_path).name)
            remove_watermark_inpaint(frame_path, regions, out)

        return frames_to_video(processed_dir, output_path, fps=process_fps, audio_source=input_path)


def remove_subtitles_from_video(
    input_path: str,
    output_path: str,
    process_fps: int = 30,
) -> str:
    """Auto-detect and remove subtitles from a video."""
    with temp_dir() as tmp:
        sample_dir = str(tmp / "samples")
        Path(sample_dir).mkdir()
        samples = extract_frames(input_path, sample_dir, fps=1)

        all_regions = []
        for sf in samples[:5]:
            all_regions.extend(detect_subtitles(sf))

        if not all_regions:
            raise ValueError("No subtitle regions detected")

        regions = _merge_regions(all_regions)
        return remove_watermark_from_video(input_path, output_path, regions, process_fps=process_fps)


def _merge_regions(regions: list[WatermarkRegion]) -> list[WatermarkRegion]:
    """Merge overlapping regions into a consistent mask."""
    if not regions:
        return []
    xs = [r.x for r in regions]
    ys = [r.y for r in regions]
    x2s = [r.x + r.width for r in regions]
    y2s = [r.y + r.height for r in regions]
    return [WatermarkRegion(
        x=min(xs), y=min(ys),
        width=max(x2s) - min(xs),
        height=max(y2s) - min(ys),
        confidence=max(r.confidence for r in regions),
    )]
