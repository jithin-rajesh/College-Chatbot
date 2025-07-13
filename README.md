# Syllabus Q&A with Gemini and Streamlit

This project parses a syllabus PDF, and then uses the Gemini API to answer user questions about it. The user interface is built with Streamlit, allowing for seamless interaction with the syllabus content.

## Getting Started

### Prerequisites

- Python 3.x
- pip
- Gemini API Key
- For the preprocessing file use pdfplumber and json

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    ```
2.  Navigate to the project directory:
    ```bash
    cd <project-directory>
    ```
3.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
4.  Set up your Gemini API Key:
    - Create a `.env` file in the root of the project.
    - Add the following line to the `.env` file:
      ```
      GEMINI_API_KEY="YOUR_API_KEY"
      ```
    - Replace `"YOUR_API_KEY"` with your actual Gemini API key.

### Running the Application

To run the application, execute the following commands in your terminal:

```bash
python app.py
```

Open a new terminal, execute this command

```bash
streamlit ui.py
```

## Project Structure

-   `app.py`: The main application file that runs the Streamlit app and integrates the Gemini API.
-   `preprocessing.py`: Contains functions for preprocessing the syllabus data from the PDF.
-   `ui.py`:  Defines the user interface elements for the Streamlit application.
-   `requirements.txt`: A list of the Python packages required to run the project.
-   `Curriculum-2022_CSEAI_B-Tech1st-n-2nd-year-and-3-yearsyllabus_030425 (1).pdf`: The source PDF file for the syllabus.
-   `syllabus_final_structure.json`: A JSON file representing the structured syllabus data.
-   `README.md`: This file.
