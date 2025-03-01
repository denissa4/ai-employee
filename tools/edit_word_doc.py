from docx import Document
import os
import uuid
import requests
import base64

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
    output_path = f"/tmp/{filename}"
    
    # Save the modified document
    doc.save(output_path)

    os.remove(doc_path)

    if final:
        # Read the file content to send it as part of the code
        with open(output_path, 'rb') as f:
            file_content = f.read()

        # Encode file content as a string suitable for inclusion in Python code (Base64 is a good option)
        file_content_base64 = base64.b64encode(file_content).decode('utf-8')
        fn = uuid.uuid4()
        code = f"""
        import os
        import base64

        # Define the path for the file in the 'srv' directory
        file_name = "{fn}"
        file_path = f"/srv/{{file_name}}"

        # Decode Base64 back to binary
        file_content_base64 = "{file_content_base64}"
        file_content = base64.b64decode(file_content_base64)

        # Write the binary data back to the file
        with open(file_path, 'wb') as f:
            f.write(file_content)

        return file_path  # Return the path of the created file
        """
        response = requests.post(f"{SANDBOX_URL}/execute", json={"code": code}, timeout=600)
        os.remove(output_path)
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