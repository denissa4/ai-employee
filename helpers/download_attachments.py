import os
import json
import requests
import pdfplumber
from docx import Document

def download_and_extract_text(url: str, filename: str) -> str:
    """
    Downloads a file from a given URL and extracts text while preserving layout.
    
    Args:
        url (str): The URL of the file to download.
        filename (str): The desired filename for saving the file.

    Returns:
        str: Extracted text while preserving layout.
    """
    try:
        # Download the file
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return f"Failed to download file. Status Code: {response.status_code}"

        # Save the file
        file_extension = filename.split('.')[-1].lower()
        filepath = f"/tmp/{filename}"  # Change this path if needed
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract text while preserving layout
        if file_extension == "pdf":
            extracted_text = extract_text_from_pdf(filepath)
        elif file_extension in ["doc", "docx"]:
            extracted_text = extract_text_from_docx(filepath)
        else:
            return f"Unsupported file type: {file_extension}"

        # Delete temp file after processing
        os.remove(filepath)

        return filename, extracted_text

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        # Ensure file is deleted even if an exception occurs
        if os.path.exists(filepath):
            os.remove(filepath)


def extract_text_from_pdf(filepath: str) -> str:
    """
    Extracts text from a PDF while preserving layout using word positions.
    
    Args:
        filepath (str): Path to the PDF file.

    Returns:
        str: JSON containing extracted text with positional metadata.
    """
    with pdfplumber.open(filepath) as pdf:
        data = {}
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()  # Extract words with coordinates
            data[str(page)] = words

    return json.dumps(data, indent=2)  # Return JSON for structured output


def extract_text_from_docx(filepath: str) -> str:
    """
    Extracts text from a Word (DOCX) file while preserving paragraphs, bold, and italic text.

    Args:
        filepath (str): Path to the DOCX file.

    Returns:
        str: Extracted text with basic formatting.
    """
    doc = Document(filepath)
    extracted_text = []
    
    for para in doc.paragraphs:
        text = ""
        for run in para.runs:
            if run.bold:
                text += f"**{run.text}** "  # Preserve bold text
            elif run.italic:
                text += f"*{run.text}* "  # Preserve italic text
            else:
                text += run.text + " "
        extracted_text.append(text.strip())

    return "\n\n".join(extracted_text)  # Preserve paragraph spacing
