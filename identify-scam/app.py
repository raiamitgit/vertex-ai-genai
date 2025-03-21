# app.py
import os
import streamlit as st
from dotenv import load_dotenv
from scam_analyzer import ScamAnalyzer

# Load environment variables at the beginning
load_dotenv()

# Streamlit UI - remains in the main script
def main():
    """
    Main function to run the Streamlit application.
    """

    scam_analyzer = ScamAnalyzer()

    st.title("Scam Detection with Gemini")
    st.markdown(
        "<h3>Enter the text/email or upload an image to check for scams</h3>",
        unsafe_allow_html=True,
    )

    # Use a single container for input elements
    with st.container():
        prompt = st.text_area("Text", placeholder="Enter your text here...", label_visibility="collapsed")
        uploaded_file = st.file_uploader(
            "Upload Image/Video", type=["jpg", "jpeg", "png", "mp4", "webm"],
            label_visibility="collapsed"
        )

    if st.button("Check for Scams"):
        if not prompt and not uploaded_file:
            st.markdown(
                "<h3>Enter the text/email or upload an image to check for scams</h3>",
                unsafe_allow_html=True,
            )

        st.spinner("Checking for scams...")
        gcs_uri = None
        if uploaded_file:
            destination_blob_name = f"uploaded_files/{uploaded_file.name}"
            gcs_uri = scam_analyzer.upload_to_gcs(uploaded_file, destination_blob_name)
            if gcs_uri is None:
                st.error("File upload failed. Please check your connection and try again.")
                return

        response = scam_analyzer.predict_gemini(prompt, image_uri = gcs_uri)
        if response:
            st.subheader("Gemini Response:")
            st.write(response)
        else:
            st.error("Failed to get a response from Gemini. Check the logs for errors.")

if __name__ == "__main__":
    main()
