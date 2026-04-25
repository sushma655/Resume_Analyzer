import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
import os
import json
import re
import io
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from helper import configure_genai, get_gemini_response


# ----------------------------
# SESSION INIT
# ----------------------------
def init_session_state():
    if "processing" not in st.session_state:
        st.session_state.processing = False


# ----------------------------
# PDF TEXT EXTRACTION (MULTI PAGE)
# ----------------------------
def extract_pdf_text(file):
    reader = PdfReader(file)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


# ----------------------------
# SAFE JSON PARSER
# ----------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("Invalid JSON from model")


# ----------------------------
# ATS SCORE BAR
# ----------------------------
def extract_score(score_text):
    try:
        return int(score_text.replace("%", "").strip())
    except:
        return 0


# ----------------------------
# KEYWORD HIGHLIGHTING
# ----------------------------
def highlight_keywords(text, keywords):
    for kw in keywords:
        text = text.replace(kw, f"**:red[{kw}]**")
    return text


# ----------------------------
# PDF REPORT GENERATOR
# ----------------------------
def generate_pdf(report_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    text_object = c.beginText(40, 750)
    text_object.setFont("Helvetica", 10)

    for line in report_text.split("\n"):
        text_object.textLine(line[:100])  # prevent overflow

    c.drawText(text_object)
    c.save()

    buffer.seek(0)
    return buffer


# ----------------------------
# MAIN APP
# ----------------------------
def main():
    load_dotenv()
    init_session_state()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("Missing GOOGLE_API_KEY in .env file")
        return

    configure_genai(api_key)

    # SIDEBAR
    with st.sidebar:
        st.title("🎯 Smart ATS")
        st.write("AI Resume Analyzer with ATS scoring")

    # MAIN UI
    st.title("📄 Smart ATS Resume Analyzer")

    jd = st.text_area("Job Description")

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

    if st.button("Analyze Resume"):

        if not jd:
            st.warning("Enter job description")
            return

        if not uploaded_file:
            st.warning("Upload resume PDF")
            return

        try:
            with st.spinner("Analyzing..."):

                resume_text = extract_pdf_text(uploaded_file)

                prompt = f"""
Return ONLY JSON:
{{
  "JD Match": "85%",
  "MissingKeywords": ["python", "docker"],
  "Profile Summary": "summary"
}}

Resume:
{resume_text}

Job:
{jd}
"""

                response = get_gemini_response(prompt)
                data = safe_json_parse(response)

                st.success("Analysis Complete")

                # ----------------------------
                # ATS SCORE BAR
                # ----------------------------
                score = extract_score(data.get("JD Match", "0%"))

                st.subheader("ATS Score")
                st.progress(score)
                st.markdown(f"### 🎯 {score}% Match")

                # ----------------------------
                # KEYWORDS
                # ----------------------------
                missing = data.get("MissingKeywords", [])

                st.subheader("Missing Keywords")
                st.write(", ".join(missing) if missing else "None")

                # ----------------------------
                # HIGHLIGHTED RESUME
                # ----------------------------
                st.subheader("Resume Preview (Highlighted)")
                st.markdown(highlight_keywords(resume_text, missing))

                # ----------------------------
                # PROFILE SUMMARY
                # ----------------------------
                st.subheader("Profile Summary")
                st.write(data.get("Profile Summary", ""))

                # ----------------------------
                # PDF DOWNLOAD REPORT
                # ----------------------------
                report = f"""
ATS REPORT

Score: {data.get('JD Match')}

Missing Keywords:
{', '.join(missing)}

Summary:
{data.get('Profile Summary')}
"""

                pdf = generate_pdf(report)

                st.download_button(
                    "📥 Download Report PDF",
                    pdf,
                    file_name="ats_report.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error: {str(e)}")


if __name__ == "__main__":
   main()
