from sentence_transformers import SentenceTransformer
import pickle
import csv

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'  # ベクトルに変換するためのモデル

model = SentenceTransformer(MODEL_NAME)

sentences_en = []  # 翻訳後の文章
csv_file = input("翻訳語のCSVファイル: ")
output_file = input("保存するpickleファイル名: ")

with open(csv_file, "r") as f:
    reader = csv.reader(f)
    for row in list(reader)[1:]:
        text = row[0]
        sentences_en.append(text)

vec = model.encode(sentences_en)

with open(output_file, "wb") as f:
    pickle.dump(vec, f)
