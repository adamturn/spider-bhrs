"""
Python 3.8
Author: Adam Turner <turner.adch@gmail.com>
"""

# standard library
import copy
import datetime
import json
import random
import re
import sys
import time
# python package index
import lxml.html
import pandas as pd
from selenium.common.exceptions import TimeoutException
# local modules
import path_helper
import spiders


class Record(object):

    week = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    columns = ["name", "type", "addr"]
    columns.extend(week)
    columns.append("tmp_closed")

    def __init__(self):
        self.data = dict.fromkeys(Record.columns)

    @property
    def tuple_fmt(self):
        return tuple(self.data[col] for col in self.data)


def extract_branch_record(bot):
    print("Waiting until branch URL anchor is visible...")
    bot.wait_until_visible("(//service-hour)[1]")
    print("Getting record from branch URL:", bot.driver.current_url)
    branch_html = lxml.html.fromstring(bot.driver.page_source)
    time_data = branch_html.xpath("(//service-hour)[1]//*[@class='ng-scope']//text()")
    clean_times = [time for time in time_data if time.strip()]
    assert len(clean_times) == 7  # 7 days in a week
    # pnc rotates these time fields such that the top day is always the current day
    # so we need to figure out what day it is, then clean up accordingly
    # Example: today = 'Tuesday' => clean_times = [tue, wed, thu, fri, sat, sun, mon]
    record = Record()
    match_key = ""
    today = datetime.datetime.now().strftime("%A")  # Expect: 'Friday'
    for i, day in enumerate(record.week):
        match = re.search(pattern=f"(?i)^{day}", string=today)
        if match:
            shift_key = i
            break
    if not shift_key:
        raise ValueError("No match key!")
    else:
        mon_index = 7 - shift_key
        shifted_times = clean_times[mon_index:]
        shifted_times.extend(clean_times[:mon_index])

    for day, time in zip(record.week, shifted_times):
        record.data[day] = time
    
    branch_name = branch_html.xpath("//h1[@class='bold ng-binding']//text()")
    if branch_name:
        record.data["name"] = branch_name[0]

    # no `branch type` data for pnc

    branch_addr = branch_html.xpath("//*[@itemprop='address']//text()")
    if branch_addr:
        clean_addr = [val for val in branch_addr if len(val.strip()) > 1]
        record.data["addr"] = " ".join(clean_addr)

    print("Record:", record.tuple_fmt)

    return record.tuple_fmt


def get_city_records(bot, city_url):
    print(f"`{city_url}`: Navigating...")
    bot.driver.get(city_url)
    anchor_xpath = "//*[@data-ng-bind='browseBranchCtrl.locationCount']"  # branch location counter
    bot.wait_until_visible(anchor_xpath)

    city_html_doc = lxml.html.fromstring(bot.driver.page_source)
    num_branches = int(city_html_doc.xpath(anchor_xpath + "//text()")[0])
    # now that we have the number of cities, we know how to slice the following array to dedup
    branch_xpath = "//a[@class='ng-binding']"
    branch_matches = bot.driver.find_elements_by_xpath(branch_xpath)
    branch_elements = branch_matches[:num_branches]

    try:
        assert len(branch_elements) == num_branches
    except AssertionError:
        print("ASSERTION ERROR: Branch elements length mismatch!")
        breakpoint()
        print("UNKNOWN BELOW")

    print(f"Found {num_branches} branches in this city!")

    city_records = []
    for i in range(num_branches):
        branch_num = i + 1
        print(f"Constructing branch record {branch_num}/{num_branches}...")
        branch_num_xpath = f"({branch_xpath})[{branch_num}]"
        print(f"Current city URL: {bot.driver.current_url}")
        print("Executing click script...")
        bot.execute_click_script(branch_num_xpath)
        city_records.append(extract_branch_record(bot))
        # go back to the last city url page with all of the branches listed
        print("Going back...")
        bot.driver.back()
        continue

    return city_records


def build_sitemap(project, bot):
    print("Requesting PNC locator app `browse` page...")
    with open(project.root / "cfg/sitemaps.json") as f:
        sitemaps = json.load(f)

    print("Extracting state data from `browse` page...")
    browse_url = sitemaps["pnc"]
    bot.driver.get(browse_url)
    state_data_xpath = "//*[@data-ng-bind='obj.stateName']"
    bot.wait_until_clickable(state_data_xpath)
    browse_html_doc = lxml.html.fromstring(bot.driver.page_source)
    print("Constructing state-level URLs...")
    branch_states = set(browse_html_doc.xpath(state_data_xpath + "//text()"))  # dedup? why pnc...
    branch_state_urls = [browse_url + "/" + state.lower().replace(" ", "-") for state in branch_states]

    print("Collecting city-level URLs for each state...")
    city_urls = []
    for state_url in branch_state_urls:
        print(f"`{state_url}`: Requesting state-level URL...")
        # from here, we want to isolate all of the cities in each state
        # this data is of the form: 'Bayou La Batre (1)'
        # the state name is all text outside of \(\) and the number of branches is contained inside.
        bot.driver.get(state_url)

        print(f"`{state_url}`: Extracting city name data...")
        city_data_xpath = "//*[@class='states cities']//*[@class='ng-binding']"
        bot.wait_until_clickable(city_data_xpath)
        state_html_doc = lxml.html.fromstring(bot.driver.page_source)
        city_names = state_html_doc.xpath(city_data_xpath + "//text()")
        city_regex = re.compile(r"^(.*)\s\(")
        clean_names = [city_regex.match(city).group(1).lower().replace(" ", "-").replace("\'", "") for city in city_names]

        print(f"`{state_url}`: Extending city-level URLs...")
        city_urls.extend([state_url + "/" + city for city in clean_names])
        continue

    pnc_city_urls = {"urls": city_urls}
    with open(project.root / "downloads/pnc_city_urls.json", "w") as f:
        json.dump(pnc_city_urls, f)

    return city_urls


def get_city_urls(bot, project, recover=False):
    if recover:
        json_path = "downloads/pnc_city_urls_recover.json"
    else:
        json_path = "downloads/pnc_city_urls.json"

    try:
        with open(project.root / json_path, "r") as f:
            pnc_city_urls = json.load(f)
    except FileNotFoundError:
        city_urls = build_sitemap(project, bot)
    else:
        city_urls = pnc_city_urls["urls"]

    return set(city_urls)


def load(records, project):
    df = pd.DataFrame.from_records(records)
    df.columns = Record.columns
    csv_name = "pnc.csv"
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
    for arg in sys.argv:
        if arg.lower() == "recover":
            print("Starting in recovery mode...")
            recover = True
        else:
            recover = False

    project = path_helper.ProjectPath.from_src(__file__)
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)

    bot = spiders.SeleniumSpider.construct(
        user_agent=headers["user-agent"],
        gecko_path=str(project.root / "geckodriver-v0.29.0-linux64/geckodriver"),
        headless=True
    )

    city_urls = get_city_urls(bot, project, recover=recover)

    records = []
    for city_url in city_urls:
        try:
            city_records = get_city_records(bot, city_url)
        except TimeoutException:
            print("SERVER TIMEOUT: Exiting browsing context...")
            bot.driver.quit()
            random_sleep = random.randint(10, 15)
            print(f"Sleeping for {random_sleep} seconds...")
            time.sleep(random_sleep)
            print("Constructing a new bot...")
            bot = spiders.SeleniumSpider.construct(
                user_agent=headers["user-agent"],
                gecko_path=str(project.root / "geckodriver-v0.29.0-linux64/geckodriver"),
                headless=True
            )
            print("Trying again...")
            city_records = get_city_records(bot, city_url)

        if recover:
            print("Recovery: Exporting city records to CSV...")
            if city_records:  # sometimes the sitemap is old and a city has no branches
                df = pd.DataFrame.from_records(city_records)
                df.columns = Record.columns
                csv_dirname = "downloads/pnc"
                csv_dir = project.root / csv_dirname
                csv_path = f"{csv_dirname}/{city_url.split('/')[-1]}_records.csv"
                try:
                    csv_dir.mkdir(parents=True)
                except FileExistsError:
                    pass
                df.to_csv(project.root / csv_path, sep=",", header=False, index=False)

            print("Recovery: Removing city url from recovery JSON...")
            buffer = copy.deepcopy(city_urls)
            buffer.remove(city_url)
            city_urls_recover = {"urls": [x for x in buffer]}
            del buffer
            with open(project.root / "downloads/pnc_city_urls_recover.json", "w") as f:
                json.dump(city_urls_recover, f)

        records.extend(city_records)


    load(records, project)

    return None


if __name__ == "__main__":
    main()
