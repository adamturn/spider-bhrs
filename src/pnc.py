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
import spiders

class Record(object):

    week = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    columns = ["name", "type", "addr"]
    columns.extend(week)

    def __init__(self):
        self.data = dict.fromkeys(Record.columns)

    @property
    def pd_fmt(self):
        return tuple(self.data[col] for col in self.data)


def selenium_scrape(project, urls, headers):
    bot = spiders.SeleniumSpider.construct(
        user_agent=headers["user-agent"],
        gecko_path=str(project.root / "utils/geckodriver-v0.29.0-linux64"),
        headless=True
    )
    for url in urls:
        bot.driver.get(url)
        



    return None


def cache_sitemap():
    project = path_helper.ProjectPath.from_src(__file__)
    # get headers
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)
    
    # plan:
    # start: https://apps.pnc.com/locator/browse
    # then, grab all of the states text, this can be delim'd with '-' and appended to browse
    browse_url = "https://apps.pnc.com/locator/browse/"
    print("Requesting...")
    response = requests.get(browse_url, headers=headers)
    browse_html_doc = lxml.html.fromstring(response.text)
    branch_states = browse_html_doc.xpath("//*[@class='states']//*[@class='ng-binding']//text()")
    branch_state_urls = [browse_url + state for state in branch_states]

    final_urls = []
    for state_url in branch_state_urls:
        # from here, we want to isolate all of the cities in each state
        # this data is of the form: 'Bayou La Batre (1)'
        # the state name is all text outside of \(\) and the number of branches
        # is contained inside.
        response = requests.get(state_url, headers=headers)
        state_html_doc = lxml.html.fromstring(response.text)
        city_names = state_html_doc.xpath("//*[@class='states cities']//*[@class='ng-binding']//text()")
        city_regex = re.compile(r"^(.*)\s\(")
        clean_names = [city_regex.match(city).group(1) for city in city_names]
        final_urls.extend([state_url + "/" + city for city in clean_names])
        continue
    
    selenium_scrape(project, urls)

    print("BREAK!")
    breakpoint()


    return None


def get_branch_urls():
    project = path_helper.ProjectPath.from_src(__file__)
    # get headers
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)



    return None


if __name__ == "__main__":
    cache_sitemap()
    get_branch_urls()
