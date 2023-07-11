from sklearn.manifold import TSNE
import numpy as np
from sentence_transformers import SentenceTransformer
import csv
import pickle
import json

import deepl

from flask import Flask, render_template, request, jsonify


DEEPL_API_KEY = ""  # deeplのAPIキーを入れる
translator = deepl.Translator(DEEPL_API_KEY)

data = []
data_index = 0
DATA_COUNT = 2
DATA_TITLE = ["部活動の地域移行", "寿司ペロ賠償請求"]


def ENGLISH_FILE(i: int) -> str:
    return f"translated{i}.csv"


def JAPANESE_FILE(i: int) -> str:
    return f"merge{i}.csv"


def VECTOR_FILE(i: int) -> str:
    return f"vector{i}.pickle"


MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'  # ベクトルに変換するためのモデル

model = None

app = Flask(__name__)


def gradation(ratio: float) -> str:
    b = int(255 * ratio)
    g = 0
    r = 255 - b
    return "#{:02x}{:02x}{:02x}BB".format(r, g, b)


def translate(text: str) -> str:
    global translator
    target_lang = 'EN-US'
    source_lang = 'JA'

    result = translator.translate_text(
        text, source_lang=source_lang, target_lang=target_lang)

    return result.text


def shorten(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


def sentence2vec(sentence: str) -> np.ndarray:
    global model
    embedding = model.encode([sentence])
    return np.array(embedding).reshape(-1)


def calc_similarity_vec(vec: np.ndarray, data_index: int) -> np.ndarray:
    """
    高次元のまま類似度を計算する
    """
    global data
    ary = data[data_index]["ary"]
    similarity = (ary - vec) * (ary - vec)  # 類似度を計算
    similarity = np.sum(similarity, axis=1)  # 類似度を計算
    return similarity


def calc_similarity(vec: np.ndarray, data_index: int) -> np.ndarray:
    global data
    embedded = data[data_index]["embedded"]
    similarity = (embedded - vec) * (embedded - vec)  # 類似度を計算
    similarity = np.sum(similarity, axis=1)  # 類似度を計算
    return similarity


def get_neighbors(vec: np.ndarray, count: int, data_index: int, remove_myself=True) -> list:
    similarity = calc_similarity(vec, data_index)
    if remove_myself:
        top5 = np.argsort(similarity)[1:count + 1]
    else:
        top5 = np.argsort(similarity)[:count]
    return top5.tolist()


def load_data():
    global data

    data = []
    for i in range(DATA_COUNT):
        sentences_en = []  # 翻訳後の文章
        sentences_ja = []  # 翻訳前の文章
        likes_bads_mapped = []
        ratios = []
        embedded = None
        ary = None

        reader = list(csv.reader(open(ENGLISH_FILE(i), "r")))
        sentences_en = [row[0] for row in reader[1:]]
        likes = [int(row[1]) for row in reader[1:]]
        # いいねとバッドの合計
        sum_likes_bads = [int(row[1]) + int(row[2])
                          for row in reader[1:]]

        # いいねとバッドの合計を正規化
        max_sum_likes_bads = max(sum_likes_bads)
        likes_bads_mapped = [sum_like_bad / max_sum_likes_bads
                             for sum_like_bad in sum_likes_bads]

        # いいねとバッドの相対的な比率
        ratios = [like / sum_like_bad for like,
                  sum_like_bad in zip(likes, sum_likes_bads)]

        reader = list(csv.reader(open(JAPANESE_FILE(i), "r")))
        sentences_ja = [row[0] for row in reader[1:]]

        # load from pickle
        with open(VECTOR_FILE(i), 'rb') as f:
            ary = pickle.load(f)

        tsne = TSNE(n_components=2, random_state=0, perplexity=3, n_iter=500)
        embedded = tsne.fit_transform(ary)  # すでに読み込んだデータを使う

        data.append({
            "sentences_en": sentences_en,
            "sentences_ja": sentences_ja,
            "likes_bads_mapped": likes_bads_mapped,
            "ratios": ratios,
            "embedded": embedded,
            "ary": ary
        })


def load_model():
    global model
    model = SentenceTransformer(MODEL_NAME)  # これは重いのでグローバル変数にしておく


@app.route("/", methods=["GET"])
def index():
    global data
    data_index = int(request.args.get("data_index", "0"))
    embedded_data = []
    colors = [gradation(ratio) for ratio in data[data_index]["ratios"]]
    for i in range(len(data[data_index]["embedded"])):
        embedded_data.append(
            {"x": float(data[data_index]["embedded"][i][0]), "y": float(data[data_index]["embedded"][i][1])})
    shorten_sentences_ja = [shorten(sentence, 20)
                            for sentence in data[data_index]["sentences_ja"]]
    return render_template("index.html",
                           sentences_ja=shorten_sentences_ja,
                           likes_bads_mapped=data[data_index]["likes_bads_mapped"],
                           colors=colors,
                           embedded_data=embedded_data,
                           title=DATA_TITLE[data_index],
                           data_index=data_index
                           )


@app.route("/comment", methods=["POST"])
def comment():
    global data
    comment = None
    data_index = None
    for key, value in request.form.items():
        if key == "comment":
            comment = value
        if key == "data_index":
            data_index = int(value)
    if comment is None or data_index is None:
        return jsonify({"error": "comment or data_index is None"})
    # コメントを翻訳する
    en = translate(comment)
    # コメントを埋め込む
    vec = sentence2vec(en)
    similarity = calc_similarity_vec(vec, data_index)
    top5 = np.argsort(similarity)[:5]
    # 埋め込んだ後の座標をtop5を用いて推定する
    x = 0
    y = 0
    for i in top5:
        x += data[data_index]["embedded"][i][0]
        y += data[data_index]["embedded"][i][1]
    x /= 5
    y /= 5
    return jsonify({"x": x, "y": y})


@app.route("/neighbors", methods=["GET"])
def neighbors():
    global data
    index = int(request.args.get("index", "0"))
    comments_embedded = request.args.get("sentCommentsEmbedded", "[]")
    comments_embedded = json.loads(comments_embedded)
    comments = request.args.get("sentComments", "[]")
    comments = json.loads(comments)
    data_index = int(request.args.get("data_index", "0"))
    vec = ""
    the_sentence = ""
    if index < len(data[data_index]["embedded"]):
        vec = data[data_index]["embedded"][index]
        the_sentence = data[data_index]["sentences_ja"][index]
    else:
        vec = comments_embedded[index - len(data[data_index]["embedded"])]
        the_sentence = comments[index - len(data[data_index]["embedded"])]
    top5 = get_neighbors(vec, 5, data_index)
    neighbors = [data[data_index]["sentences_ja"][i] for i in top5]
    return jsonify({"neighbors": neighbors, "the_sentence": the_sentence})


if __name__ == "__main__":
    print("loading data...")
    load_data()
    load_model()
    print("loaded data")
    app.run(host='0.0.0.0', port='8000', debug=0)
