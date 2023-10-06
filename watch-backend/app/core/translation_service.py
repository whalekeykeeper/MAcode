import re

import openai


def translate(word: str, sentence: str) -> str:
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant who is good on math.",
            },
            {"role": "user",
             "content": "You are a experienced translator for English and Chinese. Detect the given language, "
                        "and translate it into the other language among English and Simplified Chinese. Then translate given word \"{}\" in sentence \"{}\". Keep the translation short.".format(word, sentence)},
        ],
    )
    return completion.choices[0].message.content


def stat(text: str) -> []:
    sentences = re.split("[?.,!]", text)
    nonempty_sentences = list(filter(None, sentences))
    word_count = 0
    for e in nonempty_sentences:
        e = e.replace("?", " ").replace(",", " ").replace(".", " ").replace("!", " ")
        words = e.split(" ")
        word_count += len(words)

    return len(nonempty_sentences), word_count


if __name__ == "__main__":
    pass
