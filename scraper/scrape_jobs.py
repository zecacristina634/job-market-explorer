import json
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://remoteok.com/remote-dev-jobs"

def scrape_jobs():
    jobs=[]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_selector("table#jobsboard", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        rows = page.query_selector_all("tr.job")
        print(f"Am gasit {len(rows)} joburi pe pagina.")

        for row in rows:
            try:
                company= row.get_attribute("data-company") or ""
                relative_url = row.get_attribute("data-url") or ""
                link = f"https://remoteok.com{relative_url}" if relative_url else ""

                json_ld_el = row.query_selector('script[type="application/ld+json"]')
                title =""
                date_posted =""
                salary =""

                if json_ld_el:
                    raw_json = json_ld_el.inner_text()
                    data = json.loads(raw_json)
                    title =data.get("title", "")
                    date_posted = data.get("datePosted", "")

                    base_salary = data.get("baseSalary", {})
                    value = base_salary.get("value", {}) if base_salary else {}
                    min_v = value.get("minValue")
                    max_v = value.get("maxValue")
                    currency = base_salary.get("currency", "")
                    if min_v and max_v:
                        salary = f"{min_v}-{max_v} {currency}"

                tag_elements = row.query_selector_all(".tags h3")
                tags = [t.inner_text().strip() for t in tag_elements if t.inner_text().strip()]

                location_el = row.query_selector(".location")
                location = location_el.inner_text().strip() if location_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "tags": ",".join(tags),
                    "salary": salary,
                    "date_posted": date_posted,
                    "link": link,
                })

            except Exception as e:
                print(f"Eroare la un job: {e}")
                continue

        browser.close()

    return jobs


def save_to_json(jobs, path="data/raw/jobs.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"Salvat {len(jobs)} joburi in {path}")


def save_to_csv(jobs, path="data/raw/jobs.csv"):
    if not jobs:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)
    print(f"Salvat {len(jobs)} joburi in {path}")

if __name__ == "__main__":
    jobs_data=scrape_jobs()
    save_to_json(jobs_data)
    save_to_csv(jobs_data)