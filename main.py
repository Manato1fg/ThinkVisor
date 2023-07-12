from sklearn.manifold import TSNE
import numpy as np
from sentence_transformers import SentenceTransformer
import csv
import pickle
import json
import random

import deepl
import openai

from flask import Flask, render_template, request, jsonify, Response
import requests

import sys

from googleapiclient.discovery import build


OPENAI_API_KEY = ""  # OpenAIのAPIキーを入れる
openai.api_key = OPENAI_API_KEY

GOOGLE_CUSTOM_SEARCH_API_KEY = ""  # Google Custom Search APIのAPIキーを入れる
CSE_ID = ""  # Google Custom Search EngineのIDを入れる

INSTRUCTION1 = """
You are a professional AI assistant that analyzes the opinions of comments from the reactions.
You will be given comments and reactions in JSON format, so you will need to analyze the trend of opinions based on that information and the reaction, and verbalize what kind of opinions the user has.
Reaction is an indicator to show whether the user likes that comment or not.
Follow the instructions below.
- You must explain especially what perspectives the user emphasizes.
- You don't have to explain the given comments and reactions.
- You must answer in Japanese.
- Your answer must follow FORMAT below. Replace {{something}} and {perspective} with your answer.
    - {{something}} must be written in fewer than 75 characters in Japanese.
    - {perspective} must be written in fewer than 8 characters in Japanese.
- Seek feedback from stakeholders and see if any corrections or additions are needed before you actually write the analysis.
- Revise your output again as a pro reviser before you send your analysis.

FORMAT: 
あなたの意見を分析した結果をお伝えします。

特にあなたは**{{...}}という視点**を重視しているようです。あなたの意見をまとめると次のようになります。

- {perspective 1}: {{解説1}}
- {perspective 2}: {{解説2}}
...

他にも以下のような観点について調べてみるとより理解が深まります。

- {perspective 1}: {{解説1}}
- {perspective 2}: {{解説2}}
...
"""

INSTRUCTION2 = """
Tell me query for news related to this topic.
Follow the instructions below.
- Keywords must be in Japanese.
- Keywords separated by 'AND' or 'OR'.
- Each topic has title and keywords.
- You can use up to 3 topics.
- You can choose up to 4 news for each topics.
- You must not choose more than 5 topics for each topic.
- Do not output the word "END_ANALYSIS".

FORMAT:
# {{title1}}
- {{query1}}

# {{title2}}
- {{query2}}
"""

app = Flask(__name__)

# ニュースを検索


def search_news(query: str) -> list:
    news = []
    service = build("customsearch",
                    "v1",
                    cache_discovery=False,
                    developerKey=GOOGLE_CUSTOM_SEARCH_API_KEY)
    # CSEの検索結果を取得
    result = service.cse().list(q=query, cx=CSE_ID, num=3, start=0).execute()
    # 検索結果(JSON形式)
    items = result.get("items", [])
    for item in items[:2]:
        title = item["title"]
        link = item["link"]
        img_src = item.get("pagemap", {}).get(
            "cse_thumbnail", [{}])[0].get("src", "")
        news.append({"title": title, "url": link, "image": img_src})
    return news


def md2html(md: str) -> str:
    paragraphs = md.split("\n\n")
    html = ""
    for i in range(len(paragraphs)):
        lines = paragraphs[i].split("\n")
        if lines[0].find("関連するニュース記事") != -1:
            # URL掲載は難しかったので例外処理
            continue
        for line in lines:
            if line.startswith("..."):
                continue
            # 太字の変換
            if line.find("**") != -1 and line.count("**") == 2:
                line = line.replace("**", "<b>", 1)
                line = line.replace("**", "</b>", 1)

            # リストの変換
            if line.startswith("- "):
                html += f"<li>{line[2:]}</li>"
            else:
                html += f"<p>{line}</p>"

        if i != len(paragraphs) - 1:
            html += "<br />"

    return html


data = []
data_index = 0
DATA_COUNT = 3
DATA_TITLE = ["寿司ペロ賠償請求", "寿司ペロ賠償請求2", "部活動の地域移行実験用"]


def ENGLISH_FILE(i: int) -> str:
    return f"./data/translated{i}.csv"


def JAPANESE_FILE(i: int) -> str:
    return f"./data/merge{i}.csv"


def VECTOR_FILE(i: int) -> str:
    return f"./data/vector{i}.pickle"


def PROB_MAT_FILE(i: int) -> str:
    return f"./data/prob_mat_lda_{i}.pickle"


def ITEMS_FILE(i: int) -> str:
    return f"./data/items{i}.pickle"


def shorten(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


def load_data():
    global data

    data = []
    for i in range(DATA_COUNT):
        sentences_en = []  # 翻訳後の文章
        sentences_ja = []  # 翻訳前の文章
        reader = list(csv.reader(open(ENGLISH_FILE(i), "r")))
        sentences_en = [row[0] for row in reader[1:]]

        reader = list(csv.reader(open(JAPANESE_FILE(i), "r")))
        sentences_ja = [row[0] for row in reader[1:]]

        # lda
        # トピックごとの行列
        prob_mat = None
        topic_num = 0
        with open(PROB_MAT_FILE(i), 'rb') as f:
            prob_mat = pickle.load(f)
            prob_mat = np.array(prob_mat)
            _, topic_num = prob_mat.shape
            # 最大の列を取得
            max_col = list(np.argmax(prob_mat, axis=1))
            # それぞれのカウント
            count_for_topic = np.zeros(topic_num)
            for col in max_col:
                count_for_topic[col] += 1

        most_likely_topics = []
        topics = []
        probs = []
        k = 0
        with open(ITEMS_FILE(i), 'rb') as f:
            items = pickle.load(f)
            for item in items:
                topic0, _ = item[0]
                topic1, _ = item[1]
                topic2, _ = item[2]
                most_likely_topics.append(",".join([topic0, topic1, topic2]))
                topics.append([])
                probs.append([])
                for word, prob in item:
                    topics[k].append(word)
                    probs[k].append(float(prob))
                k += 1

        data.append({
            "sentences_en": sentences_en,
            "sentences_ja": sentences_ja,
            "topic_num": topic_num,
            "max_col": max_col,
            "count_for_topic": count_for_topic,
            "most_likely_topics": most_likely_topics,
            "topics": topics,
            "probs": probs
        })


def load_model():
    pass


@app.route("/", methods=["GET"])
def index():
    global data
    data_index = int(request.args.get("data_index", "0"))
    shorten_sentences_ja = [shorten(sentence, 20)
                            for sentence in data[data_index]["sentences_ja"]]
    random_indices = [i for i in range(len(data[data_index]["sentences_ja"]))]
    random.shuffle(random_indices)
    count_for_topic = list(data[data_index]["count_for_topic"])
    most_likely_topics = data[data_index]["most_likely_topics"]
    topics = data[data_index]["topics"]
    probs = data[data_index]["probs"]
    _max_col = data[data_index]["max_col"]
    max_col = []
    for col in _max_col:
        max_col.append(int(col))
    return render_template("index.html",
                           sentences_ja=shorten_sentences_ja,
                           title=DATA_TITLE[data_index],
                           data_index=data_index,
                           initial_comment=data[data_index]["sentences_ja"][random_indices[0]],
                           initial_topic_index=int(max_col[random_indices[0]]),
                           random_indices=random_indices,
                           count_for_topic=count_for_topic,
                           most_likely_topics=most_likely_topics,
                           topics=topics,
                           probs=probs,
                           max_col=max_col
                           )


@app.route("/randomComment", methods=["GET"])
def randomComment():
    global data
    data_index = int(request.args.get("data_index", "0"))
    index = int(request.args.get("index", "0"))
    return jsonify({
        "comment": data[data_index]["sentences_ja"][index],
        "topic_index": int(data[data_index]["max_col"][index])
    })


@app.route("/analysis", methods=["POST"])
def analysis():
    global data

    _preferences = None
    data_index = None
    for key, value in request.form.items():
        if key == "preferences":
            _preferences = json.loads(value)
        if key == "data_index":
            data_index = int(value)
    if _preferences is None or data_index is None:
        return jsonify({"error": "invalid request"})

    # _preferencesにはidが入っているのでコメントに変更する。
    preferences = []
    for obj in _preferences:
        the_comment = data[data_index]["sentences_ja"][obj["id"]]
        preferences.append(
            {"comment": the_comment, "reaction": obj["reaction"]})

    # ここでGPT-3を使って分析する
    user_preferences = json.dumps(preferences)

    # Streaming返送
    def generate(user_preferences):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": INSTRUCTION1},
                {"role": "user", "content": user_preferences},
            ],
            stream=True
        )
        chat_results = ""
        for resp in completion:
            if resp["choices"][0]["finish_reason"] != "stop":
                yield resp["choices"][0]["delta"]["content"]  # Streaming
                # print(resp["choices"][0]["delta"]["content"], end="")
                chat_results += resp["choices"][0]["delta"]["content"]

        yield "END_ANALYSIS"

        # ニュースを検索するクエリを発行してもらう
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": INSTRUCTION1},
                {"role": "user", "content": user_preferences},
                {"role": "assistant", "content": chat_results},
                {"role": "user", "content": INSTRUCTION2},
            ],
        )
        query = completion["choices"][0]["message"]["content"]
        news_result = ""
        for line in query.split("\n"):
            if line.startswith("# "):
                perspective = line[2:]
                news_result += f"<h2 class=\"perspective_title\"># {perspective}</h2>"
            if line.startswith("- "):
                query = line[2:]
                function_response = search_news(query)
                for i in range(len(function_response)):
                    news_result += "<div class=\"news\">"
                    news_result += f"<img src=\"{function_response[i]['image']}\" />"
                    news_result += f"<div class=\"news_content_wrapper\" data-news-url=\"{function_response[i]['url']}\" onClick=\"clickNews(this)\">"
                    news_result += f"<div class=\"news_title\"> {function_response[i]['title']} </div>"
                    news_result += f"<div class=\"news_url\"> {shorten(function_response[i]['url'], 20)} </div>"
                    news_result += "</div>"
                    news_result += "</div>"
        yield news_result

    return Response(generate(user_preferences))


if __name__ == "__main__":
    print("loading data...")
    load_data()
    load_model()
    print("loaded data")
    app.run(host='0.0.0.0', port='8000', debug=0, threaded=True)
