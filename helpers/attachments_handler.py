import aiohttp
import os
import tempfile
import uuid


async def download_and_save(url: str) -> str:
    """
    Downloads a file from a given URL asynchronously and extracts content while preserving layout.

    Args:
        url (str): The URL of the file to download.

    Returns:
        str: The path to the downloaded file.
    """
    filename = uuid.uuid4()
    file_path = os.path.join(tempfile.gettempdir(), filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return f"Failed to download file. Status Code: {response.status}"

                with open(file_path, "wb") as f:
                    while chunk := await response.content.read(8192):
                        f.write(chunk)

        return file_path

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return f"Error: {str(e)}"

