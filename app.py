from flask import Flask, request, jsonify
import json
import re
import os
import google.generativeai as genai

app = Flask(__name__)

try:
    with open('syllabus_final_structure.json', 'r', encoding='utf-8') as f:
        syllabus_data = json.load(f)
    syllabus_json_string = json.dumps(syllabus_data, indent=2)
    print("Syllabus data loaded successfully.")
except FileNotFoundError:
    syllabus_data = None
    syllabus_json_string = None
    print("ERROR: syllabus_final_structure.json not found.")
except json.JSONDecodeError:
    syllabus_data = None
    syllabus_json_string = None
    print("ERROR: Could not decode JSON from syllabus_final_structure.json.")

genai_model = None
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("WARNING: GEMINI_API_KEY environment variable not found. AI fallback will be disabled.")
    else:
        genai.configure(api_key=api_key)
        genai_model = genai.GenerativeModel('gemini-2.5-flash')
        print("Gemini AI model initialized successfully.")
except Exception as e:
    print(f"ERROR: Could not initialize Gemini AI. - {e}")

def format_list(items, title):
    if isinstance(items, str):
        items = re.split(r'\. |\d+\. ', items)
    
    response = f"**{title}**:\n\n"
    for item in items:
        if item.strip():
            cleaned_item = re.sub(r'^(PEO|PSO)\d*:?\s*', '', item.strip())
            response += f"- {cleaned_item.strip()}\n"
    return response

def format_course_details(course_data):
    if not course_data or course_data.get('details') == 'Not Found':
        return "Sorry, detailed information for this course could not be found."

    details = course_data['details']
    summary = course_data['summary']
    response = f"### Course Details: {summary.get('Courses', 'N/A')} ({summary.get('Course Number', 'N/A')})\n\n"
    response += f"- **Category:** {summary.get('Category Code', 'N/A')}\n"
    response += f"- **L-T-P:** {summary.get('L-T-P', 'N/A')}\n"
    response += f"- **Credits:** {summary.get('Credit', 'N/A')}\n\n"
    if details.get('overview'): response += f"**Overview:**\n{details['overview']}\n\n"
    if details.get('outcomes'): response += format_list(details['outcomes'].split('CO '), "Course Outcomes (COs)") + "\n"
    if details.get('syllabus'): response += f"**Syllabus:**\n{details['syllabus']}\n\n"
    if details.get('textbooks'): response += format_list(details['textbooks'], "Textbooks") + "\n"
    if details.get('references'): response += format_list(details['references'], "Reference Books") + "\n"
    return response

def find_course(identifier, data):
    identifier = identifier.strip().lower()
    for sem, sem_data in data['semesters'].items():
        for course_wrapper in sem_data['courses']:
            for course_code, course_info in course_wrapper.items():
                if course_code.lower() == identifier or course_info['summary']['Courses'].lower() == identifier:
                    return course_info
    return None

@app.route('/ask', methods=['POST'])
def ask_question():
    if not syllabus_data:
        return jsonify({"answer": "I'm sorry, the syllabus data is currently unavailable on the server."}), 500

    req_data = request.get_json()
    if not req_data or 'question' not in req_data:
        return jsonify({'error': 'Bad Request: "question" field is missing.'}), 400
    
    question = req_data['question']
    question_lower = question.lower()
    
    course_code_match = re.search(r'([a-z]{2}\d[a-z]\d{3}[a-z])', question_lower)
    if course_code_match:
        course_code = course_code_match.group(1)
        course = find_course(course_code, syllabus_data)
        if course:
            return jsonify({"answer": format_course_details(course)})
    if 'courses in' in question_lower or 'subjects in' in question_lower:
        sem_match = re.search(r'semester (\d+|i{1,2})', question_lower) or re.search(r'sem (\d+|i{1,2})', question_lower)
        if sem_match:
            sem_map = {'1': 'SEMESTER I', 'i': 'SEMESTER I', '2': 'SEMESTER II', 'ii': 'SEMESTER II'}
            semester_key = sem_map.get(sem_match.group(1))
            if semester_key and semester_key in syllabus_data['semesters']:
                courses = syllabus_data['semesters'][semester_key]['courses']
                course_list = [f"{c_info['summary']['Courses']} ({c_code})" for c in courses for c_code, c_info in c.items()]
                return jsonify({"answer": format_list(course_list, f"Courses in {semester_key}")})

    header_info = syllabus_data['header_info']
    if 'peo' in question_lower: return jsonify({"answer": format_list(header_info.get('peos'), "Program Educational Objectives (PEOs)")})
    if 'pso' in question_lower: return jsonify({"answer": format_list(header_info.get('psos'), "Program Specific Outcomes (PSOs)")})
    if 'po' in question_lower or 'program outcomes' in question_lower: return jsonify({"answer": format_list(header_info.get('pos'), "Program Outcomes (POs)")})
    if 'vision' in question_lower and 'department' in question_lower: return jsonify({"answer": f"**Department Vision:**\n\n{header_info.get('department_vision_mission', {}).get('Vision')}"})
    if 'mission' in question_lower and 'department' in question_lower: return jsonify({"answer": f"**Department Mission:**\n\n{header_info.get('department_vision_mission', {}).get('Mission')}"})
    if 'vision' in question_lower: return jsonify({"answer": f"**Institution Vision:**\n\n{header_info.get('institution_vision_mission', {}).get('Vision')}"})
    if 'mission' in question_lower: return jsonify({"answer": f"**Institution Mission:**\n\n{header_info.get('institution_vision_mission', {}).get('Mission')}"})


    if not genai_model:
        answer = "I couldn't find a specific answer for your query. The advanced AI assistant is currently disabled. Please ask about course details, semester subjects, vision, or mission."
        return jsonify({"answer": answer})

    print(f"Rule-based check failed. Falling back to Gemini AI for question: '{question}'")
    
    prompt = f"""
    You are an expert college syllabus assistant.
    Your task is to answer the user's question based ONLY on the provided syllabus data in JSON format.
    Do not use any external knowledge. If the answer is not in the provided context, state that you cannot find the information in the syllabus.
    Format your answer clearly using markdown for better readability.

    Here is the full syllabus data:
    ```json
    {syllabus_json_string}
    ```

    Here is the user's question:
    "{question}"
    
    Answer:
    """

    try:
        ai_response = genai_model.generate_content(prompt)
        answer = ai_response.text
    except Exception as e:
        print(f"ERROR: Gemini API call failed. - {e}")
        answer = "Sorry, I encountered an error while trying to generate an AI-powered response. Please try again."

    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(debug=True)