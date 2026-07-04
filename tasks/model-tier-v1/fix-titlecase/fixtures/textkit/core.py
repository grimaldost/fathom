"""Title-case a string."""


def title_case(s):
    """Return ``s`` with each word title-cased.

    A "word" is a maximal run of non-whitespace characters. For each word the
    first letter is upper-cased and the remaining letters are lower-cased, so
    ``"hELLO wORLD"`` becomes ``"Hello World"``. The empty string maps to the
    empty string. Words are rejoined with single spaces.
    """
    words = s.split(" ")
    return " ".join(word[0].upper() + word[1:] for word in words)
