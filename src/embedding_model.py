"""One shared embedding model for the whole process.

Three modules used to build their own SentenceTransformer, which meant three
copies of the weights in memory and three loads at startup. They all call
get_model() now, so the model is built once, on first use.
"""

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)

    return _model


def encode(texts):
    return get_model().encode(texts)
