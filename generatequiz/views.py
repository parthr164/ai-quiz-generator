from django.http import HttpResponse
from pathlib import Path
from django.conf import settings
from django.http import Http404, FileResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .services.pipeline import generate_quiz
import json
import uuid


def home(request):
    return HttpResponse("Welcome to the AI Quiz Generator!")


def _quiz_dir(quiz_id):
    return Path(settings.MEDIA_ROOT) / "quizzes" / quiz_id


def _load_questions(quiz_id):
    path = _quiz_dir(quiz_id) / "questions.json"
    if not path.exists():
        raise Http404("Quiz not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@require_http_methods(["GET", "POST"])
def upload_view(request):
    if request.method == "GET":
        return render(request, "upload.html")

    pdf_file = request.FILES.get("pdf")
    if not pdf_file:
        return render(request, "upload.html", {"error": "Please upload a PDF."})

    try:
        num_questions = int(request.POST.get("num_questions", "10"))
    except ValueError:
        num_questions = 10
    num_questions = max(1, min(num_questions, 50))

    quiz_id = str(uuid.uuid4())
    qdir = _quiz_dir(quiz_id)
    qdir.mkdir(parents=True, exist_ok=True)

    # Save uploaded PDF
    pdf_path = qdir / "source.pdf"
    with open(pdf_path, "wb") as f:
        for chunk in pdf_file.chunks():
            f.write(chunk)

    # Run generation (sync MVP)
    generate_quiz(pdf_path=pdf_path, quiz_dir=qdir, num_questions=num_questions)

    return redirect("quiz", quiz_id=quiz_id)


@require_http_methods(["GET"])
def quiz_view(request, quiz_id):
    questions = _load_questions(quiz_id)
    return render(request, "quiz.html", {"quiz_id": quiz_id, "questions": questions})

@require_http_methods(["POST"])
def submit_view(request, quiz_id):
    questions = _load_questions(quiz_id)

    # Collect answers
    total = len(questions)
    correct = 0
    detailed = []

    for q in questions:
        qid = q["question_id"]
        user_choice = request.POST.get(f"q_{qid}")  # value is choice index as str
        user_choice_idx = int(user_choice) if user_choice is not None and user_choice.isdigit() else None

        is_correct = (user_choice_idx is not None) and (user_choice_idx == q.get("answer_index"))
        if is_correct:
            correct += 1

        detailed.append({
            "question": q["question"],
            "choices": q["choices"],
            "user_choice_idx": user_choice_idx,
            "answer_index": q.get("answer_index"),
            "answer": q.get("answer"),
            "explanation": q.get("explanation", ""),
            "is_correct": is_correct,
        })

    score_pct = round((correct / total) * 100, 1) if total else 0.0

    return render(request, "results.html", {
        "quiz_id": quiz_id,
        "total": total,
        "correct": correct,
        "score_pct": score_pct,
        "detailed": detailed,
    })


@require_http_methods(["GET"])
def download_questions_view(request, quiz_id):
    path = _quiz_dir(quiz_id) / "questions.json"
    if not path.exists():
        raise Http404("Quiz not found.")
    return FileResponse(open(path, "rb"), as_attachment=True, filename="questions.json")
