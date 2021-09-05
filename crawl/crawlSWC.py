import requests
import json
from pathlib import Path

p = Path('data/swc/metadata')
p.mkdir(exist_ok=True, parents=True)

cont = ""
pages = []
while True:
    r = requests.get("https://de.wikipedia.org/w/api.php?action=query&format=json&prop=&list=categorymembers&titles=&cmtitle=Kategorie%3AWikipedia%3AGesprochener_Artikel&cmtype=page%7Csubcat%7Cfile&cmlimit=max&cmcontinue=" + cont)
    result = r.json()
    pages.extend(result["query"]["categorymembers"])
    if "continue" in result:
        cont = result["continue"]["cmcontinue"]
    else:
        break

with open(str(p / "pages.json"), 'w') as outfile:
    json.dump(pages, outfile)