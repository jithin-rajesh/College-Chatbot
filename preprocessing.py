import pdfplumber
import re
import json
import pandas as pd


def clean_text(text):
    if not text:
        return ""
   
    text = re.sub(r'(\n\s*){2,}', '\n', text).replace('\n', ' ')
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text

def extract_section_between_keywords(full_text, start_keyword, end_keyword=None):
  
    try:
        start_esc = re.escape(start_keyword)
        
        if end_keyword:
            end_esc = re.escape(end_keyword)
            pattern = re.compile(f"{start_esc}(.*?){end_esc}", re.IGNORECASE | re.DOTALL)
        else:
            pattern = re.compile(f"{start_esc}(.*)", re.IGNORECASE | re.DOTALL)
            
        match = pattern.search(full_text)
        if match:
            return clean_text(match.group(1).strip())
            
    except Exception as e:
        print(f"Error extracting between '{start_keyword}' and '{end_keyword}': {e}")
        
    return "Not Found"


def parse_all_detailed_courses(full_text):
   
    all_courses_dict = {}
    
    course_blocks = re.split(r'COURSE OVERVIEW:', full_text, flags=re.IGNORECASE)
    
    for block in course_blocks[1:]: # Skip the text before the first "COURSE OVERVIEW"
        course_block_full = "COURSE OVERVIEW:" + block
        
        course_code_match = re.search(r'\b([A-Z]{2,3}[0-9]U[0-9A-Z]{3,7})\b', course_block_full)
        if not course_code_match:
            continue
            
        course_code = course_code_match.group(1).strip()
        
        course_name = extract_section_between_keywords(course_block_full, course_code, "COURSE OVERVIEW:")
        
        all_courses_dict[course_code] = {
            "course_name": course_name if course_name != "Not Found" else "Name Not Found in Header",
            "overview": extract_section_between_keywords(course_block_full, "COURSE OVERVIEW:", "COURSE OUTCOMES"),
            "outcomes": extract_section_between_keywords(course_block_full, "COURSE OUTCOMES", "SYLLABUS"),
            "syllabus": extract_section_between_keywords(course_block_full, "SYLLABUS", "TEXT BOOKS"),
            "textbooks": extract_section_between_keywords(course_block_full, "TEXT BOOKS", "REFERENCES"),
            "references": extract_section_between_keywords(course_block_full, "REFERENCES", "COURSE PLAN"),
            "course_plan": extract_section_between_keywords(course_block_full, "COURSE PLAN")
        }
        
    return all_courses_dict


def parse_semester_summary_tables(pages):
   
    semester_tables = {}
    
    for i in range(1, 9):
        roman = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII'}[i]
        sem_title = f"SEMESTER {roman}"
        
        for page in pages:
            title_matches = page.search(sem_title, case=False)
            if not title_matches:
                continue

            total_matches = page.search("TOTAL", case=False)
            if not total_matches:
                continue

            table_top = title_matches[0]['top']
            table_bottom = total_matches[0]['bottom']

            if table_top >= table_bottom:
                continue
            
            cropped_page = page.crop((0, table_top, page.width, table_bottom))
            
            table_text = cropped_page.extract_text(x_tolerance=2, layout=True)
            if not table_text:
                continue
                
            courses_in_sem = []
            
            pattern = re.compile(
                r"([A-Z\d/\s½]+)\s+([A-Z]{3})\s+([A-Z0-9]+)\s+(.+?)\s+([0-9]-[0-9]-[0-9])\s+([0-9])\s+([0-9/\\-]+)",
                re.MULTILINE
            )
            
            matches = pattern.findall(table_text)
            for match in matches:
                courses_in_sem.append({
                    "Slot": clean_text(match[0]),
                    "Category Code": match[1].strip(),
                    "Course Number": match[2].strip(),
                    "Courses": clean_text(match[3]),
                    "L-T-P": match[4].strip(),
                    "Hours": match[5].strip(),
                    "Credit": match[6].strip()
                })

            if courses_in_sem:
                semester_tables[sem_title] = courses_in_sem
                break 
                
    return semester_tables

def process_syllabus_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join([page.extract_text(x_tolerance=1) or "" for page in pdf.pages])
            
            final_syllabus_data = {
                "header_info": {},
                "semesters": {}
            }

            print("1. Parsing Header Information...")
            final_syllabus_data["header_info"] = {
                "institution_vision_mission": extract_section_between_keywords(full_text, "Vision and Mission of the Institution", "DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING"),
                "department_vision_mission": extract_section_between_keywords(full_text, "Vision and Mission of the Department", "PROGRAMME EDUCATIONAL OBJECTIVES"),
                "peos": extract_section_between_keywords(full_text, "PROGRAMME EDUCATIONAL OBJECTIVES (PEOs)", "PROGRAMME OUTCOMES (POs)"),
                "pos": extract_section_between_keywords(full_text, "PROGRAMME OUTCOMES (POs)", "PROGRAMME SPECIFIC OUTCOMES (PSOs)"),
                "psos": extract_section_between_keywords(full_text, "PROGRAMME SPECIFIC OUTCOMES (PSOs)", "Scheduling of Courses")
            }

            print("\n2. Parsing ALL Detailed Course Descriptions (First Pass)...")
            all_courses_master_dict = parse_all_detailed_courses(full_text)
            print(f"   - Found details for {len(all_courses_master_dict)} unique courses.")

            print("\n3. Parsing Semester Summary Tables (Second Pass)...")
            semester_summary_tables = parse_semester_summary_tables(pdf.pages)
            
            print("\n4. Assembling Final JSON Structure...")
            for sem_name, courses_list in semester_summary_tables.items():
                print(f"   - Assembling {sem_name}...")
                final_syllabus_data["semesters"][sem_name] = {"courses": []}
                
                for course_summary in courses_list:
                    course_code = course_summary.get("Course Number")
                    if course_code and course_code in all_courses_master_dict:
                        combined_info = {
                            "summary": course_summary,
                            "details": all_courses_master_dict[course_code]
                        }
                        final_syllabus_data["semesters"][sem_name]["courses"].append({course_code: combined_info})
                    else:
                        print(f"   - WARNING: Course code '{course_code}' from summary not found in detailed descriptions.")
                        final_syllabus_data["semesters"][sem_name]["courses"].append({course_code or "UNKNOWN_CODE": {"summary": course_summary, "details": "Not Found"}})

            return final_syllabus_data

    except Exception as e:
        print(f"An error occurred during PDF processing: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    pdf_file_path ='Curriculum-2022_CSEAI_B-Tech1st-n-2nd-year-and-3-yearsyllabus_030425 (1).pdf' 
    
    structured_syllabus = process_syllabus_pdf(pdf_file_path)
    
    if structured_syllabus:
        output_json_path = 'syllabus_final_structure.json'
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(structured_syllabus, f, ensure_ascii=False, indent=4)
        print(f"\nSuccessfully processed and saved structured data to {output_json_path}")