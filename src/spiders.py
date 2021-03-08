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
            firefox_binary="/usr/bin/firefox",
            executable_path=gecko_path,
            options=opts
        )

        return cls(driver=driver)

    def explicit_wait(self, xpath):
        wait = webdriver.support.ui.WebDriverWait(self.driver, 10)
        wait.until(expected_conditions.element_to_be_clickable((webdriver.common.by.By.XPATH, xpath)))

        return None

    def wait_until_invisible(self, xpath):
        wait = webdriver.support.ui.WebDriverWait(self.driver, 10)
        wait.until(expected_conditions.invisibility_of_element_located((webdriver.common.by.By.XPATH, xpath)))

        return None

    def wait_until_visible(self, xpath):
        wait = webdriver.support.ui.WebDriverWait(self.driver, 10)
        wait.until(expected_conditions.visibility_of_element_located((webdriver.common.by.By.XPATH, xpath)))

        return None

