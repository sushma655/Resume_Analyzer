import google.generativeai as genai
from PyPDF2 import PdfReader
import os

# ---------------- CONFIG ----------------
def configure_genai(api_key):
    genai.configure(api_key=api_key)

# ---------------- GEMINI ----------------
def get_gemini_response(prompt):
    model = genai.GenerativeModel("gemini-1.0-pro")
    response = model.generate_content(prompt)
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
