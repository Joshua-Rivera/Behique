import math

from behique import tokens
from behique.embed import DIM, Embedder


def test_token_count_and_offsets():
    text = "Hello world, tokenizers!"
    n = tokens.count(text)
    assert 3 < n < 12
    offs = tokens.offsets(text)
    assert len(offs) == n
    assert offs[0][0] == 0 and offs[-1][1] == len(text)


def test_embedder_shapes_and_similarity():
    e = Embedder()
    a, b, c = e.embed_passages(["a cat sat on the mat", "a kitten rests on a rug", "tax law"])
    assert len(a) == DIM
    q = e.embed_query("cat on a mat")

    def cos(x, y):
        return sum(i * j for i, j in zip(x, y, strict=True))

    assert math.isclose(cos(a, a), 1.0, rel_tol=1e-3)
    assert cos(q, a) > cos(q, c)
    assert cos(a, b) > cos(a, c)
