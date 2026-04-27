from google import genai
from PyPDF2 import PdfReader
import os

# ---------------- CONFIG ----------------
def configure_genai(api_key):
    os.environ["GOOGLE_API_KEY"] = api_key

# ---------------- GEMINI ----------------
def get_gemini_response(prompt):
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text

# ---------------- PDF ----------------
def extract_pdf_text(file):
    reader = PdfReader(file)
    text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    return text
