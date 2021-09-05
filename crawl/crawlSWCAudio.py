import json
from pathlib import Path

import scrapy
from scrapy.crawler import CrawlerProcess
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
import os
import shutil
from scrapy import signals
from scrapy.signalmanager import dispatcher
import multiprocessing as mp
from multiprocessing import Queue
from tqdm import tqdm
from scrapy.utils.markup import remove_tags
from utility import chapter_num_from_wav, custom_settings
import urllib.request
import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument('--id', type=int, default=None)
parser.add_argument('--textOnly', action='store_true', default=False)
parser.add_argument('--force', action='store_true', default=False)
args = parser.parse_args()

class WikipediaSpider(scrapy.Spider):

    def __init__(self, url, **kwargs):
        self.name = "WikipediaSpider"
        self.start_urls = [url]
        super().__init__(**kwargs)

    def parse(self, response):
        chapter_num = 1
        box = response.css("#Vorlage_Gesprochene_Version")
        if len(box) > 0:
            for part in box[0].css("tr"):
                info_url = part.xpath(".//a[contains(text(),'Informationen')]/@href").extract_first()
                audio_url = part.css('.internal::attr("href")').extract_first()
                text_url = part.css('.text::attr("href")').extract_first()
                if audio_url is not None:
                    yield response.follow("https://de.wikipedia.org" + info_url, self.parse_information, headers={"chapter_num": chapter_num, "audio_url": audio_url, "text_url": text_url})
                    chapter_num += 1

    def parse_information(self, response):
        date = None
        for tr in response.css(".mw-content-ltr tr"):
            key = tr.xpath("td[position()=1]/text()").extract_first()
            if key == "Datum":
                date = tr.xpath("td[position()=2]//time/@datetime").extract_first()

        if response.request.headers["text_url"] is None:
            text_url = None
        else:
            text_url = response.request.headers["text_url"].decode("utf-8")

        if response.request.headers["audio_url"] is not None:
            yield {
                "audio_url": response.request.headers["audio_url"].decode("utf-8"),
                "text_url": text_url,
                "date": date,
                "number": response.request.headers["chapter_num"].decode("utf-8")
            }

class WikipediaTextSpider(scrapy.Spider):

    def __init__(self, url, **kwargs):
        self.name = "WikipediaTextSpider"
        self.start_urls = [url]
        super().__init__(**kwargs)

    def parse(self, response):
        paragraphs = []

        def append_par(p, text):
            text = text.strip()
            if len(text) > 0:
                paragraphs.append(text)

        for p in response.css(".mw-parser-output > p, .mw-parser-output > .Vorlage_Zitat p, .mw-parser-output > ul > li, .mw-parser-output > ol > li, .mw-parser-output > h1, .mw-parser-output > h2, .mw-parser-output > h3, .mw-parser-output > dl > dt, .mw-parser-output > dl > dd"):
            text = ""
            tags = p.xpath("(*[not(@class='editoronly' or @class='reference' or @class='mwe-math-element' or @class='IPA' or name()='style')]|text()[not(ancestor::*[@class='editoronly' or @class='reference' or @class='mwe-math-element' or @class='IPA' or name()='style'])])")
            for t in tags:                
                text += remove_tags(t.extract())
            append_par(p, text)

        yield {
            'paragraphs': paragraphs,
            "chapter": 1
        }       



Path("data/swc/wav").mkdir(exist_ok=True)

with open('data/swc/metadata/pages.json', 'r') as outfile:
    pages = json.load(outfile)

for page in pages:
    output_dir = Path("data/swc/wav/" + str(page["pageid"]) + "/")

    if (not output_dir.exists() or args.force or not (output_dir / "wav").exists()) and (args.id is None or args.id == page["pageid"]):
        settings = custom_settings("swc", str(page["pageid"]))
        if "skip" in settings and settings["skip"]:
            continue
            
        print(str(output_dir))
        output_dir.mkdir(exist_ok=True)

        metadata_file = output_dir / "metadata.json"
        if metadata_file.exists():
            metadata_file.unlink()


        def _crawl_metadata():
            process = CrawlerProcess({
                'FEED_FORMAT': 'json',
                'FEED_URI': str(metadata_file)
            })
            process.crawl(WikipediaSpider, url="https://de.wikipedia.org/wiki?curid=" + str(page["pageid"]))
            process.start()


        p = mp.Process(target=_crawl_metadata)
        p.start()
        p.join()


        if os.stat(str(metadata_file)).st_size == 0:
            continue

        with open(str(metadata_file), 'r') as f:
            metadata = json.load(f)

        if metadata[0]["text_url"] is None and metadata[0]["date"] is None:
            continue

        output_file = output_dir / "text-raw.json"
        if output_file.exists():
            output_file.unlink()

        crawl_failed = mp.Value('b', False)

        def _crawl(crawl_failed):
            def crawler_error(failure, response, spider):
                crawl_failed.value = True

            dispatcher.connect(crawler_error, signal=signals.spider_error)

            process = CrawlerProcess({
                'FEED_FORMAT': 'json',
                'FEED_URI': str(output_file)
            })

            if metadata[0]["text_url"] is None:
                date = metadata[0]["date"]
                if ":" in date:
                    date = date.replace(" ", "T") + "Z"
                else:
                    date = date + "T20:00:00Z"
                r = requests.get("https://de.wikipedia.org/w/api.php?action=query&format=json&prop=revisions&pageids=" + str(page["pageid"]) + "&rvprop=ids%7Ctimestamp%7Cflags%7Ccomment%7Cuser&rvlimit=1&rvstart=" + date )
                result = r.json()

                process.crawl(WikipediaTextSpider, url="https://de.wikipedia.org/w/index.php?oldid=" + str(result["query"]["pages"][str(page["pageid"])]["revisions"][0]["revid"]))
            else:
                process.crawl(WikipediaTextSpider, url=metadata[0]["text_url"])
            
            process.start(True)
            process.join()


        p = mp.Process(target=_crawl, args=(crawl_failed,))
        p.start()
        p.join()

        if crawl_failed.value or os.stat(str(output_file)).st_size == 0 or args.textOnly:
            continue

        download_dir = (output_dir / "download")
        download_dir.mkdir(exist_ok=True)
        print("Download wav")
        for chapter in metadata:
            print("Download: " + str(chapter["number"]))
            urllib.request.urlretrieve("http:" + chapter["audio_url"], str(download_dir / ("audio-" + str(chapter["number"]) + ".mp3")))

        wav_dir = (output_dir / "wav")
        if wav_dir.exists():
            shutil.rmtree(str(wav_dir))
        wav_dir.mkdir(exist_ok=True)
        for file in download_dir.iterdir():
            os.system("ffmpeg -i " + str(file) + " -ac 1 -ar 16000 " + str(wav_dir / (file.name[:file.name.rfind(".")] + ".wav")))

        shutil.rmtree(str(download_dir))
        #exit(0)
