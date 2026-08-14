#!/usr/bin/env python3
"""Verify the user-visible Publications page produced by Hugo."""

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
FIGURES = (
    "dream.png",
    "hamlet.png",
    "refeed.png",
    "msumbench.png",
    "tcts.png",
    "covid-eenet.png",
    "hi-covidnet.png",
)


class PublicationsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.class_counts: dict[str, int] = {}
        self.entry_keyword_counts: list[int] = []
        self._in_entry = False
        self._current_keyword_count = 0
        self.links: set[str] = set()
        self.image_sources: set[str] = set()
        self.iframe_sources: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        for class_name in classes:
            self.class_counts[class_name] = self.class_counts.get(class_name, 0) + 1

        if tag == "article" and "publication-entry" in classes:
            self._in_entry = True
            self._current_keyword_count = 0

        if self._in_entry and "publication-keyword" in classes:
            self._current_keyword_count += 1

        if tag == "a" and attributes.get("href"):
            self.links.add(attributes["href"] or "")
        elif tag == "img" and attributes.get("src"):
            self.image_sources.add(attributes["src"] or "")
        elif tag == "iframe" and attributes.get("src"):
            self.iframe_sources.add(attributes["src"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self._in_entry:
            self.entry_keyword_counts.append(self._current_keyword_count)
            self._in_entry = False


def parse_page(path: Path) -> PublicationsParser:
    parser = PublicationsParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def assert_redirect(path: Path) -> None:
    rendered = path.read_text(encoding="utf-8").lower().replace(" ", "")
    assert "http-equiv=refresh" in rendered, f"{path} has no refresh redirect"
    assert "url=https://hyangsukmin.github.io/publication/" in rendered, (
        f"{path} does not redirect to /publication/"
    )


def main() -> None:
    parser = parse_page(PUBLIC / "publication/index.html")
    rendered_styles = "\n".join(
        path.read_text(encoding="utf-8") for path in (PUBLIC / "css").glob("*.css")
    )

    assert parser.class_counts.get("publication-entry", 0) == 8
    assert parser.class_counts.get("publication-figure", 0) == 7
    assert parser.class_counts.get("publication-animation", 0) == 1
    assert parser.class_counts.get("publication-entry--text-only", 0) == 0
    assert parser.class_counts.get("publication-summary", 0) == 8
    assert parser.class_counts.get("author-highlight", 0) == 8
    assert parser.entry_keyword_counts == [5, 5, 5, 5, 5, 4, 5, 5]
    assert ".publication-entry" in rendered_styles, "custom publication CSS is missing"
    assert ".author-highlight" in rendered_styles, "author highlight CSS is missing"

    assert "/publication/" in parser.links
    assert "/research/" not in parser.links
    assert parser.iframe_sources == {"/uploads/research/remember-loop.html?v=3"}

    expected_images = {f"/uploads/publications/{name}" for name in FIGURES}
    assert expected_images <= parser.image_sources
    for name in FIGURES:
        assert (ROOT / "static/uploads/publications" / name).is_file()

    assert_redirect(PUBLIC / "research/index.html")
    assert_redirect(PUBLIC / "publications/index.html")
    print("publications verification passed")


if __name__ == "__main__":
    main()
