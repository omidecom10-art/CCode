from __future__ import annotations

from pathlib import Path

from utils.file_helpers import ensure_output_dir
from utils.llm import call_complex

CODEGEN_SYSTEM = """You are a Python script generator for an ad creative automation system.
Generate clean, self-contained Python scripts that accomplish the user's goal.

Available packages in the environment:
- opencv-python-headless (cv2)
- Pillow (PIL)
- subprocess (for FFmpeg commands)
- Standard library (os, json, pathlib, etc.)

Rules:
- Scripts must be self-contained and runnable
- Use FFmpeg via subprocess for video operations
- Use OpenCV or Pillow for image operations
- Include proper error handling
- Print progress to stdout
- Accept input/output paths as variables at the top of the script
- Never use external APIs or network requests unless explicitly asked

Output ONLY the Python code, no markdown fences or explanation."""


def generate_script(description: str, context: dict | None = None) -> str:
    """Generate a Python script using Claude Sonnet (expensive model).

    This is the ONLY function that uses the expensive model.
    Cost: ~$0.03-0.05 per call.
    """
    prompt = f"Generate a Python script that does the following:\n\n{description}"
    if context:
        prompt += f"\n\nAdditional context:\n{context}"

    code = call_complex(
        system=CODEGEN_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def generate_and_save(description: str, filename: str | None = None, context: dict | None = None) -> str:
    """Generate a script and save it to the output/scripts directory."""
    code = generate_script(description, context)

    scripts_dir = ensure_output_dir("scripts")
    if not filename:
        existing = list(scripts_dir.glob("script_*.py"))
        num = len(existing) + 1
        filename = f"script_{num:03d}.py"

    path = scripts_dir / filename
    path.write_text(code)
    return str(path)
