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
import google.generativeai as genai


# ----------------------------
# GEMINI FUNCTIONS (DIRECTLY IN APP)
# ----------------------------
def configure_genai(api_key):
    genai.configure(api_key=api_key)

def get_gemini_response(prompt):
    """Get response from Gemini using current model"""
    try:
        # Try with gemini-1.5-flash first (faster, cheaper)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Fallback to gemini-1.5-pro if flash fails
        print(f"Flash failed: {e}, trying pro...")
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text


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
        # Try to parse the entire text as JSON
        return json.loads(text)
    except:
        # If that fails, try to extract JSON using regex
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                # If still failing, try to clean common issues
                cleaned = re.sub(r',\s*}', '}', match.group())
                cleaned = re.sub(r',\s*]', ']', cleaned)
                return json.loads(cleaned)
        else:
            raise ValueError("Invalid JSON from model")


# ----------------------------
# ATS SCORE BAR
# ----------------------------
def extract_score(score_text):
    try:
        # Handle both "85%" and "85" formats
        score_str = str(score_text).replace("%", "").strip()
        return int(score_str)
    except:
        return 0


# ----------------------------
# KEYWORD HIGHLIGHTING
# ----------------------------
def highlight_keywords(text, keywords):
    if not keywords:
        return text
    
    for kw in keywords:
        # Case-insensitive highlighting
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f"**:red[{kw}]**", text)
    return text


# ----------------------------
# PDF REPORT GENERATOR
# ----------------------------
def generate_pdf(report_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Add title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "ATS Resume Analysis Report")
    
    # Add content
    c.setFont("Helvetica", 10)
    y = 720
    
    for line in report_text.split("\n"):
        if y < 50:  # New page if needed
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 750
        
        # Handle long lines
        if len(line) > 90:
            # Split long lines
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= 90:
                    current_line += " " + word if current_line else word
                else:
                    c.drawString(50, y, current_line)
                    y -= 15
                    current_line = word
            if current_line:
                c.drawString(50, y, current_line)
                y -= 15
        else:
            c.drawString(50, y, line)
            y -= 15
    
    c.save()
    buffer.seek(0)
    return buffer


# ----------------------------
# IMPROVED PROMPT
# ----------------------------
def create_analysis_prompt(resume_text, job_description):
    return f"""You are an expert ATS (Applicant Tracking System) analyst. Analyze this resume against the job description.

Job Description:
{job_description}

Resume:
{resume_text}

Return ONLY valid JSON in this exact format (no other text, no markdown formatting):
{{
  "JD Match": "85",
  "MissingKeywords": ["keyword1", "keyword2", "keyword3"],
  "Profile Summary": "A brief 2-3 sentence summary of how well the candidate matches the role"
}}

Rules:
- JD Match should be a number between 0 and 100 only (no % symbol)
- MissingKeywords should list 3-7 key skills/qualifications from the job description that are missing from the resume
- Profile Summary should be specific and actionable

Example valid response:
{{
  "JD Match": "72",
  "MissingKeywords": ["Python", "AWS", "Docker"],
  "Profile Summary": "Strong frontend experience but lacks cloud and backend skills mentioned in the job description."
}}"""


# ----------------------------
# MAIN APP
# ----------------------------
def main():
    load_dotenv()
    init_session_state()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("Missing GOOGLE_API_KEY in .env file. Please add it and restart.")
        st.info("Create a .env file with: GOOGLE_API_KEY=your_key_here")
        return

    try:
        configure_genai(api_key)
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {str(e)}")
        return

    # SIDEBAR
    with st.sidebar:
        st.title("🎯 Smart ATS")
        st.write("AI Resume Analyzer with ATS scoring")
        add_vertical_space(2)
        st.markdown("""
        ### How it works:
        1. Paste the job description
        2. Upload your resume (PDF)
        3. Click Analyze Resume
        4. Get ATS score and feedback
        
        ### Tips:
        - Tailor your resume to each job
        - Include keywords from the JD
        - Use standard section headings
        """)
        
        # Debug info
        with st.expander("Debug Info"):
            st.write(f"API Key configured: {'Yes' if api_key else 'No'}")
            try:
                # Test the model
                test_model = genai.GenerativeModel("gemini-1.5-flash")
                st.success("Gemini 1.5 Flash is available")
            except Exception as e:
                st.error(f"Model error: {str(e)}")

    # MAIN UI
    st.title("📄 Smart ATS Resume Analyzer")
    
    # Job description input
    jd = st.text_area(
        "📋 Job Description",
        height=200,
        placeholder="Paste the job description here..."
    )
    
    # File uploader
    uploaded_file = st.file_uploader(
        "📎 Upload Resume (PDF)",
        type="pdf",
        help="Upload your resume in PDF format"
    )
    
    # Analyze button
    if st.button("🚀 Analyze Resume", type="primary", disabled=st.session_state.processing):
        
        # Validation
        if not jd:
            st.warning("⚠️ Please enter a job description")
            return
        
        if not uploaded_file:
            st.warning("⚠️ Please upload a resume PDF")
            return
        
        st.session_state.processing = True
        
        try:
            with st.spinner("🔍 Analyzing your resume against the job description..."):
                
                # Extract text from PDF
                resume_text = extract_pdf_text(uploaded_file)
                
                if not resume_text.strip():
                    st.error("Could not extract text from PDF. Please ensure it's a text-based PDF (not scanned).")
                    st.session_state.processing = False
                    return
                
                # Create and send prompt
                prompt = create_analysis_prompt(resume_text, jd)
                response = get_gemini_response(prompt)
                
                # Parse JSON response
                data = safe_json_parse(response)
                
                # Extract data
                score = extract_score(data.get("JD Match", "0"))
                missing_keywords = data.get("MissingKeywords", [])
                profile_summary = data.get("Profile Summary", "No summary available")
                
                # Display results
                st.success("✅ Analysis Complete!")
                
                # ATS Score with progress bar
                st.subheader("📊 ATS Compatibility Score")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(score / 100)
                with col2:
                    st.metric("Score", f"{score}%")
                
                # Color code based on score
                if score >= 80:
                    st.success(f"🎉 Great match! Your resume aligns well with this role.")
                elif score >= 60:
                    st.info(f"👍 Good match. Some improvements could help.")
                elif score >= 40:
                    st.warning(f"⚠️ Moderate match. Consider significant tailoring.")
                else:
                    st.error(f"📉 Low match. Major revisions recommended.")
                
                # Missing Keywords
                st.subheader("🔑 Missing Keywords")
                if missing_keywords:
                    st.write("These important keywords from the job description were not found in your resume:")
                    cols = st.columns(3)
                    for i, kw in enumerate(missing_keywords):
                        cols[i % 3].markdown(f"- **:red[{kw}]**")
                else:
                    st.success("✅ Great! All key keywords found in your resume.")
                
                # Resume Preview with highlighting
                with st.expander("📄 Resume Preview (with highlighted missing keywords)"):
                    highlighted_text = highlight_keywords(resume_text[:5000], missing_keywords)  # Limit length
                    st.markdown(highlighted_text)
                    if len(resume_text) > 5000:
                        st.info("Preview truncated to 5000 characters.")
                
                # Profile Summary
                st.subheader("📝 Profile Summary & Recommendations")
                st.write(profile_summary)
                
                # Generate and provide PDF report
                report = f"""
ATS RESUME ANALYSIS REPORT
{'='*50}

Job Description Analyzed: {jd[:200]}...

{'='*50}
SCORE: {score}%

ASSESSMENT: {'Excellent Match' if score >= 80 else 'Good Match' if score >= 60 else 'Needs Improvement'}

MISSING KEYWORDS:
{chr(10).join(['- ' + kw for kw in missing_keywords]) if missing_keywords else 'None - Excellent keyword optimization!'}

RECOMMENDATIONS:
{profile_summary}

{'='*50}
Generated by Smart ATS Resume Analyzer
                """
                
                pdf = generate_pdf(report)
                
                st.download_button(
                    label="📥 Download Full Report (PDF)",
                    data=pdf,
                    file_name=f"ats_report_{score}_percent.pdf",
                    mime="application/pdf"
                )
                
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse AI response. Please try again.")
            st.code(f"Error: {str(e)}\nResponse: {response if 'response' in locals() else 'No response'}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.info("Please check your API key and try again.")
        
        finally:
            st.session_state.processing = False


if __name__ == "__main__":
    st.set_page_config(
        page_title="Smart ATS Resume Analyzer",
        page_icon="📄",
        layout="wide"
    )
    main()
