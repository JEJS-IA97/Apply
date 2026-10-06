from bs4 import BeautifulSoup


class FakeLocator:
    def __init__(self, soup, selector):
        self._soup = soup
        self._selector = selector

    @property
    def first(self):
        return self

    def count(self):
        return len(self._soup.select(self._selector))

    def is_visible(self):
        element = self._soup.select_one(self._selector)
        if element is None:
            return False
        style = (element.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or element.has_attr("hidden"):
            return False
        width = str(element.get("width") or "1")
        height = str(element.get("height") or "1")
        return not (width in ("0", "0px") or height in ("0", "0px"))


class FakePage:
    def __init__(
        self,
        html,
        confirm_on_submit=True,
        goto_error=None,
        redirect_url=None,
        confirm_to=None,
    ):
        self._soup = BeautifulSoup(html, "html.parser")
        self._confirm = confirm_on_submit
        self._goto_error = goto_error
        self._redirect_url = redirect_url
        self._confirm_to = confirm_to
        self.url = ""
        self.calls = []
        self.filled = {}
        self.files = {}

    def goto(self, url, timeout=None):
        self.calls.append(("goto", url, timeout))
        if self._goto_error:
            raise self._goto_error
        self.url = self._redirect_url or url

    def locator(self, selector):
        return FakeLocator(self._soup, selector)

    def wait_for_selector(self, selector, timeout=None):
        self.calls.append(("wait_for_selector", selector))
        if self._soup.select_one(selector) is None:
            raise TimeoutError(f"selector ausente: {selector}")

    def fill(self, selector, value):
        self.calls.append(("fill", selector))
        if self._soup.select_one(selector) is None:
            raise TimeoutError(f"selector ausente: {selector}")
        self.filled[selector] = value

    def set_input_files(self, selector, path):
        self.calls.append(("set_input_files", selector))
        if self._soup.select_one(selector) is None:
            raise TimeoutError(f"selector ausente: {selector}")
        self.files[selector] = path

    def click(self, selector):
        self.calls.append(("click", selector))
        if self._soup.select_one(selector) is None:
            raise TimeoutError(f"selector ausente: {selector}")
        if self._confirm:
            self.url = self._confirm_to or f"{self.url}?application=ok"

    def wait_for_url(self, predicate, timeout=None):
        self.calls.append(("wait_for_url", None))
        if predicate(self.url):
            return self.url
        raise TimeoutError("sin cambio de URL")

    def content(self):
        return "<html><body>Confirmation: application received</body></html>"
