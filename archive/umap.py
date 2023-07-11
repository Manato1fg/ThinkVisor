import umap
import numpy as np
from matplotlib import pyplot as plt


def map(data: np.ndarray) -> None:  # 次元削減する
    mapper = umap.UMAP(random_state=0)
    embedding = mapper.fit_transform(data)

    # 結果を二次元でプロットする
    embedding_x = embedding[:, 0]
    embedding_y = embedding[:, 1]
    plt.scatter(embedding_x, embedding_y)
