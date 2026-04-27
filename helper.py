import google.generativeai as genai

# ---------------- CONFIG ----------------
def configure_genai(api_key):
    genai.configure(api_key=api_key)

# ---------------- GEMINI (FIXED) ----------------
def get_gemini_response(prompt):
    # Updated to use current model - gemini-1.5-flash
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text
