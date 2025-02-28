from docx import Document
import os
import tempfile
import uuid
import requests
from io import BytesIO

SANDBOX_URL = os.getenv('SANDBOX_ENDPOINT', '')

def replace_text_in_paragraph(paragraph, target, replacement):
    """
    Replaces all occurrences of the target string with the replacement string within the given paragraph,
    while preserving the original formatting.
    """
    for run in paragraph.runs:
        if target in run.text:
            run.text = run.text.replace(target, replacement)

def replace_text_in_doc(doc_path, target, replacement, final=False):
    """
    Replaces all occurrences of the target string with the replacement string in the specified Word document,
    preserving the original formatting, and saves the modified document to a new file.
    """
    doc = Document(doc_path)
    
    # Iterate through all paragraphs in the document
    for paragraph in doc.paragraphs:
        replace_text_in_paragraph(paragraph, target, replacement)
    
    # Iterate through all tables in the document
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_text_in_paragraph(paragraph, target, replacement)

    filename = uuid.uuid4()
    output_path = os.path.join(tempfile.gettempdir(), filename)
    
    # Save the modified document
    doc.save(output_path)

    os.remove(doc_path)

    if final:
        fn = uuid.uuid4()
        code = f"""
        import os

        # Define the path for the file in the 'srv' directory
        srv_directory = '/srv'
        file_name = {fn}
        file_path = os.path.join(srv_directory, file_name)

        # Ensure the directory exists
        if not os.path.exists(srv_directory):
            os.makedirs(srv_directory)

        # Create and write to the file
        with open(file_path, 'w') as f:
            f.write('This is a test file created inside the srv directory.')
            
        return file_path  # Return the path of the created file
        """
        response = requests.post(f"{SANDBOX_URL}/execute", json={"code": code}, timeout=600)
        return response

    return output_path


def read_word_doc(file_path):
    """
    Reads all the text from a Word document (.docx).
    
    Args:
        file_path (str): The path to the .docx file.
    
    Returns:
        str: The text content of the Word document.
    """
    doc = Document(file_path)
    text = []

    # Read paragraphs
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)

    # Read tables (if any)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text.append(cell.text)

    return '\n'.join(text)