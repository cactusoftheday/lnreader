import json
import os
import ebooklib
from ebooklib import epub
import re

# Function to extract the cover image
def extract_cover_image(book, output_folder):
    cover_images = list(book.get_items_of_type(ebooklib.ITEM_COVER))
    if cover_images:
        cover_image_filename = os.path.join(output_folder, 'cover.jpg')
        with open(cover_image_filename, 'wb') as cover_file:
            cover_file.write(cover_images[0].get_content())

# Function to save content to a file
def save_content_to_file(content, filename):
    # Ensure the directory where the file will be saved exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Write the content to the file
    with open(filename, 'wb') as file:
        file.write(content)

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to extract text and images from chapters
def extract_and_save_chapters(book, output_folder):
    # Create the output folder if it doesn't exist
    ensure_directory_exists(output_folder)

    # Iterate through all the items in the book
    for item in book.get_items():
        # Check if the item is of type ITEM_DOCUMENT (HTML content)
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()

            # Extract and save the content to a file
            chapter_filename = os.path.join(output_folder, item.get_name()).replace("\\","/")
            save_content_to_file(content, chapter_filename)
        elif item.get_type() == ebooklib.ITEM_IMAGE:
            # Handle image items (if needed)
            img_filename = item.get_name()
            img_content = item.get_content()

            if img_content:
                img_path = os.path.join(output_folder, img_filename)
                save_content_to_file(img_content, img_path)

# Function to extract and save chapter metadata to a JSON file
def extract_and_save_chapter_metadata(book, output_folder):
    chapter_metadata = {
        'url': output_folder,
        'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '',
        'cover': 'OEBPS/Images/CoverDesign.jpg',  # Replace with the actual cover path
        'genre': 'light novel',  # Replace with the genre
        'summary': 'N/A',  # Replace with the summary
        'authors': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '',
        'artist': '',  # Replace with the artist information
        'chapters': []
    }

    # Iterate through the book's items to extract chapter metadata
    i = 0
    for item in book.get_items():
        if item.media_type == 'application/xhtml+xml':
            # Extract chapter title from HTML content
            # chapter_title = extract_chapter_title(item) if extract_chapter_title(item) != 0 else "Unknown chapter" + i
            chapter_metadata['chapters'].append({
                'name': "Chapter " + str(i),
                'path': item.file_name
            })
            i = i + 1

    chapter_metadata_filename = os.path.join(output_folder, 'metadata.json')

    with open(chapter_metadata_filename, 'w', encoding='utf-8') as metadata_file:
        json.dump(chapter_metadata, metadata_file, indent=4, ensure_ascii=False)

# Function to extract chapter title from HTML content
def extract_chapter_title(html_item):
    # You may need to implement a more sophisticated logic here
    # to extract chapter titles from the HTML content.
    # This is a simple example, and it may not work for all EPUBs.

    # Extract title from the <title> tag
    title_tag = html_item.content.find(b'<title>')
    if title_tag != -1:
        end_title_tag = html_item.content.find(b'</title>', title_tag)
        if end_title_tag != -1:
            title = html_item.content[title_tag + 7:end_title_tag].decode('utf-8')
            return title

    # If no title is found in <title> tag, you can add custom logic here
    # to extract titles from the HTML content.

    # Return an empty string if no title is found
    return 0

def cleanTitle(dir_name):
    # cleans a string so that it is valid for directories
    pattern = r'[<>:"/\\|?*\x00-\x1F]'
    # Remove any disallowed characters from the directory name string
    clean_dir_name = re.sub(pattern, '', dir_name)
    return clean_dir_name

def parseEpub(epub_path, dest_dir):
    book = epub.read_epub(epub_path)
    name = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown EPUB'
    output_folder = dest_dir + "convertedEpubs/" + cleanTitle(name)
    extract_cover_image(book, output_folder)
    extract_and_save_chapters(book, output_folder)
    extract_and_save_chapter_metadata(book, output_folder)
    return output_folder
