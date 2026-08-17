from typing import Any, TypeVar

A = TypeVar('A')


def rotate_list(list_: list[A], n: int) -> list[A]:
    if n >= len(list_):
        raise ValueError
    return list_[n:] + list_[:n]


def best_match(s: str, choices: list[str]) -> str:
    matches = []
    for choice in choices:
        if s.startswith(choice):
            matches.append(choice)
    try:
        return max(matches, key=len)
    except ValueError:
        raise ValueError(f'Invalid Input: {s} did not match any of {choices}')