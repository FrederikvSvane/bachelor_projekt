import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re


def load_template():
    with open("test/scraper/møde_data_template.json", "r", encoding="utf-8") as f:
        return json.load(f)


def parse_case_text(text, case_type):
    json = load_template()
    json["Sagstype"] = case_type
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        if line.startswith("Retsmødet er offentligt"):
            json["Retsmødet er offentligt"] = True
        elif line.startswith("Dommer:"):
            json["Dommer"].append(line.replace("Dommer:", "").strip())
        elif line.startswith("Advokat:"):
            json["Advokater"].append(line.replace("Advokat:", "").strip())
        elif line.startswith("Sagsøger:"):
            json["Sagsøger"].append(line.replace("Sagsøger:", "").strip())
        elif line.startswith("Sagsøgers advokat:"):
            json["Sagsøgers advokater"].append(
                line.replace("Sagsøgers advokat:", "").strip()
            )
        elif line.startswith("Sagsøgte:"):
            json["Sagsøgte"].append(line.replace("Sagsøgte:", "").strip())
        elif line.startswith("Sagsøgtes advokat:"):
            json["Sagsøgtes advokater"].append(
                line.replace("Sagsøgtes advokat:", "").strip()
            )
        elif line.startswith("Sagen drejer sig om:"):
            if "fortsat sag" in line.lower():
                json["Fortsat sag"] = True
                cleaned_text = line.replace("Sagen drejer sig om:", "").strip()
                cleaned_text = (
                    cleaned_text.replace("FORTSAT SAG", "")
                    .replace("fortsat sag", "")
                    .strip()
                )
                cleaned_text = cleaned_text.replace("-", "").strip()
                json["Sagen drejer sig om"] = cleaned_text
            else:
                json["Sagen drejer sig om"] = line.replace(
                    "Sagen drejer sig om:", ""
                ).strip()
        elif line.startswith("FORTSAT SAG"):
            json["Fortsat sag"] = True
        elif re.search(r"^\d{2}-\d{2}-\d{4}", line): # REGEX for at finde dato, tid og sted
            date_match = re.search(r"(\d{2}-\d{2}-\d{4})", line)
            if date_match:
                date_part = date_match.group(1)
                try:
                    date_obj = datetime.strptime(date_part, "%d-%m-%Y")
                    json["Dato"] = date_obj.strftime("%d-%m-%Y")
                except ValueError:
                    json["Dato"] = date_part

            time_match = re.search(r'kl\.(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', line)
            if time_match:
                json["Starttid"] = time_match.group(1)
                json["Sluttid"] = time_match.group(2)

            location_match = re.search(r'Retssal\s*(\d+)', line)
            if location_match:
                json["Lokale"] = f"Retssal {location_match.group(1)}"
            
        elif any(x in line for x in ["Borgerlig sag", "Straffesag"]):
            if "m/lægdommere" in line.lower():
                json["Lægdommere"] = True
                line = line.replace("m/lægdommere", "").strip()
            if "u/lægdommere" in line.lower():
                json["Lægdommere"] = False
                line = line.replace("u/lægdommere", "").strip()
            if "m/domsmænd" in line.lower():
                json["Domsmænd"] = True
                line = line.replace("m/domsmænd", "").strip()
            if "u/domsmænd" in line.lower():
                json["Domsmænd"] = False
                line = line.replace("u/domsmænd", "").strip()
            json["Kategori"] = line

    return json


def get_case_type(url):
    if "straffesager" in url:
        return "Straffe"
    elif "civile-sager" in url:
        return "Civile"
    elif "tvangsauktioner" in url:
        return "Tvangsauktioner"
    else:
        return "Ukendt sagstype"


def get_court_cases(url):
    case_type = get_case_type(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    editor_content = soup.find("div", class_="editor-content")

    cases = []
    for case_element in editor_content.find_all(
        "p", class_="MsoNormal", style="mso-pagination: widow-orphan lines-together;"
    ):
        text_content = []
        for element in case_element.contents:
            if element.name == "br":
                text_content.append("\n")
            if element.name == "span":
                for span_element in element.contents:
                    if span_element.name == "br":
                        text_content.append("\n")
                    elif isinstance(span_element, str):
                        text_content.append(span_element.strip())
            elif isinstance(element, str):
                text_content.append(element.strip())

        case_text = " ".join(text_content).replace("\n ", "\n").strip()
        cases.append(parse_case_text(case_text, case_type))

    return cases


def parse_url_info(url):
    # Retshus
    match = re.search(r"domstol\.dk/(\w+)/", url)
    if not match:
        raise ValueError(f"Could not parse URL format: {url}")

    court = match.group(1)
    if court == "koebenhavn":
        court = "København"
    elif court == "hilleroed":
        court = "Hillerød"

    # Ugenr
    week = url.strip("/").split("/")[-1][-1]
    case_type = get_case_type(url)

    return court, case_type, week


def get_output_path(url):
    court, case_type, week = parse_url_info(url)

    path = os.path.join("test/data/retsmøder", court, case_type)
    filename = f"{case_type}_uge_{week}.json"

    # Laver mapper hvis de ikke findes
    os.makedirs(path, exist_ok=True)

    return os.path.join(path, filename)


def calculate_durations(cases):
    for case in cases:
        start_time = case.get("Starttid")
        end_time = case.get("Sluttid")
        #remove potential ending . from start_time and end_time
        if start_time and start_time[-1] == ".":
            start_time = start_time[:-1]
        if end_time and end_time[-1] == ".":
            end_time = end_time[:-1]
        duration = 0  #default duration if times are missing or invalid
        
        if start_time and end_time:
            try:
                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                
                start_total = start_h * 60 + start_m
                end_total = end_h * 60 + end_m
                
                duration = end_total - start_total
            except (ValueError, AttributeError):
                # Handle invalid time formats with grace <3
                pass
        
        case["Varighed"] = duration
    return cases

def main():
    # Liste af URLs til scraping (find manuelt)
    urls = [
        # "https://www.domstol.dk/hilleroed/retslister/2025/2/straffesager-uge-8/",
        # "https://www.domstol.dk/hilleroed/retslister/2025/2/civile-sager-uge-8/",
        # "https://www.domstol.dk/hilleroed/retslister/2025/2/tvangsauktioner-uge-8/",
        # "https://www.domstol.dk/hilleroed/retslister/2025/1/straffesager-7/",
        # "https://www.domstol.dk/hilleroed/retslister/2025/1/civile-sager-uge-7/",
        # "https://www.domstol.dk/hilleroed/retslister/2025/1/tvangsauktioner-uge-7/",
        # "https://www.domstol.dk/koebenhavn/retslister/2025/2/straffesager-uge-8/",
        # "https://www.domstol.dk/koebenhavn/retslister/2025/2/civile-sager-uge-8/",
        # "https://www.domstol.dk/koebenhavn/retslister/2025/2/straffesager-uge-7/",
        # "https://www.domstol.dk/koebenhavn/retslister/2025/2/civile-sager-uge-7/",
        "https://www.domstol.dk/hilleroed/retslister/2025/2/straffesager-uge-9/",
        "https://www.domstol.dk/hilleroed/retslister/2025/2/civile-sager-uge-9/",
        "https://www.domstol.dk/koebenhavn/retslister/2025/2/civile-sager-uge-9/",
        "https://www.domstol.dk/koebenhavn/retslister/2025/2/straffesager-uge-9/"
    ]

    for url in urls:
        try:
            cases = get_court_cases(url)
            cases = calculate_durations(cases)
            output_path = get_output_path(url)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(cases, f, ensure_ascii=False, indent=2)

            print(f"Successfully scraped {len(cases)} cases from {url}")
            print(f"Saved to: {output_path}")

        except Exception as e:
            print(f"Error processing {url}: {str(e)}")


if __name__ == "__main__":
    main()
