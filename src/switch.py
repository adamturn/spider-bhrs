"""Main switch that takes keyword arguments and returns urls.

Author: Adam Turner <turner.adch@gmail.com>
"""

# local modules
import jpm


def main(ticker):
    if ticker == "jpm":
        return jpm.get_branch_urls()

    raise ValueError(f"Unknown ticker: `{ticker}`!")
