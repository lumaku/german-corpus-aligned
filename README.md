# German Speech Corpus aligned with CTC segmentation

Alignments on Librivox and Spoken Wikipedia Corpus (SWC) with CTC segmentation:

| Dataset  | Length | Speakers | Utterances |
|----------|--------|----------|------------|
| SWC      | 210h   | 363      | 78214      |
| Librivox | 804h   | 251      | 368532     |

This repository contains pre-processed text and alignments. Both corpora are combined to one recipe, audio file and corpus can be attributed by file names and utterance IDs. The audio files can be downloaded separately:

* SWC: [German Spoken Wikipedia Corpus](https://nats.gitlab.io/swc/)
* Librivox: The audio files can be retrieved via IDs in the metadata file `books-German.json` and then automatically retrieved via `id` using the LibriVox API, e.g. https://librivox.org/api/feed/audiobooks/?id=82&format=json , and then downloading the URL. As downloading the files separately takes time, there is an MP3 boundle is available at [the MMK website](https://www.ei.tum.de/mmk/verschiedenes/german-speech-corpus-aligned-with-ctc-segmentation/).

For librivox, the naming scheme is `librivox_{book_id}_{chapter}_{utterance_id}`. The separate file `librivox_utt2spk` contains speaker information.

A pretrained ASR model (Transformer) is in the Releases section of this repository.

Further description can be found in the CTC segmentation paper (on [Springer Link](https://link.springer.com/chapter/10.1007%2F978-3-030-60276-5_27), on [ArXiv](https://arxiv.org/abs/2007.09127))


