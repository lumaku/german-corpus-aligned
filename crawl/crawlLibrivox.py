import requests
import json
from pathlib import Path

books = []
index = 0
batch_size = 50

p = Path('data/librivox/metadata')
p.mkdir(exist_ok=True, parents=True)

while True:
    r = requests.get("https://librivox.org/api/feed/audiobooks/?format=json&extended=0&limit=" + str(batch_size) + "&offset=" + str(index))
    if r.status_code != 200:
        break
    books.extend(r.json()["books"])
    print(index, len(r.json()["books"]))
    index += batch_size


with open(str(p / "books.json"), 'w') as outfile:
    json.dump(books, outfile)

