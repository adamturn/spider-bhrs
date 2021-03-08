from selenium import webdriver
from selenium.webdriver.support import expected_conditions


class SeleniumSpider(object):

    def __init__(self, driver):
        self.driver = driver

    @classmethod
    def construct(cls, user_agent, gecko_path, headless=True):
        opts = webdriver.firefox.options.Options()
        if headless:
            opts.add_argument("--headless")
        fp = webdriver.FirefoxProfile()
        fp.set_preference("general.useragent.override", user_agent)

        driver = webdriver.Firefox(
            firefox_profile=fp,
            executable_path=str(gecko_path),
            options=opts
        )

        return cls(driver=driver)

    def explicit_wait(self, xpath):
        wait = webdriver.support.ui.WebDriverWait(self.driver, 10)
        wait.until(expected_conditions.element_to_be_clickable((webdriver.common.by.By.XPATH, xpath)))

        return None
