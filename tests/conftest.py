import random

import pytest

from behique.store import Store

DIM = 8


def rand_vec(seed: int, dim: int = DIM) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(dim)]


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.db", model_name="test-model", dim=DIM)
    yield s
    s.close()
