import os
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PIL import Image
from io import BytesIO

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
CATEGORY_NAME = "Category:Constellation_maps_by_the_International_Astronomical_Union"
DOWNLOAD_DIR = "constellations"
USER_AGENT = "YourAppName/1.0 (yourname@example.com)"
PDF_FILENAME = "Constellation_Maps.pdf"

def get_files_from_category(category_name):
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": category_name,
        "cmtype": "file",
        "cmlimit": "max"
    }
    headers = {
        "User-Agent": USER_AGENT
    }
    response = requests.get(WIKIMEDIA_API_URL, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("query", {}).get("categorymembers", [])

def download_image(url, dest_folder, filename):
    headers = {
        "User-Agent": USER_AGENT
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    file_path = os.path.join(dest_folder, filename)
    with open(file_path, 'wb') as out_file:
        for chunk in response.iter_content(chunk_size=8192):
            out_file.write(chunk)
    return file_path

def create_pdf_with_images(image_files, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin = inch / 2
    image_width = (width - 2 * margin) / 2
    image_height = (height - 2 * margin) / 2

    for i, file_path in enumerate(image_files):
        if i % 2 == 0:
            if i > 0:
                c.showPage()
            c.setFont("Helvetica", 12)
            c.drawString(margin, height - margin / 2, "Page {}".format(i // 2 + 1))

        x_offset = margin
        y_offset = height - margin - ((i % 2) + 1) * image_height - (i % 2) * margin

        # Open the image from the file path
        image = Image.open(file_path)
        image = image.convert("RGB")

        # Calculate the aspect ratio and resize accordingly
        aspect_ratio = min(image_width / image.width, image_height / image.height)
        new_width = int(image.width * aspect_ratio)
        new_height = int(image.height * aspect_ratio)

        # Resize the image to fit within the specified width and height
        image = image.resize((new_width, new_height), Image.LANCZOS)

        # Save the resized image to a temporary file
        temp_file_path = file_path + "_temp.jpg"
        image.save(temp_file_path, format='JPEG', quality=95)

        x_centered = x_offset + (image_width - new_width) / 2
        y_centered = y_offset + (image_height - new_height) / 2
        c.drawImage(temp_file_path, x_centered, y_centered, width=new_width, height=new_height)

        # Remove the temporary file after use
        os.remove(temp_file_path)

    c.save()

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    files = get_files_from_category(CATEGORY_NAME)
    jpg_files = [file for file in files if file["title"].endswith(".jpg")]

    image_files = []
    for file in jpg_files:
        file_title = file["title"]
        file_name = file_title.split(":")[1]
        file_path = os.path.join(DOWNLOAD_DIR, file_name)

        if not os.path.exists(file_path):
            file_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{file_name}"
            download_image(file_url, DOWNLOAD_DIR, file_name)

        image_files.append(file_path)

    create_pdf_with_images(image_files, PDF_FILENAME)

if __name__ == "__main__":
    main()
