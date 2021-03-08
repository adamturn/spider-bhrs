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
    columns.append("tmp_closed")

    def __init__(self):
        self.data = dict.fromkeys(Record.columns)

    @property
    def pd_fmt(self):
        return tuple(self.data[col] for col in self.data)


def navigate_city_urls(bot, urls):
    records = []
    for city_url in urls:
        print(f"`{city_url}: Navigating...")
        bot.driver.get(city_url)
        # need to figure out how many city
        branch_anchor_xpath = "//*[@class='cardBranchName text-capitalize']//*[@class='ng-binding']"
        bot.explicit_wait(branch_anchor_xpath)
        city_html_doc = lxml.html.fromstring(bot.driver.page_source)
        city_header_txt = city_html_doc.xpath("//*[@class='stateListHeader stateListHdrBg']//h1//text()")
        num_branches = int(city_header_txt[0]) # the first bit of text is the number
        # now that we have the number of cities, we know how to slice the following array

        print("Waiting until details are clickable...")
        details_xpath = "//*[@class='cardNavigation']//*[@href][2]"
        bot.explicit_wait(details_xpath)

        print("Waiting until modal fade is invisible...")
        bot.wait_until_invisible(xpath="//div[contains(@class, 'modal')]")
        branch_elements = bot.driver.find_elements_by_xpath(details_xpath)
        clean_elements = branch_elements[:num_branches]
        assert len(clean_elements) == num_branches
        print(f"Found {num_branches} branches in this city!")

        print("Creating records for each branch in city...")
        for branch_element in clean_elements:
            bot.wait_until_invisible(xpath="//div[contains(@class, 'modal')]")
            branch_element.click()
            time_data_xpath = "(//service-hour)[1]//*[@class='ng-scope']"
            bot.wait_until_visible(xpath=time_data_xpath)
            print(bot.driver.current_url)
            branch_html = lxml.html.fromstring(bot.driver.page_source)
            time_data = branch_html.xpath(time_data_xpath + "//text()")
            clean_times = [time for time in time_data if time.strip()]
            print(clean_times)

            # Constructing record for this branch
            assert len(clean_times) == 7            
            record = Record()
            for day, time in zip(record.week, clean_times):
                record.data[day] = time
            
            branch_name = branch_html.xpath("//h1[@class='bold ng-binding']//text()")
            if branch_name:
                record.data["name"] = branch_name[0]
            # no branch type data for pnc
            branch_addr = branch_html.xpath("//*[@itemprop='address']//text()")
            if branch_addr:
                clean_addr = [val for val in branch_addr if len(val.strip()) > 1]
                record.data["addr"] = " ".join(clean_addr)

            # append record
            print(record.pd_fmt)
            records.append(record.pd_fmt)
            # go back to the last city url page with all of the branches listed
            bot.driver.back()
            continue


    return None


def cache_sitemap():
    project = path_helper.ProjectPath.from_src(__file__)
    # get headers
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)    
    bot = spiders.SeleniumSpider.construct(
        user_agent=headers["user-agent"],
        gecko_path=str(project.root / "geckodriver-v0.29.0-linux64/geckodriver"),
        headless=True
    )

    try:
        with open(project.root / "downloads/pnc_sitemap.json", "r") as f:
            pnc_sitemap = json.load(f)
    except FileNotFoundError:
        # start by navigating to https://apps.pnc.com/locator/browse
        # then, grab all of the states text, this can be delim'd with '-' and appended to browse
        browse_url = "https://apps.pnc.com/locator/browse"
        print("Requesting PNC locator app browse page...")
        bot.driver.get(browse_url)
        state_data_xpath = "//*[@data-ng-bind='obj.stateName']"
        bot.explicit_wait(state_data_xpath)
        print("Extracting state data from browse page...")
        browse_html_doc = lxml.html.fromstring(bot.driver.page_source)
        branch_states = set(browse_html_doc.xpath(state_data_xpath + "//text()"))  # dedup? why pnc...
        branch_state_urls = [browse_url + "/" + state.lower().replace(' ', '-') for state in branch_states]

        print("Building sitemap array...")
        city_urls = []
        for state_url in branch_state_urls:
            print(f"`{state_url}`: Requesting...")
            # from here, we want to isolate all of the cities in each state
            # this data is of the form: 'Bayou La Batre (1)'
            # the state name is all text outside of \(\) and the number of branches
            # is contained inside.
            bot.driver.get(state_url)
            print(f"`{state_url}`: Extracting city names...")
            city_data_xpath = "//*[@class='states cities']//*[@class='ng-binding']"
            bot.explicit_wait(city_data_xpath)
            state_html_doc = lxml.html.fromstring(bot.driver.page_source)
            city_names = state_html_doc.xpath(city_data_xpath + "//text()")
            city_regex = re.compile(r"^(.*)\s\(")
            fmt_names = [city_regex.match(city).group(1).lower().replace(' ', '-') for city in city_names]
            print(f"`{state_url}`: Extending sitemap array...")
            city_urls.extend([state_url + "/" + city for city in fmt_names])
            continue

        pnc_sitemap = {"urls": city_urls}
        with open(project.root / "downloads/pnc_sitemap.json", "w") as f:
            json.dump(pnc_sitemap, f)
    else:
        city_urls = pnc_sitemap["urls"]
    # final urls will all lead to sites that immediately make a javascript function call 
    # that returns data from a database back-end, hence selenium
    navigate_city_urls(bot, city_urls)

    return None


def get_branch_urls():
    project = path_helper.ProjectPath.from_src(__file__)
    # get headers
    with open(project.root / "cfg/headers.json", "r") as f:
        headers = json.load(f)



    return None


def main():
    cache_sitemap()
    get_branch_urls()

    return None


if __name__ == "__main__":
    main()
