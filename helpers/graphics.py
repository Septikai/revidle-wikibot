from enum import StrEnum


class Colour(StrEnum):
    """Colour values for printing to console"""
    Yellow = "\033[93m"
    Green = "\033[32m"
    Purple = "\033[35m"


_end_colour = "\033[0m"


def print_coloured(colour: Colour, value: str, *, sep: str = "\r", end: str = "\n"):
    """Print a coloured string"""
    print(f"{colour}{value}{_end_colour}", sep=sep, end=end)


def print_startup_progress_bar(iteration: int, total: int, bar_prefix: str):
    """Print an updating progress bar during bot startup"""
    percent = "{0:.1f}".format(100 * (iteration / float(total))) + "%"
    percent = percent if len(percent) == 6 else " " * (6 - len(percent)) + percent
    filled_length = int(50 * iteration // total)
    bar = "█" * filled_length + "-" * (50 - filled_length)
    if iteration != total:
        print_coloured(Colour.Purple, f"\r{bar_prefix} |{bar}| {percent}  Complete", end="")
    else:
        print_coloured(Colour.Purple, f"\r{bar_prefix} |{bar}| {percent}  Complete")
