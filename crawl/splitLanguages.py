import json


with open('data/librivox/metadata/books.json', 'r') as outfile:
    books = json.load(outfile)

books_per_language = {}
for book in books:
    if book["language"] not in books_per_language:
        books_per_language[book["language"]] = []
    books_per_language[book["language"]].append(book)

for language in books_per_language:
    with open('data/librivox/metadata/books-' + language.replace("/", "-") + '.json', 'w') as outfile:
        json.dump(books_per_language[language], outfile)
    print(language, len(books_per_language[language]))
