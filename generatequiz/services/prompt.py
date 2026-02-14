
def build_question_prompt(chunk_text, num_questions=10):
    '''
    Generate a prompt for creating quiz questions from a text chunk.
    '''
    
    return f"""
    You are an expert at creating quiz questions that test deep understanding of the material. 
Generate {num_questions} quiz questions of easy difficulty based on the following excerpt. 
The excerpt may contain PDF artifacts (page numbers, figure labels, axis ticks, glossary/margin terms, broken line wraps).
Ignore non-explanatory artifacts and focus on the conceptual content. 

Each question should have 4 answer options with only one correct answer. 
The questions should require critical thinking and not be answerable by simple keyword matching.

Generate {num_questions} total questions and return them in the following format:
{{
    "questions":[
        {{
            "type": "mcq",
            "question_id": 1,
            "question": "What is the main topic of this excerpt?",
            "choices": ["A", "B", "C", "D"],
            "answer_index": 0
        }},

        {{
            "type": "mcq",
            "question_id": 2,
            "question": "What is the main topic of this excerpt?",
            "choices": ["A", "B", "C", "D"],
            "answer_index": 2
        }}
    ]
}}

Rules:
- choices must be exactly 4 items
- answer_index must be an integer 0..3
- questions must be answerable from the given text (no outside knowledge)
- avoid trivial questions (e.g., “What is the chapter number?”)
- keep the answer options concise (less than 10-15 words)
- distribute the right answers fairly evenly among the choices [0,1,2,3]

Excerpt: 
\"\"\"\n{chunk_text}\n\"\"\"
""".strip()


def call_openai_text(client, prompt, model = "gpt-4.1-mini"):
    """
    Call the OpenAI API with a text prompt and return the response text
    """
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.3,
        max_output_tokens=900,
    )
    return resp.output_text.strip()

