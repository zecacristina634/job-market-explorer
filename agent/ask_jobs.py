import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

JOBS_PATH = "data/processed/jobs_clean.json"

def load_jobs():
    with open(JOBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def format_jobs_for_context(jobs, max_jobs=100):
    """Transformarea listei de joburi in text simplu"""
    lines =[]
    for job in jobs[:max_jobs]:
        skills = ", ".join(job.get("extracted_skills", [])) or "N/A"
        lines.append(
            f"- {job.get('title')} @ {job.get('company')} | "
            f"Categorie: {job.get('category')} | "
            f"Salariu: {job.get('salary') or 'N/A'} | "
            f"Skill-uri: {skills} | "
            f"Locatie: {job.get('location')}"
        )
    return "\n".join(lines)

def ask(question: str) -> str:
    jobs = load_jobs()
    context = format_jobs_for_context(jobs)

    prompt =f"""Esti un asistent care raspunde la intrebari despre o lista de joburi tech.
    Foloseste STRICT informatiile din lista de mai jos pentru a raspunde.
    Daca informatia nu se gaseste in lista, spune clar ca nu ai date suficiente.
    
    Lista de joburi:
    {context}

    Intrebare: {question}

    Raspunde clar si concis, in limba romana, bazandu-te doar pe datele de mai sus."""

    response = llm.invoke(prompt)
    return response.content.strip()


if __name__ =="__main__":
    print("Job Market Explorer - Asistent Q&A")
    print("Scrie o intrebare despre joburile procesate (sau 'exit' pentru a iesi)\n")

    while True:
        question = input("Intrebarea ta: ").strip()
        if question.lower() in ("exit", "quit", "iesire"):
            break
        if not question:
            continue

        answer = ask(question)
        print(f"\nRaspuns: {answer}\n")