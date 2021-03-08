"""Ticker: JPM.

Author: Adam Turner <turner.adch@gmail.com>
"""

# python package index
import json
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
            print(f"Branch URL: `{url}`")
            yield url
        else:
            print(f"Non-Branch URL: `{url}`.")
            continue


def get_branch_urls(headers, project):
    with open(project.root / "cfg/sitemaps.json", "r") as f:
        sitemap_url = json.load(f)["jpm"]

    response = requests.get(sitemap_url, headers=headers)
    html_doc = lxml.html.fromstring(response.content)
    doc_urls = html_doc.xpath("//loc//text()")

    return list(filter_urls(doc_urls))


def transform_time_fields(record, lobby_hours):
    print("Transforming time fields...")
    clean_hrs = [val.strip() for val in lobby_hours if val.strip()]
    # Expect a list of the form: ['Mon', '9 AM', '-', '5 PM', 'Tue', ..., 'Sun', 'Closed']
    for i, val in enumerate(clean_hrs):
        val_lc = val.lower()
        if val_lc in record.data:
            branch_hours = ""
            # start at the next part in the array and iterate until you hit another day
            for time_part in clean_hrs[i+1:]:
                time_lc = time_part.lower()
                if time_lc in record.data:  # this means we will have hit the next `day` part
                    break
                else:
                    branch_hours += time_lc
            record.data[val_lc] = branch_hours
        else:
            continue

    return record


def get_branch_record(branch_url, headers):
    record = Record()

    response = requests.get(branch_url, headers=headers)
    branch_html = lxml.html.fromstring(response.text)

    branch_name = branch_html.xpath("//*[@id='location-name']//text()")
    if branch_name:
        record.data["name"] = branch_name[0]

    # JPM doesn't have readily available `branch type` data (think `ATM + Branch` vs `Branch`)
    # if you want to construct your own field based on existing page data, do it here.

    branch_addr = branch_html.xpath("//*[@id='address']//text()")
    if branch_addr:
        clean_addr = [val.strip() for val in branch_addr if len(val.strip()) > 1]
        record.data["addr"] = ", ".join(clean_addr)

    lobby_hours = branch_html.xpath("(//tbody)[1]//text()")
    if lobby_hours:
        record = transform_time_fields(record, lobby_hours)

    print(record.pd_fmt)

    return record.pd_fmt


def load(records, project):
    df = pd.DataFrame.from_records(records)
    df.columns = Record.columns
    csv_name = "jpm.csv"
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

    branch_urls = get_branch_urls(headers, project)

    records = []
    for url in branch_urls:
        print("Processing:", url)
        records.append(get_branch_record(url, headers))

    load(records, project)

    return None


if __name__ == "__main__":
    main()
