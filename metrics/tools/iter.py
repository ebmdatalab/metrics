import itertools


def batched(iterable, n):
    """
    Backport of 3.12's itertools.batched

    https://docs.python.org/3/library/itertools.html#itertools.batched

    batched('ABCDEFG', 3) --> ABC DEF G
    """
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch
