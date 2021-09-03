#!/usr/bin/env python3

"""
Dominik Winkelbauer; Ludwig Kürzinger
Technische Universität München, 2021
"""

from bs4 import BeautifulSoup
import requests
import shutil
import urllib
from pathlib import Path
import json
import os

METADATA_PATH = Path("./librivox-metadata")
DOWNLOAD_DIR = Path("./librivox")

CUSTOM_JSON_PATH = METADATA_PATH / "custom.json"
GERMAN_BOOKS_PATH = METADATA_PATH / "books-German.json"

def custom_settings(id, custom_json_path=CUSTOM_JSON_PATH):
    print(f"Loading custom.json data from {custom_json_path}")
    with open(custom_json_path, 'r') as outfile:
        custom = json.load(outfile)
        if id in custom:
            return custom[id]
        else:
            return {}

class LibriVoxBook:
    def __init__(self, book_id, output_path = None):
        self.book_id = book_id
        self.url = f"https://librivox.org/rss/{book_id}"
        self.chapters = self.read(book_id)
        self.download_urls = self.get_urls(self.chapters)
        if output_path:
            self.download_and_convert(self.download_urls, output_path)

    @staticmethod
    def read(book_id):
        url = f"https://librivox.org/rss/{book_id}"
        header = "Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0"
        chapters = None
        try:
            r = requests.get(url, header)
            status_code = r.status_code
        except Exception as e:
            print(f'Error fetching the Book {book_id}, {e.__class__}: {e}')
        try:
            soup = BeautifulSoup(r.text, 'lxml')
            chapters = soup.findAll('item')
        except Exception as e:
            print(f'Could not parse the xml: {url}')
            print(e)
        return chapters

    @staticmethod
    def get_urls(chapters):
        urls = []
        for chp in chapters:
            url = chp.find('enclosure').get_attribute_list("url")[0]
            urls += [url]
        return urls

    @staticmethod
    def download_and_convert(download_urls, output_path):
        download_dir = Path(output_path / "download")
        download_dir.mkdir(exist_ok=True, parents=True)
        for i, chapter in enumerate(download_urls):
            audio_file_name = download_dir / f"audio-{i+1}.mp3"
            if not audio_file_name.exists():
                print(f"Download: {chapter} to {audio_file_name}")
                try:
                    urllib.request.urlretrieve(chapter, audio_file_name)
                except KeyboardInterrupt:
                    if audio_file_name.exists():
                        os.remove(audio_file_name)
            else:
                print(f"Audio found for {chapter} - {audio_file_name.stem}")
        wav_dir = (output_path / "wav")
        if wav_dir.exists():
            shutil.rmtree(str(wav_dir))
        wav_dir.mkdir(exist_ok=True, parents=True)
        for audio_file in download_dir.iterdir():
            fname = wav_dir / (audio_file.name[:audio_file.name.rfind(".")] + ".wav")
            os.system("ffmpeg -i " + str(audio_file) + " -ac 1 -ar 16000 " + str(wav_dir / fname))


# Note that the data hoster has download limits,
# and that you may have to restart the download
# after some time.
with open(GERMAN_BOOKS_PATH) as f:
    librivox_booklist = json.load(f)
book_dict = {}
print(f"Downloading books to {DOWNLOAD_DIR}")
for book in librivox_booklist:
    settings = custom_settings(book["id"])
    if "skip" in settings and settings["skip"]:
        print(f"Skipping Book #{book['id']}")
        continue
    else:
        print(f"-- Book #{book['id']}")
    output_path = Path(DOWNLOAD_DIR /  str(book["id"]))
    book_dict[book["id"]] = LibriVoxBook(book["id"], output_path=output_path)

