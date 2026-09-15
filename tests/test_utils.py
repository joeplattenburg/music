import pytest

from music import utils


@pytest.mark.parametrize(
    'list_,n,expected',
    [
        ([1, 2, 3, 4], 0, [1, 2, 3, 4]),
        ([1, 2, 3, 4], 1, [2, 3, 4, 1]),
        ([1, 2, 3, 4], 3, [4, 1, 2, 3]),
        ([1, 2, 3, 4], 5, None),
    ]
)
def test_rotate_list(list_: list[int], n: int, expected: list[int]) -> None:

    if expected is None:
        with pytest.raises(ValueError):
            utils.rotate_list(list_, n)
    else:
        actual = utils.rotate_list(list_, n)
        assert actual == expected


def test_best_match() -> None:
    s = 'hello there'
    choices = ['h', 'hi', 'hello', 'hello bob']
    assert utils.best_match(s, choices) == 'hello'
    with pytest.raises(ValueError):
        utils.best_match(s, [choices[1], choices[3]])