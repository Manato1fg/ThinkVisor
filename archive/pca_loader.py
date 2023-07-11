import pickle
DATA_COUNT = 2


def VECTOR_FILE(i: int) -> str:
    return f"vector{i}.pickle"


data = []

for i in range(DATA_COUNT):
    # load from pickle
    with open(VECTOR_FILE(i), 'rb') as f:
        ary = pickle.load(f)
        data[i] = ary
