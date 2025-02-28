import aiohttp
import os
import uuid
import mimetypes

async def download_and_save(url: str) -> str:
    from server import app
    """
    Downloads a file from a given URL asynchronously and extracts content while preserving layout.

    Args:
        url (str): The URL of the file to download.

    Returns:
        str: The path to the downloaded file.
    """
    app.logger.info(f"Downloading file from {url} ...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Failed to download file. Status Code: {response.status}"

                # Get file extension from Content-Type header
                extension = 'docx'

                # Generate file name with extension
                filename = f"{uuid.uuid4()}{extension}"
                file_path = f"/tmp/{filename}"

                # Save file
                with open(file_path, "wb") as f:
                    while chunk := await response.content.read(8192):
                        f.write(chunk)

        app.logger.info(f"File downloaded to {file_path}")
        return file_path

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return f"Error: {str(e)}"
