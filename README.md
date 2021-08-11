# German Speech Corpus aligned with CTC segmentation

Alignments on Librivox and Spoken Wikipedia Corpus (SWC) with CTC segmentation:

| Dataset  | Length | Speakers | Utterances |
|----------|--------|----------|------------|
| SWC      | 210h   | 363      | 78214      |
| Librivox | 804h   | 251      | 368532     |

This repository contains pre-processed text and alignments. Both corpora are combined to one recipe, audio file and corpus can be attributed by file names and utterance IDs. The audio files can be downloaded separately:

* SWC: [German Spoken Wikipedia Corpus](https://nats.gitlab.io/swc/)
* Librivox: from the IDs in the metadata file `books-German.json`. Audiofiles can be automatically retrieved via `id` using the LibriVox API, e.g. https://librivox.org/api/feed/audiobooks/?id=82&format=json , and then downloading the URL.

For librivox, the naming scheme is `librivox_{book_id}_{chapter}_{utterance_id}`. The separate file `librivox_utt2spk` contains speaker information.

Further description can be found in the CTC segmentation paper (on [Springer Link](https://link.springer.com/chapter/10.1007%2F978-3-030-60276-5_27), on [ArXiv](https://arxiv.org/abs/2007.09127))


