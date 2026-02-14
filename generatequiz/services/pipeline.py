import json
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import uuid
import random

from .prompt import *
from .utils import *

def generate_mcqs_over_chunks(chunks, model = "gpt-4.1-mini", mcqs_per_chunk = 2, max_chunks = None):
    """
    Reads the chunks, generates MCQs, validates them, and saves them
    """

    subset = chunks if max_chunks is None else chunks[:max_chunks]

    # Maintain list of valid and invalid questions/results
    all_valid = []
    all_invalid = []

    client = OpenAI()

    for i, chunk in enumerate(subset, 1):
        prompt = build_question_prompt(chunk["text"], num_questions=mcqs_per_chunk)

        try:
            raw = call_openai_text(client, prompt, model=model)
            data = safe_json_loads(raw)
            qs = data.get("questions", [])

            if not isinstance(qs, list) or len(qs) != mcqs_per_chunk:
                raise ValueError(f"Expected {mcqs_per_chunk} questions, got {len(qs) if isinstance(qs, list) else 'non-list'}")

            for q in qs:
                if not isinstance(q, dict):
                    all_invalid.append({
                        "chunk_id": chunk["chunk_id"],
                        "error": "question is not an object",
                        "raw_value": q
                    })
                    continue

                err = validate_json(q)
                if err:
                    all_invalid.append({
                        "chunk_id": chunk["chunk_id"],
                        "error": err,
                        "raw_value": q
                    })
                    continue

                q_out = dict(q)
                q_out["question_id"] = str(uuid.uuid4())
                q_out["chunk_id"] = chunk["chunk_id"]
                # convenience field
                q_out["answer"] = q_out["choices"][q_out["answer_index"]]
                all_valid.append(q_out)

            print(f"[{i}/{len(subset)}] chunk_id={chunk['chunk_id']} ✓ valid so far={len(all_valid)} invalid so far={len(all_invalid)}")

        except Exception as e:
            all_invalid.append({
                "chunk_id": chunk["chunk_id"],
                "error": f"generation/parsing failed: {e}",
                "raw_value": None
            })
            print(f"[{i}/{len(subset)}] chunk_id={chunk['chunk_id']} ✗ failed: {e}")

    return all_valid

def generate_quiz(pdf_path, quiz_dir, num_questions):
    
    quiz_dir.mkdir(parents=True, exist_ok=True)

    quiz_pdf_path = quiz_dir / "source.pdf"
    if pdf_path != quiz_pdf_path:
        quiz_pdf_path.write_bytes(Path(pdf_path).read_bytes())

    # Extract text from PDF
    pages = extract_text_from_pdf(quiz_pdf_path)

    # Text cleaning
    text_cleaned = clean_text(pages)

    # Text chunking
    text_chunked = chunk_fixed_size(text_cleaned, chunk_size=4000, overlap=400, min_chunk_size=800)

    # Prompt + validation
    result = generate_mcqs_over_chunks(text_chunked, model="gpt-4.1-mini", mcqs_per_chunk=2, max_chunks=10)

    questions = []
    completed_questions = set()
    for num in range(num_questions):
        
        # Randomize questions and ensure we don't repeat questions
        i = random.randint(0, len(result)-1)
        while i in completed_questions:
            i = random.randint(0, len(result)-1)
        completed_questions.add(i)

        questions.append({
            "question_id": str(uuid.uuid4()),
            "chunk_id": result[i]['chunk_id'],
            "type": "mcq",
            "question": result[i]["question"],
            "choices": result[i]["choices"],
            "answer_index": result[i]["answer_index"],
            "answer": result[i]["answer"],
            "explanation": ""
        })

    # ---- 3) Save artifacts
    questions_path = quiz_dir / "questions.json"
    questions_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

    metadata = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "num_questions": len(questions),
        "source_pdf": str(pdf_path),
        "questions_path": str(questions_path),
    }
    metadata_path = quiz_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "questions_path": str(questions_path),
        "metadata_path": str(metadata_path),
        "num_questions": len(questions),
    }