"""Ticker: JPM.

Author: Adam Turner <turner.adch@gmail.com>
"""

# python package index
import json
import lxml.html
import requests
# local modules
import path_helper


def filter_urls(urls):
    """Filters urls from a sitemap and yields a subset of branch urls.

    Branch url example: 'https://locator.chase.com./az/grand-canyon/1-mather-business-center'
        Note the pattern: state/ -> region/ -> unique
        Note that: url.split('/') == ['https:', '', 'locator.chase.com', 'az', 'grand-canyon', '1-mather-business-center']
        Note that: url[3] is the state, url[5] is the unique location

    Args:
        urls: iterable of str urls each leading to a unique branch page
    """
    for url in urls:
        parts = url.split("/")
        if len(parts) == 6 and len(parts[3]) == 2:
            print(f"Branch url: `{url}`")
            yield url
        else:
            print(f"Unkown url: `{url}`.")
            continue


def get_branch_urls():
    project = path_helper.ProjectPath.from_src(__file__)
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)

    with open(project.root / "cfg/sitemaps.json", "r") as f:
        sitemap_url = json.load(f)["jpm"]

    response = requests.get(sitemap_url, headers=headers)
    html_doc = lxml.html.fromstring(response.content)
    doc_urls = html_doc.xpath("//loc//text()")

    return list(filter_urls(doc_urls))


def get_branch_data(url):
    project = path_helper.ProjectPath.from_src(__file__)
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)

    response = requests.get(url, headers=headers)

    breakpoint()



    return None 
