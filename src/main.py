"""Multiprocess entrypoint.

Author: Adam Turner <turner.adch@gmail.com>
"""

# standard library
import multiprocessing as mp
import os
import sys
# local modules
import jpm
import switch


def pipeline(ticker, url):
    if ticker == "jpm":
        jpm.get_branch_data(url)


    return None



if __name__ == "__main__":
    ticker = sys.argv[1]
    urls = switch.main(ticker)

    with mp.Pool(os.cpu_count()) as pool:
        pool.starmap(pipeline, zip([ticker for i in range(len(urls))], urls))
