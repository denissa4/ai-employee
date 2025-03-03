import requests
import uuid
import os

def download_and_save(url: str, name: str) -> str:
    """
    Downloads a file from a given URL and extracts content while preserving layout.

    Args:
        url (str): The URL of the file to download.

    Returns:
        str: The path to the downloaded file.
    """
    file_path = None  # Initialize file_path to handle exceptions properly

    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return f"Failed to download file. Status Code: {response.status_code}"

        # Get file extension (assuming docx for now)
        extension = name.split('.')[1]

        # Generate file name with extension
        filename = f"{uuid.uuid4()}.{extension}"
        file_path = f"/tmp/{filename}"

        # Save file
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return file_path

    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return f"Error: {str(e)}"

