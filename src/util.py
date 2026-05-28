from itertools import islice
from typing import Iterable


def chunk_generator(iterable: Iterable, n: int):
    it = iter(iterable)
    while chunk := list(islice(it, n)):
        yield chunk