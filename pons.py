from datetime import date
import json
from typing import List
import urllib.request

import argparse
from logging import getLogger
from deep_translator import GoogleTranslator
from deep_translator.exceptions import RequestError
from custom import deutsch_file, english_file, eInput, dInput, ANKI_PORT

logger = getLogger("main")
translated_words = list()
not_translated_words = list()
duplicated_words = list()
translations_display_list = list()


class WordNotFoundException(Exception):
    """
    Raise when it cannot be translated

    Arguments:
        Exception {} -- WordNotFoundException
    """
    pass


class CannotPatchIntoAnkiException(Exception):
    """
    Raise when cannot connect to Anki Services

    Arguments:
        Exception {} -- CannotPatchIntoAnkiException
    """
    pass


class DuplicatedWordException(Exception):
    """
    Raise when it cannot be translated

    Arguments:
        Exception {} -- WordNotFoundException
    """
    pass


def performTranslation(word, language='english'):
    """
    Performs translation

    Arguments:
        word {_type_} -- Word to ebe translated

    Keyword Arguments:
        language {string} -- Which Language to translate from (default: {'english'})

    Raises:
        exc: Cannot do Translation

    Returns:
        _type_ -- The translated word
    """
    pons = GoogleTranslator(source=language, target='slovenian')
    try:
        return pons.translate(word)
    except RequestError:
        pass


def parseArguments():
    """
    Parse Arguments
    Returns: argparse.Parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-lang", type=str, default='German',
                        help="German or English boolean")

    args = parser.parse_args()
    return args


def concatenateListIntoString(s):
    t = ""
    for k in s:
        t += f"{k}, "
    return t.rstrip(", ")

def display_translations():
    t = ""
    for k in range(len(translations_display_list)):
        if k == 0:
            t += f"\n{translations_display_list[k]}"
        else: t += translations_display_list[k]
    print(f"🍒 Please find the expected translations below :)\n{t}") if len(translations_display_list) != 0 else ""

def get_words(file=eInput):
    l = []
    with open(file, 'r') as f:
        for row in f:
            row = row.rstrip("\n")
            l.append(row)
    return l


def request(action, **params):
    """
    HTTP Request

    Arguments:
        action {_type_} -- _description_

    Returns:
        _type_ -- _description_
    """
    return {'action': action, 'params': params, 'version': 6}


def invokeAnkiAPI(action, **params):
    """
    Invoke the PonsAPI Translator

    Arguments:
        action {HTTPRequest} 

    Raises: Exceptions

    Returns:
        A translation
    """
    duplicated = False
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(
        urllib.request.Request(ANKI_PORT, requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] == "cannot create note because it is a duplicate ":
        duplicated = True
        pass
    elif response['error'] is not None:
        pass
    return response, duplicated

def build_the_report(lang = 'German'):
    """
    Building up the Translation Report

    Keyword Arguments:
        lang {str} -- Language to translate from (default: {'english'})
    """
    input_file = eInput if lang == 'English' else eInput
    with open(input_file, 'r') as file:
        words_to_be_translated = len(file.readlines())

    words_word = 'words' if words_to_be_translated > 1 else 'word'

    print(f"📚  Building Up the Translation Report on Day: '{date.today()}'. \n\n🏟️  We seek to translate {words_to_be_translated} {words_word} into '{lang}'.\n")
    if translated_words:
        print(f"✅ Successfully Translated the Following Words:\n {concatenateListIntoString(translated_words)}\n")
    if not_translated_words:
        print(
            f"❌ Could not translate the following words:\n {concatenateListIntoString(not_translated_words)}\n")
    if duplicated_words:
        print(
            f"🫶  Certain Duplications seem to have been found:\n {concatenateListIntoString(duplicated_words)}\n")

    display_translations()

def main():
    args = parseArguments()
    if args.lang == 'German':
        input_file, file = dInput, deutsch_file
        deck_name = "german"
        language = "de"
    else:
        input_file, file = eInput, english_file
        deck_name = "english"
        language = "en"

    words = get_words(input_file)
    for word in words:
        try:
            translated = performTranslation(
                word, language=language)
                        
            if not translated:
                logger.info(f"The word: '{word}' could not be translated :(")
                not_translated_words.append(word)
                pass

            # Store into Corpus
            with open(file, 'a') as f:
                printed_word = word.strip() + " -- " + translated + "\n"
                f.write(printed_word) if printed_word is not None else logger.info(
                    f"The word: '{word}' could not be translated :(")

        except FileNotFoundError as exc:
            logger.info(f"File '{file}' could not be found. ")
            raise exc

        note = {
            "deckName": deck_name,
            "modelName": "Basic-fbf65",
            "fields": {
                "Front": word.strip(),
                "Back": printed_word.strip()
            }
        }
        translations_display_list.append(printed_word)

        try:
            _, duplicated = invokeAnkiAPI('addNote', note=note) 
            duplicated_words.append(word) if duplicated else translated_words.append(word)
        except CannotPatchIntoAnkiException as exc:
            logger.info(f"Cannot connect to Anki on port: '{ANKI_PORT}'.")
            pass

    # Build the Report in CMD
    build_the_report(lang=args.lang)    

if __name__ == "__main__":
    main()
