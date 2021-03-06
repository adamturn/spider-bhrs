"""
Author: Adam Turner <turner.adch@gmail.com>
"""

# standard library
import json
import re
# python package index
import lxml.html
import requests
# local modules
import path_helper


def get_branch_urls():
    project = path_helper.ProjectPath.from_src(__file__)
    # get headers
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)
    # get sitemap
    with open(project.root / "cfg/sitemaps.json", "r") as f:
        sitemaps = json.load(f)

    print("Requesting sitemap...")
    response = requests.get(url=sitemaps["wfc"], headers=headers)

    print("Filtering urls...")
    branch_urls = [url for url in response.text.split("\n") if url.split()]

    return branch_urls, headers


def get_branch_data(branch_urls, headers):
    records = []
    for url in branch_urls:
        print(f"`{url}`: Requesting...")
        response = requests.get(url, headers=headers)
        html_doc = lxml.html.fromstring(response.text)
        print(f"`{url}`: Extracting...")
        # we are using lobby hours and ignoring drive-up hours for now
        # fields: name, type, addr, monfri, sat, sun
        branch_type = html_doc.xpath("//*[@itemprop='location']/*[@class='fn heading']//text()")[0].strip()
        addr_data = html_doc.xpath("//address//text()")
        # cleaning gets rids of whitespace parts and existing delimiters
        addr_data = [part.strip() for part in addr_data if part.strip() and len(part.strip()) >= 2]
        branch_name = addr_data[0]
        branch_addr = ", ".join(addr_data[1:])
        # parsing the time data
        time_data = html_doc.xpath("(//*[@id='bankInfoSection']//ul)[1]//text()")
        time_data = [part.strip() for part in time_data if part.strip()]
        time_regex = re.compile(r"\w\s(.*$)")
        breakpoint()
        branch_monfri_open = ""
        branch_monfri_close = ""
        branch_sat_open = ""
        branch_sat_close = ""
        branch_sun_open = ""
        branch_sun_close = ""
        breakpoint()

        record = (branch_name, branch_type, branch_addr, branch_monfri, branch_sat, branch_sun)
        print(record)
        records.append(record)

        breakpoint()    


    return None


def main():
    urls, headers = get_branch_urls()
    get_branch_data(urls, headers)

    return None


if __name__ == "__main__":
    main()
