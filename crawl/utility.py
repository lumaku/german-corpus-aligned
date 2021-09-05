import json
from somajo import Tokenizer
from num2words import num2words

def chapter_num_from_wav(path_wav):
    if path_wav.startswith("audio-"):
        return int(path_wav[len("audio-"):-len(".wav")])
    else:
        for part in path_wav.split('_'):
            if part.isdigit():
                return int(part)
        for part in path_wav.split('_'):
            if part.startswith("kap") and part[len("kap"):].isdigit():
                return int(part[len("kap"):])
            if part.startswith("akt") and part[len("akt"):].isdigit():
                return int(part[len("akt"):])
        raise ValueError("chapter num not found in path!"+str(path_wav))
           
def format_time(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

def custom_settings(source, id):
    with open('data/' + source + '/metadata/custom.json', 'r') as outfile:
        custom = json.load(outfile)
        if id in custom:
            return custom[id]
        else:
            return {}
