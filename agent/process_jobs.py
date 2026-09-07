import json
import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

load_dotenv()

CATEGORII =[
    "Data / AI",
    "Backend",
    "Frontend",
    "Full-Stack",
    "DevOps / Infrastructure",
    "QA / Testing",
    "Product / Project Management",
    "Design",
    "Marketing / Content",
    "Other",
]

TECH_KEYWORDS = [
    "developer", "engineer", "engineering", "software", "data", "python",
    "javascript", "backend", "frontend", "full-stack", "fullstack",
    "devops", "cloud", "api", "database", "sql", "ai", "ml", "machine learning",
    "programmer", "coding", "technical", "it ", "qa", "test automation",
    "product manager", "ux", "ui", "design", "golang", "java", "react",
    "node", "aws", "infrastructure", "security", "cyber", "analyst",
]

NON_TECH_KEYWORDS = [
    "porter", "barber", "waiter", "waitress", "kitchen", "chef", "cook",
    "driver", "cashier", "retail", "store manager", "shop assistant",
    "housekeeping", "room attendant", "meat department", "optometrist",
    "labourer", "manufacturing", "machinist", "estimator", "surveyor",
    "valuer", "payroll", "loss prevention", "customer support driver",
]

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

class JobState(TypedDict):
    jobs: List[dict]

def filter_tech_jobs(state: JobState) -> JobState:
    """Nod 0: eliminarea joburilor care nu sunt din domeniul tech"""
    filtered_jobs =[]
    removed_count =0

    for job in state["jobs"]:
        title_lower =job.get("title", "").lower()
        tags_lower =job.get("tags", "").lower()
        combined_text =f"{title_lower} {tags_lower}"

        has_non_tech = any(kw in combined_text for kw in NON_TECH_KEYWORDS)
        has_tech = any(kw in combined_text for kw in TECH_KEYWORDS)

        if has_non_tech and not has_tech:
            removed_count += 1
            continue

        filtered_jobs.append(job)

    print(f"Filtrare: {removed_count} joburi non-tech eliminate, {len(filtered_jobs)} ramase")
    return {"jobs": filtered_jobs}

def clean_tags(state: JobState) -> JobState:
    """Nod 1: normalizarea tag-urilor fiecarui job."""
    cleaned_jobs =[]

    for job in state["jobs"]:
        raw_tags =job.get("tags", "")
        tag_list = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        unique_tags =list(dict.fromkeys(tag_list))

        new_job = job.copy()
        new_job["tags"] =unique_tags
        cleaned_jobs.append(new_job)

    return {"jobs": cleaned_jobs}

def classify_job(state: JobState) -> JobState:
    """Nod 2: clasificarea fiecarui job cu gpt"""
    classified_jobs =[]

    for job in state["jobs"]:
        title= job.get("title", "")
        tags =", ".join(job.get("tags", []))

        prompt = f"""Esti un clasificator de joburi tech. Alege EXACT o categorie din aceasta lista, fara alte explicatii: {", ".join(CATEGORII)}
    Titlul jobului: {title}
    Tag-uri: {tags}

    Raspunde doar cu numele categoriei, exact cum apare in lista."""

        response = llm.invoke(prompt)
        category = response.content.strip()

        if category not in CATEGORII:
            category= "Other"

        new_job = job.copy()
        new_job["category"] = category
        classified_jobs.append(new_job)

        print(f"  {title[:40]:40} -> {category}")

    return {"jobs": classified_jobs}

def recheck_other(state: JobState) -> JobState:
    """Nod 3: verificarea joburilor 'Other' folosind descrierea completa"""
    rechecked_jobs =[]
    changed_count=0

    for job in state["jobs"]:
        if job.get("category") != "Other":
            rechecked_jobs.append(job)
            continue

        description = job.get("description", "")[:1000]
        title = job.get("title", "")

        prompt =f"""Esti un clasificator de joburi tech. Analizeaza cu atentie titlul si descrierea de mai jos.
        Alege EXACT o categorie din aceasta lista, fara alte explicatii:
        {",".join(CATEGORII)}

        Titlul jobului: {title}
        Descriere: {description}
        
        Daca jobul NU are nicio legatura cu tehnologia/IT, raspunde cu 'Other'.
        Raspunde doar cu numele categoriei, exact cum apare in lista."""

        response = llm.invoke(prompt)
        new_category = response.content.strip()

        if new_category not in CATEGORII:
            new_category = "Other"

        new_job = job.copy()
        if new_category !="Other":
            changed_count += 1;
        new_job["category"] = new_category
        rechecked_jobs.append(new_job)

    print(f"Recheck: {changed_count} joburi reclasificate pe baza descrierii.")
    return {"jobs": rechecked_jobs}

def report_uncategorized(state: JobState) -> JobState:
    """Nod 4: eliminarea joburilor clasificate ca 'Other' dupa verificare"""
    kept_jobs = [job for job in state["jobs"] if job.get("category")!="Other"]
    removed_count = len(state["jobs"]) -len(kept_jobs)
    print(f"Filtrare: {removed_count} joburi non-tech eliminate.")
    return {"jobs": kept_jobs}

def validate(state: JobState) -> JobState:
    """Nod 5: verificarea fiecarui job pentru date esentiale lipsa"""
    validated_jobs = []
    incomplete_count =0

    required_fields = ["title" , "company", "category"]

    for job in state["jobs"]:
        is_complete= all(job.get(field) for field in required_fields)

        new_job = job.copy()
        new_job["complete"] = is_complete

        if not is_complete:
            incomplete_count += 1

        validated_jobs.append(new_job)

    print(f"Validare: {incomplete_count} joburi cu campuri lipsa.")
    return {"jobs": validated_jobs}

def save_processed(jobs: list, path="data/processed/jobs_clean.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"Au fost salvate {len(jobs)} joburi procesate.")

def build_graph():
    """Conectarea nodurilor intr-un LangGraph"""
    graph = StateGraph(JobState)

    graph.add_node("filter_tech_jobs", filter_tech_jobs)
    graph.add_node("clean_tags", clean_tags)
    graph.add_node("classify_job", classify_job)
    graph.add_node("recheck_other", recheck_other)
    graph.add_node("report_uncategorized", report_uncategorized)
    graph.add_node("validate", validate)

    graph.set_entry_point("filter_tech_jobs")
    graph.add_edge("filter_tech_jobs", "clean_tags")
    graph.add_edge("clean_tags", "classify_job")
    graph.add_edge("classify_job", "recheck_other")
    graph.add_edge("recheck_other", "report_uncategorized")
    graph.add_edge("report_uncategorized", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


if __name__ =="__main__":
    with open("data/raw/jobs.json", "r", encoding="utf-8") as f:
        raw_jobs=json.load(f)

    app = build_graph()
    result = app.invoke({"jobs": raw_jobs})

    save_processed(result["jobs"])

