# Imports
import os
from pathlib import Path
import fitz  # PyMuPDF
import json
import re
import unicodedata

def setup_output_structure(pdf_name, display_path=False):
    """
    Create the output folder structure for a given PDF as follows:
    ./outputs/<pdf_name>/
        - raw_text.txt
        - chunks.json
        - questions.json
        - run_metadata.json
    """
    base_output = Path("./outputs") / pdf_name
    base_output.mkdir(parents=True, exist_ok=True)

    raw_text_file = base_output / "raw_text.txt"
    
    output_paths = {
        "base": base_output,
        "raw_text": raw_text_file,
        "chunks_json": base_output / "chunks.json",
        "questions_json": base_output / "questions.json",
        "metadata_json": base_output / "run_metadata.json"
    }

    if display_path:
        print(f"\nOutput structure will be created as follows: {output_paths['base']}")
        print(f"  - raw_text.txt: {output_paths['raw_text']}")
        print(f"  - chunks.json: {output_paths['chunks_json']}")
        print(f"  - questions.json: {output_paths['questions_json']}")
        print(f"  - run_metadata.json: {output_paths['metadata_json']}")
        print('\n')
    
    return output_paths

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    """
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)
    doc.close()

    return "\n\n".join(pages_text)
    

def clean_text(text):
    """
    Minimal cleaning for PDF-extracted text.

    What this does:
    1. Unicode normalization (fixes ligatures like ﬁ, ﬀ, etc.)
    2. Normalize newlines and whitespace
    3. Remove standalone page numbers (e.g., '15', '203')

    What this intentionally does NOT do (may implement later):
    - No header/footer detection
    - No paragraph restructuring
    - No figure/table removal
    - No heuristic guessing
    """

    # 1. Unicode normalization (fix ligatures and weird characters)
    text = unicodedata.normalize("NFKC", text)

    # 2. Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Normalize whitespace (keep line structure)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    # 4. Remove standalone page numbers
    cleaned_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.isdigit() and len(stripped) <= 4:
            continue
        cleaned_lines.append(line)

    # 5. Collapse excessive blank lines (keep max 1)
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()

def chunk_fixed_size(text, chunk_size = 4000, overlap= 400, min_chunk_size = 800):
    """
    Splits text into fixed-size character chunks with overlap.

    Returns:
      List of chunks:
      {
        "chunk_id": int,
        "text": str,
        "char_len": int
      }
    """
    chunks = []
    text_len = len(text)
    chunk_id = 0
    start = 0

    while start < text_len:
        end = start + chunk_size
        chunk_text = text[start:end].strip()

        if len(chunk_text) >= min_chunk_size:
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "char_len": len(chunk_text)
            })
            chunk_id += 1

        # move start forward, keeping overlap
        start += max(1, chunk_size - overlap)

    return chunks


def safe_json_loads(text):
    """
    Ensure result is a JSON object otherwise return first {...} block it can find
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def validate_json(q):
    question_type = q.get("type")
    if question_type != "mcq":
        return "type must be 'mcq'"

    question = q.get("question")
    if not isinstance(question, str) or not question.strip():
        return "missing/invalid question"

    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) != 4 or not all(isinstance(c, str) and c.strip() for c in choices):
        return "choices must be a list of exactly 4 non-empty strings"

    answer = q.get("answer_index")
    if not isinstance(answer, int) or not (0 <= answer <= 3):
        return "answer_index must be an int in [0..3]"

    # Optional explanation
    if "explanation" in q and q["explanation"] is not None and not isinstance(q["explanation"], str):
        return "explanation must be a string if present"

    # Light anti-noise check (optional but helpful)
    bad_markers = ["doi.org", "©", "springer", "page "]
    low_q = question.lower()
    if any(m in low_q for m in bad_markers):
        return "question looks like it used PDF boilerplate"

    return None