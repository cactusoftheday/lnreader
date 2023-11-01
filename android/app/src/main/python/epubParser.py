import json
import os
import zipfile

import ebooklib
from ebooklib import epub
import xml.etree.ElementTree as ET
import re

from lxml import etree

namespaces = {
    'calibre': 'http://calibre.kovidgoyal.net/2009/metadata',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'opf': 'http://www.idpf.org/2007/opf',
    'ncx': 'http://www.daisy.org/z3986/2005/ncx/',
    'u': 'urn:oasis:names:tc:opendocument:xmlns:container',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xhtml': 'http://www.w3.org/1999/xhtml'
}

def getCover(epub_path):
    with zipfile.ZipFile(epub_path) as z:
        for filename in z.namelist():
            if (filename.endswith('opf')):
                contentOPF = filename  # search for opf file

        tree = etree.XML(z.read(contentOPF))
        coverHREF = None

        try:
            coverID = tree.xpath("//opf:metadata/opf:meta[@name='cover']", namespaces=namespaces)[0].get('content')
            # print('coverID 2', coverID)  # now we know where the cover image is located
            coverHREF = tree.xpath("//opf:manifest/opf:item[@id='" + coverID + "']", namespaces=namespaces)[0].get(
                'href')

        except IndexError:  # not an EPUB 2.0
            # print('EPUB 2 failure')
            pass

        if not coverHREF:  # try EPUB 3.0
            try:
                coverHREF = tree.xpath("//opf:manifest/opf:item[@properties='cover-image']", namespaces=namespaces)[
                    0].get('href')
            except IndexError:
                # print('EPUB 3 failure')
                pass
        elif not coverHREF:  # some EPUBs don't explicitly declare cover images
            try:
                coverID = tree.xpath("//opf:spine/open:itemref[@idref='cover']", namespaces=namespaces)[0].get('idref')
                temp = tree.xpath("//opf:manifest/opf:item[@id='" + coverID + "']", namespaces=namespaces)[0].get(
                    'href')

                tree = etree.fromstring(z.read(temp))
                coverHREF = tree.xpath('//xhtml:img', namespaces=namespaces)[0].get('src')
            except IndexError:
                print('Edge case failure')
        elif not coverHREF:
            # print('No cover found')
            return None

        coverPath = coverHREF.replace('\\', '/')
        # print('coverPath', coverPath)

        return coverPath if os.path.dirname(contentOPF) == 0 else os.path.dirname(contentOPF) + '/' + coverPath

# Function to save content to a file
def saveContentToFile(content, filename):
    # Ensure the directory where the file will be saved exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Write the content to the file
    with open(filename, 'wb') as file:
        file.write(content)

def ensureDirExists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to extract text and images from chapters
def extractAndSaveChapters(book, output_folder):
    # Create the output folder if it doesn't exist
    ensureDirExists(output_folder)

    # Iterate through all the items in the book
    for item in book.get_items():
        # Check if the item is of type ITEM_DOCUMENT (HTML content)
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()

            # Extract and save the content to a file
            chapter_filename = os.path.join(output_folder, item.get_name()).replace("\\","/")
            saveContentToFile(content, chapter_filename)
        elif item.get_type() == ebooklib.ITEM_IMAGE:
            # Handle image items (if needed)
            img_filename = item.get_name()
            img_content = item.get_content()

            if img_content:
                img_path = os.path.join(output_folder, img_filename)
                saveContentToFile(img_content, img_path)
        elif item.get_type() == ebooklib.ITEM_STYLE:
            saveContentToFile(item.get_content(), os.path.join(output_folder,item.get_name()))
        elif item.get_type() == ebooklib.ITEM_FONT:
            #print("font")
            saveContentToFile(item.get_content(), os.path.join(output_folder,item.get_name()))
        elif item.get_type() == ebooklib.ITEM_NAVIGATION:
            tree = ET.ElementTree(ET.fromstring(item.get_content()))
            root = tree.getroot()
            chapterDict = {}
            for navPoint in root.iter('{http://www.daisy.org/z3986/2005/ncx/}navPoint'):
                # Extract the chapter title and content (file name)
                chapter_title = navPoint.find('{http://www.daisy.org/z3986/2005/ncx/}navLabel/{http://www.daisy.org/z3986/2005/ncx/}text').text
                chapter_content = navPoint.find('{http://www.daisy.org/z3986/2005/ncx/}content').get('src')
                #print(chapter_title, chapter_content)
                chapterDict[chapter_title] = chapter_content

    return chapterDict
    # There may be more than just fonts and styles however I don't want to extract everything else

# Function to extract and save chapter metadata to a JSON file
def saveMetadata(book, output_folder, epub_path, chapterDict):
    chapter_metadata = {
        'url': output_folder,
        'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '',
        'cover': getCover(epub_path),  # Replace with the actual cover path
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
            fileName = item.file_name
            matchingChapter = [(key, value) for (key, value) in chapterDict.items() if fileName in value]
            if len(matchingChapter) > 0:
                chapter_metadata['chapters'].append({
                    'name': matchingChapter[0][0],
                    'path': fileName
                })
            else:
                chapter_metadata['chapters'].append({
                    'name': "Unnamed Chapter " + str(i),
                    'path': fileName
                })
            i = i + 1

    chapter_metadata_filename = os.path.join(output_folder, 'metadata.json')

    with open(chapter_metadata_filename, 'w', encoding='utf-8') as metadata_file:
        json.dump(chapter_metadata, metadata_file, indent=4, ensure_ascii=False)

# Function to extract chapter title from HTML content
def extractChapterTitle(html_item):
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
    chapterDict = extractAndSaveChapters(book, output_folder)
    saveMetadata(book, output_folder, epub_path, chapterDict)
    return output_folder
