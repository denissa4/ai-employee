import re
import json
from google import genai
from PIL import Image, ImageDraw
import os
import uuid
import base64

def is_inside(box, target_area_box):
    x1, y1, x2, y2 = box
    gx1, gy1, gx2, gy2 = target_area_box
    return gx1 <= x1 and gy1 <= y1 and gx2 >= x2 and gy2 >= y2

def is_overlapping(box, target_area_box):
    x1, y1, x2, y2 = box
    gx1, gy1, gx2, gy2 = target_area_box
    return not (x2 < gx1 or x1 > gx2 or y2 < gy1 or y1 > gy2)

def detect_objects(query, file, target_area_box=None):

    # Load and resize the image to 1000x1000 pixels
    image = Image.open(file)
    image = image.resize((1000, 1000))

    # Initialize Google GenAI client
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))
    # Send the image to the model
    response = client.models.generate_content(
        model=os.getenv('GEMINI_RECOGNITION_MODEL', ''),
        contents=[query, image]
    )

    # Extract bounding box JSON from response
    match = re.search(r"\[.*\]", response.text, re.DOTALL)
    if match:
        json_text = match.group(0)  # Extract JSON part
        try:
            bounding_boxes = json.loads(json_text)  # Convert to Python list
        except json.JSONDecodeError:
            print("Error: Extracted text is not valid JSON.")
            bounding_boxes = []
    else:
        return response.text

    # Draw bounding boxes on the image
    draw = ImageDraw.Draw(image)

    if target_area_box:
        # Draw the manually defined green box
        draw.rectangle(target_area_box, outline="green", width=3)

    for item in bounding_boxes:
        label = item["label"]
        y1, x1, y2, x2 = item["box_2d"]

        # Draw the detected bounding box
        draw.rectangle([(x1, y1), (x2, y2)], outline="red", width=2)

        status = ''
        color = 'green'
        if target_area_box:
            # Determine the relation to the green box
            if is_inside((x1, y1, x2, y2), target_area_box):
                status = "Inside"
                color = "blue"
            elif is_overlapping((x1, y1, x2, y2), target_area_box):
                status = "Overlapping"
                color = "orange"
            else:
                status = "Outside"
                color = "purple"

        # Draw status text
        draw.text((x1, y1 - 20 if y1 - 20 > 0 else y1 + 5), f"{label}{': ' if status else ''}", fill=color)

    # Save the modified image
    fn = str(uuid.uuid4())
    file_extension = file.split('.')[-1].lower()
    temp_save_path = f"/tmp/{fn}.{file_extension}"
    image.save(temp_save_path)

    # Read and encode the image for transfer
    with open(temp_save_path, "rb") as f:
        img_bytes = f.read()
        encoded_img = base64.b64encode(img_bytes).decode("utf-8")  # Convert to Base64 string

    # Python code to be executed remotely
    code = f"""
import uuid
import base64
from PIL import Image
import io

# Decode and save the image file
img_bytes = base64.b64decode("{encoded_img}")
fn = uuid.uuid4()
fn = str(fn)
file_path = f"/tmp/sandbox/{{fn}}.{file_extension}"

# Save the decoded image
image = Image.open(io.BytesIO(img_bytes))
image.save(file_path)
    """

    # Execute remotely and return result
    from core import execute_python_code
    res = execute_python_code(code)
    return (res, response.text)

