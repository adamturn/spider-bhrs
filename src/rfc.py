"""
Author: Adam Turner <turner.adch@gmail.com>
"""

# standard library
import io
import json
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


def get_branch_urls(project, headers):
    with open(project.root / "cfg/sitemaps.json", "r") as f:
        sitemaps = json.load(f)

    print("Parsing sitemap...")
    response = requests.get(url=sitemaps["rfc"], headers=headers)
    sitemap_html = lxml.html.fromstring(response.text)
    sitemap_urls = sitemap_html.xpath("//loc//text()")
    branch_regex = re.compile(r"(?i)https://www.regions.com/Locator/Branch/bank-branch")
    branch_urls = [url for url in sitemap_urls if branch_regex.search(url)]

    return branch_urls


def transform_time_fields(record, lobby_hours):
    clean_hrs = [val.strip() for val in lobby_hours if val.strip()]

    try:
        assert len(clean_hrs) % 2 == 0  # Expects a list: ['mon-fri', 'hours', 'sat', 'hours', 'sun', 'hours'
    except AssertionError:
        print("ASSERTION ERROR")
        breakpoint()
        print("UNKOWN BELOW")

    # window slice such that we have ('Mon - Fri:', '9 a.m.-5 p.m.') pairs in the window as (day_range, branch_hours)
    for i in range(0, len(clean_hrs), 2):
        day_range = clean_hrs[i]
        start_day = day_range[:3].lower()
        branch_hours = clean_hrs[i+1]
        if start_day in record.data:
            record.data[start_day] = branch_hours

    # fill in the empty days with previous data, rfc week starts on mon
    mem = None
    for day in record.week:
        buffer = record.data[day]
        if buffer is not None:
            mem = buffer
        else:
            record.data[day] = mem

    return record


def get_branch_record(url, headers):
    print(f"`{url}`: Constructing branch record...")
    record = Record()

    with requests.Session() as sesh:
        # for some unknown reasons, the first request errors out?
        # not sure why rfc would do this, but we can get past it...
        for _ in range(2):
            response = requests.get(url, headers=headers)
    branch_html = lxml.html.fromstring(response.text)

    branch_name = branch_html.xpath("//h1[contains(@class, 'location-title')]//text()")
    if branch_name:
        record.data["name"] = branch_name[0]

    branch_type = branch_html.xpath("//*[contains(@class, 'location-type')]//text()")
    if branch_type:
        record.data["type"] = branch_type[0]

    branch_addr = branch_html.xpath("(//*[contains(@class, 'location-address-line')])[1]//text()")
    if branch_addr:
        clean_addr = [val.strip() for val in branch_addr]
        record.data["addr"] = ", ".join(clean_addr)

    lobby_hours = branch_html.xpath("(//*[contains(@class, 'hours-block-list')])[1]//text()")
    if lobby_hours:
        record = transform_time_fields(record, lobby_hours)

    print(f"`{url}`: Record: {record.pd_fmt}")
    
    return record.pd_fmt


def load(records, project):
    df = pd.DataFrame.from_records(records)
    df.columns = Record.columns
    csv_name = "rfc.csv"
    csv_path = str(project.root / f"downloads/{csv_name}")
    df.to_csv(csv_path)
    print(f"Exporting to `{csv_path}`")
    try:
        df.to_csv(csv_path)
    except FileNotFoundError:
        print(f"WARNING: DUMPING CSV TO LOCAL PATH: `{csv_name}`!")
        df.to_csv(csv_name)
        raise FileNotFoundError(f"Could not export to `{csv_path}`. Did you forget to run `setup.sh`?")

    return None


def main():
    project = path_helper.ProjectPath.from_src(__file__)
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)

    branch_urls = get_branch_urls(project, headers)

    records = []
    for branch_url in branch_urls:
        records.append(get_branch_record(branch_url, headers))

    load(records, project)

    return None


if __name__ == "__main__":
    main()
