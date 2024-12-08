# import openai
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set")
else:
    print("API Key loaded successfully!")

# Get the Gemini API key from environment variables
genai.configure(api_key=api_key)

# ## The following code is using OpenAI API
# def translate(word: str, sentence: str) -> str:
#     completion = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {
#                 "role": "system",
#                 "content": "You are a helpful assistant who is good on math.",
#             },
#             {"role": "user",
#              "content": "You are a experienced translator for English and Chinese. Detect the given language, "
#                         "and translate it into the other language among English and Simplified Chinese. Then translate given word \"{}\" in sentence \"{}\". Keep the translation short.".format(word, sentence)},
#         ],
#     )
#     return completion.choices[0].message.content

## The following code is using Google Gemini API
def translate(word: str, sentence: str) -> str:
    word = _preprocess_word(word)
    # Define the prompt for translation
    # ToDo(Qin): Improve the prompt
    prompt = (f"Translate the word \"{word}\" in the context of the sentence \"{sentence}\" from English to simplified "
              f"Chinese or vice versa. Keep the translation short and ensure the translation is " \
             f"accurate and contextually appropriate. Provide the translated word in written format only, "
              f"not the entire sentence, and also not the pinyin.")
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    translated_text = response.text.strip()

    # For debugging
    print("----\nword: \"{}\"\nsentence: \"{}\"\ntranslation: {}\n".format(word, sentence, translated_text))
    return translated_text

# Remove punctuations at the beginning or the end of the word. The word is either in English or Simplified Chinese.
def _preprocess_word(word: str) -> str:
    word = word.strip(".,?!\"'()[]{}:;—-!~@#$\\/%^&*_|<>").strip()
    return word

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
