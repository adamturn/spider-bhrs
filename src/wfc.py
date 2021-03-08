"""
Author: Adam Turner <turner.adch@gmail.com>
"""

# standard library
from ast import NodeTransformer
import json
import os
import re
# python package index
import lxml.html
import pandas as pd
import requests
# local modules
import path_helper


class Record(object):

    week = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    columns = ["name", "type", "addr"]
    columns.extend(week)
    columns.append("tmp_closed")

    def __init__(self):
        self.data = dict.fromkeys(Record.columns)

    @property
    def pd_fmt(self):
        return tuple(self.data[col] for col in self.data)


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
    # TODO: remove and write a real test
    # branch_urls = [
    #     "https://www.wellsfargo.com/locator/bank/81__S__AIRPORT__DR_HIGHLAND__SPRINGS_VA_23075/",
    #     "https://www.wellsfargo.com/locator/bank/1060__MAIDEN__CHOICE__LN_BALTIMORE_MD_21229/",
    #     "https://www.wellsfargo.com/locator/bank/441__SEABREEZE__BLVD_DAYTONA__BEACH_FL_32118/",
    #     "https://www.wellsfargo.com/locator/bank/19809__NW__2ND__AVE_MIAMI__GARDENS_FL_33169/",
    #     "https://www.wellsfargo.com/locator/bank/780__S__AIRPORT__BLVD_SAN__FRANCISCO_CA_94128/",
    #     "https://www.wellsfargo.com/locator/bank/3990__NW__16TH__ST_LAUDERHILL_FL_33311/",
    # ]

    return branch_urls, headers, project


def transform_addr_fields(url, html_doc, record):
    print(f"`{url}`: Transforming address fields...")
    # we are using lobby hours and ignoring drive-up hours for now
    # fields: name, type, addr, monfri, sat, sun
    record.data["type"] = html_doc.xpath("//*[@itemprop='location']/*[@class='fn heading']//text()")[0].strip()
    addr_data = html_doc.xpath("//address//text()")
    # cleaning gets rids of whitespace parts and existing delimiters
    addr_data = [part.strip() for part in addr_data if part.strip() and len(part.strip()) >= 2]
    record.data["name"] = addr_data[0]
    record.data["addr"] = ", ".join(addr_data[1:])

    return record


def transform_time_fields(url, html_doc, record):
        print(f"`{url}`: Transforming time fields...")
        time_rows = html_doc.xpath("(//*[@id='bankInfoSection']//ul)[1]//text()")  # note the [1]: lobby hours only
        time_rows = [row.strip() for row in time_rows if row.strip()]

        # Expect: time_data ~= ['Mon-Fri 09:00 AM-05:00 PM', 'Sat 09:00 AM-12:00 PM', 'Sun closed']        
        days_regex = re.compile(r"(?i)^(\w{3}(\-\w{3})?)\s")  # Extract the group 1 match: `Mon-Fri`
        time_regex = re.compile(r"\w\s(.*$)")  # Extract: `09:00 AM-05:00 PM`

        for row in time_rows:
            days_match = days_regex.search(row).group(1)
            start_day = days_match.split("-")[0].strip().lower()
            time_match = time_regex.search(row).group(1)
            record.data[start_day] = time_match

        # fill in the empty days with previous data, wfc week starts on mon
        mem = None
        for day in Record.week:
            buffer = record.data[day]
            if buffer is not None:
                mem = buffer
            else:
                record.data[day] = mem

        # Example code to transform these time fields into `open` and `close` parts:
        # branch_monfri, branch_sat, branch_sun = time_data
        # delim = "-"
        # branch_monfri_open, branch_monfri_close = branch_monfri.split(delim)
        # closed = "closed"
        # if branch_sat.lower() == closed:
        #     branch_sat_open, branch_sat_close = [closed] * 2
        # else:
        #     branch_sat_open, branch_sat_close = branch_sat.split(delim)
        # if branch_sun.lower() == closed:
        #     branch_sun_open, branch_sun_close = [closed] * 2
        # else:
        #     branch_sun_open, branch_sun_close = branch_sat.split(delim)

        return record


def get_branch_data(branch_urls, headers, project):
    records = []
    for url in branch_urls:
        print(f"`{url}`: Requesting...")
        response = requests.get(url, headers=headers)

        print(f"`{url}`: Extracting...")
        html_doc = lxml.html.fromstring(response.text)
        
        if html_doc.xpath("//*[@id='searchForm.errors']"):
            # page does not exist (sitemap is not frequently updated by wfc)
            print("ALERT: Page does not exist! Skipping record...")
            continue
        elif not html_doc.xpath("//address"):
            print("ALERT: Address data element was not found! Skipping record...")
            continue

        print(f"`{url}`: Constructing record...")
        branch = Record()
        branch = transform_addr_fields(url, html_doc, record=branch)

        if branch.data["type"].lower() == "atm":
            print("ALERT: ATM-only location. Skipping time fields...")
        elif html_doc.xpath("//*[@class='incidentMessage']//*[contains(text(), 'Drive-up Only Alert')]"):
            # branch lobby is closed for unknown reason, no time fields
            print("ALERT: Drive-up Only Alert. Skipping time fields...")
            branch.data["tmp_closed"] = 1
        elif not html_doc.xpath("//*[contains(text(), 'Lobby Hours')]"):
            print("ALERT: Could not find Lobby Hours! Skipping time fields...")
        else:
            branch = transform_time_fields(url, html_doc, record=branch)
            branch.data["tmp_closed"] = 0

        print(f"`{url}`: Record: `{branch.pd_fmt}`")
        print(f"`{url}`: Appending...")
        records.append(branch.pd_fmt)
        continue

    return records, project


def load(records, project):
    print("Constructing DataFrame...")
    df = pd.DataFrame.from_records(records)
    df.columns = Record().data.keys()

    csv_name = "wfc.csv"
    csv_path = str(project.root / f"downloads/{csv_name}")
    print(f"Exporting to `{csv_path}`")
    try:
        df.to_csv(csv_path)
    except FileNotFoundError:
        print(f"WARNING: DUMPING CSV TO LOCAL PATH: `{csv_name}`!")
        df.to_csv(csv_name)
        raise FileNotFoundError(f"Could not export to `{csv_path}`. Did you forget to run `setup.sh`?")

    return None


def main():
    urls, headers, sitemap = get_branch_urls()

    records, project = get_branch_data(urls, headers, sitemap)

    load(records, project)

    return None


if __name__ == "__main__":
    main()
