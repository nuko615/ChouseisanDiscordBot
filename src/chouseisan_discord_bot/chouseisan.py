from __future__ import annotations

from typing import Self
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait


class ChouseisanError(RuntimeError):
    """Raised when an event cannot be created safely."""


class ChouseisanClient:
    NAME_ID = "name"
    COMMENT_ID = "comment"
    CANDIDATES_ID = "kouho"
    CREATE_BUTTON_ID = "createBtn"
    RESULT_LINK_ID = "listLink"

    def __init__(
        self,
        base_url: str = "https://chouseisan.com",
        *,
        headless: bool = True,
        wait_seconds: int = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.wait_seconds = wait_seconds
        self._driver: webdriver.Chrome | None = None

    def __enter__(self) -> Self:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        for argument in ("--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"):
            options.add_argument(argument)

        try:
            self._driver = webdriver.Chrome(options=options)
            self._driver.set_page_load_timeout(30)
        except Exception as error:
            raise ChouseisanError("Chrome could not be started") from error
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def create_event(self, title: str, candidates: tuple[str, ...], memo: str) -> str:
        if self._driver is None:
            raise ChouseisanError("ChouseisanClient must be used as a context manager")

        driver = self._driver
        wait = WebDriverWait(driver, self.wait_seconds)
        try:
            driver.get(self.base_url)

            name = wait.until(conditions.presence_of_element_located((By.ID, self.NAME_ID)))
            comment = driver.find_element(By.ID, self.COMMENT_ID)
            candidate_box = driver.find_element(By.ID, self.CANDIDATES_ID)

            name.clear()
            name.send_keys(title)
            comment.clear()
            comment.send_keys(memo)
            candidate_box.clear()
            candidate_box.send_keys("\n".join(candidates))

            wait.until(conditions.element_to_be_clickable((By.ID, self.CREATE_BUTTON_ID))).click()
            link = wait.until(conditions.presence_of_element_located((By.ID, self.RESULT_LINK_ID)))
            event_url = link.get_attribute("href")
        except Exception as error:
            raise ChouseisanError("Chouseisan page operation failed") from error

        if not event_url:
            raise ChouseisanError("Chouseisan did not return an event URL")
        parsed = urlparse(event_url)
        if parsed.scheme != "https" or parsed.hostname != "chouseisan.com":
            raise ChouseisanError("Chouseisan returned an unexpected event URL")
        return event_url
