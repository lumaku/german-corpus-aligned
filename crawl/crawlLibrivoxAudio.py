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
from utility import chapter_num_from_wav
import urllib.request
from utility import custom_settings
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--id', type=int, default=None)
parser.add_argument('--textOnly', action='store_true', default=False)
parser.add_argument('--force', action='store_true', default=False)
args = parser.parse_args()

class GutenbergSpiegelSpider(scrapy.Spider):

    def __init__(self, url, num_chapters, **kwargs):
        self.name = "GutenbergSpiegel"
        self.start_urls = [url]
        self.num_chapters = num_chapters
        super().__init__(**kwargs)

    def parse(self, response):
        yield response.follow(response.request.url[:response.request.url.rfind("/")], self.parse_summary, headers={"chapter_offset": int(response.request.url[response.request.url.rfind("/") + 1:]) - 1})

    def parse_summary(self, response):
        chapters = response.css('#gutenb > a::attr("href")').getall()
        # if len(chapters) == self.num_chapters + 1:
        #    chapters = chapters[1:]
        #    offset = 1
        # elif len(chapters) == self.num_chapters:
        #    offset = 0
        # else:
        #    raise scrapy.exceptions.CloseSpider("InvalidNumberChapters")
        chapters = chapters[int(response.request.headers["chapter_offset"]):]
        for chapter in chapters:
            yield response.follow(chapter, self.parse_chapter, headers={"chapter_num": int(chapter[chapter.rfind("/") + 1:]) - int(response.request.headers["chapter_offset"])})

    def parse_chapter(self, response):
        ignore = True
        paragraphs = []

        def append_par(p, text):
            nonlocal ignore
            text = text.strip()
            if len(text) > 0:
                paragraphs.append(text)
                if p.root.tag == "p" or p.root.tag == "td":
                    ignore = False

        for p in response.css("#gutenb > p, #gutenb > h2, #gutenb > h3, #gutenb > h4, #gutenb > .poem td:last-child"):
            text = ""
            tags = p.xpath("(*[not(@class='footnote' or @class='speaker')]|text()[not(ancestor::*[@class='footnote' or @class='speaker'])])")
            for t in tags:
                if hasattr(t.root, "attrib") and "class" in t.root.attrib and t.root.attrib["class"] == "regie":
                    append_par(p, text)
                    append_par(p, remove_tags(t.extract()))
                    text = ""
                else:
                    text += remove_tags(t.extract())
            append_par(p, text)

        if ignore:
            return

        yield {
            'paragraphs': paragraphs,
            "chapter": int(response.request.headers["chapter_num"])
        }


class ZenoSpider(scrapy.Spider):

    def __init__(self, url, num_chapters, **kwargs):
        self.name = "ZenoSpider"
        self.start_urls = [url]
        self.num_chapters = num_chapters
        super().__init__(**kwargs)

    #def parse(self, response):
    #    menu = response.css('.zenoCOMain .zenoTRNavBottom').getall()
    #    
    #    if len(menu) > 0:
    #        yield response.follow(response.request.url, self.parse_summary , headers={"chapter_offset": 0})
    #    else:
    #        yield response.follow(response.request.url, self.parse_chapter, headers={"chapter_num": 1})

    #def parse_summary(self, response):
       
    def parse(self, response):
        yield response.follow(response.request.url, self._parse , headers={"chapter_offset": 0, "chapter_num": "1"})

    def _parse(self, response):
        chapter_num = response.request.headers["chapter_num"].decode("utf-8")
        menu = response.css('.zenoCOMain .zenoTRNavBottom').getall()

        subchapter_text = response.css('.zenoCOMain a.zenoTXLinkInt').xpath("../text()").extract_first()
        if subchapter_text is not None:
            subchapter_text = subchapter_text.strip()

        if subchapter_text != '•' or len(menu) > 0:
            ignore = True
            paragraphs = []

            def append_par(p, text):
                nonlocal ignore
                text = text.strip()
                if len(text) > 0:
                    paragraphs.append(text)
                    if p.root.tag == "p":
                        ignore = False

            for p in response.css(".zenoCOMain > p, .zenoCOMain > h2, .zenoCOMain > h3, .zenoCOMain > h4, .zenoCOMain > h5"):
                text = ""
                tags = p.xpath(".//text()[not(ancestor::*[@class='zenoTXKonk' or @class='zenoTXFnRef' or @class='zenoPC' or @class='zenoTXLinkInt'])]")
                for t in tags:
                    text += remove_tags(t.extract())
                append_par(p, text)

            if not ignore:  
                yield {
                    'paragraphs': paragraphs,
                    "chapter": chapter_num
                }

        chapters = response.css('.zenoCOMain li a, .zenoCOMain a.zenoTXLinkInt')
        sub_chapter_num = 1
        for chapter in chapters:
            chapter_text = chapter.xpath("../text()").extract_first()
            chapter_class = chapter.xpath("./@class").extract_first()

            if chapter_class != "zenoTXLinkInt" or (chapter_text is not None and chapter_text.strip() == '•'):
                chapter_link = chapter.xpath("./@href").extract_first()
                yield response.follow(chapter, self._parse, headers={"chapter_num": chapter_num + "-" + str(sub_chapter_num)})
                sub_chapter_num += 1


class LibrivoxSpider(scrapy.Spider):

    def __init__(self, url, **kwargs):
        self.name = "LibrivoxSpider"
        self.start_urls = [url]
        super().__init__(**kwargs)

    def parse(self, response):
        i = 1
        for tr in response.css(".chapter-download tbody tr"):
            chapter_name = tr.xpath("normalize-space(descendant-or-self::*[@class='chapter-name'])").extract_first()
            audio_url = tr.css('a.play-btn::attr("href")').extract_first()
            yield {
                "number": i,
                'chapter_name': chapter_name,
                "audio_url": audio_url
            }
            i += 1


Path("data/librivox/wav").mkdir(exist_ok=True, parents=True)

with open('data/librivox/metadata/books-German.json', 'r') as outfile:
    books = json.load(outfile)

for book in books:
    output_dir = Path("data/librivox/wav/" + book["id"] + "/")

    if book["url_zip_file"] != "" and (not output_dir.exists() or args.force) and (args.id is None or str(args.id) == book["id"]):
        settings = custom_settings("librivox", book["id"])
        if "skip" in settings and settings["skip"]:
            continue

        if "url_text_source" in settings:
            url_text_source = settings["url_text_source"]
        else:
            url_text_source = book["url_text_source"].strip()

        domain = url_text_source[url_text_source.find("//") + 2:]
        domain = domain[:domain.find("/")]
        if domain == "gutenberg.spiegel.de" and not url_text_source.startswith("http://gutenberg.spiegel.de/autor/"):
            spider = GutenbergSpiegelSpider
        elif domain == "www.zeno.org":
            spider = ZenoSpider
        else:
            continue

        print(str(output_dir))
        output_dir.mkdir(exist_ok=True)

        metadata_file = output_dir / "metadata.json"
        if metadata_file.exists():
            metadata_file.unlink()


        def _crawl_librivox():
            process = CrawlerProcess({
                'FEED_FORMAT': 'json',
                'FEED_URI': str(metadata_file)
            })
            process.crawl(LibrivoxSpider, url=book["url_librivox"])
            process.start()


        p = mp.Process(target=_crawl_librivox)
        p.start()
        p.join()

        with open(str(metadata_file), 'r') as f:
            metadata = json.load(f)

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
            process.crawl(spider, url=url_text_source, num_chapters=int(book["num_sections"]), chapter_offset=1, headers={"is_first": True})  # url="https://gutenberg.spiegel.de/buch/gesammelte-schriften-758/", num_chapters=25)

            process.start(True)
            process.join()


        p = mp.Process(target=_crawl, args=(crawl_failed,))
        p.start()
        p.join()

        if crawl_failed.value or os.stat(str(output_file)).st_size == 0 or args.textOnly:
            exit(0)
            continue

        download_dir = (output_dir / "download")
        download_dir.mkdir(exist_ok=True)
        print("Download wav")
        for chapter in metadata:
            print("Download: " + chapter["chapter_name"])
            urllib.request.urlretrieve(chapter["audio_url"], str(download_dir / ("audio-" + str(chapter["number"]) + ".mp3")))

            
        wav_dir = (output_dir / "wav")
        if wav_dir.exists():
            shutil.rmtree(str(wav_dir))
        wav_dir.mkdir(exist_ok=True)
        for file in download_dir.iterdir():
            os.system("ffmpeg -i " + str(file) + " -ac 1 -ar 16000 " + str(wav_dir / (file.name[:file.name.rfind(".")] + ".wav")))

        shutil.rmtree(str(download_dir))
        exit(0)
