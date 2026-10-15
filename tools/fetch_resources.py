"""Fetch redistributable fonts and upstream license notices from primary repos.

Run only when refreshing these checked-in resources, not on application startup.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from html.parser import HTMLParser
from urllib.parse import urljoin
from pathlib import Path, PurePosixPath
import posixpath
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "PetYourPet-resource-preparation/0.1"}


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def save(url, destination):
    data = fetch(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination.name


def fonts():
    base = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
    jobs = []
    for directory, filename in (("pressstart2p", "PressStart2P-Regular.ttf"),
                                ("ibmplexmono", "IBMPlexMono-Regular.ttf")):
        jobs.append((base + directory + "/" + filename, ROOT / "assets" / "fonts" / filename))
        jobs.append((base + directory + "/OFL.txt", ROOT / "LICENSES" / (directory + "-OFL.txt")))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(lambda job: save(*job), jobs):
            print("Font resource:", name, flush=True)


BASE = "https://doc.qt.io/qt-6.12/"

class Index(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = False
        self.group = ""
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2":
            self.heading = True
            self.group = ""
        if tag == "a" and self.group in ("Qt Core", "Qt GUI", "Qt Image Formats", "Qt Network", "Qt Widgets", "Qt SVG"):
            href = attrs.get("href", "")
            if "-attribution-" in href and href.endswith(".html"):
                self.urls.add(urljoin(BASE, href))

    def handle_endtag(self, tag):
        if tag == "h2":
            self.heading = False

    def handle_data(self, data):
        if self.heading:
            self.group += data
            self.group = self.group.strip()


class Notice(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = False
        self.name = ""
        self.pre = False
        self.current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.title = True
        if tag == "pre":
            self.pre = True
            self.current = []
        if tag == "br" and self.pre:
            self.current.append("\n")

    def handle_endtag(self, tag):
        if tag == "h1":
            self.title = False
        if tag == "pre":
            self.pre = False
            block = "".join(self.current).strip()
            if block:
                self.blocks.append(block)

    def handle_data(self, data):
        if self.title:
            self.name += data
        if self.pre:
            self.current.append(data)


def collect_qt_notices():
    index = Index()
    index.feed(fetch(BASE + "licenses-used-in-qt.html").decode("utf-8"))
    # These notices explicitly describe platform-specific code outside Windows x64.
    excluded = ("cocoa", "qeventdispatcher", "android", "xserver", "xcb", "forkfd", "pixman")
    urls = sorted(url for url in index.urls if not any(name in url for name in excluded))
    if len(urls) < 25:
        raise RuntimeError("Qt notice index did not contain the expected components")
    header = ("QT / PYSIDE6 / SHIBOKEN AND INCLUDED THIRD-PARTY NOTICES\n"
              "Qt / PySide6 / Shiboken version: 6.12.0\n"
              "Copyright (C) The Qt Company Ltd. and contributors.\n"
              "Used under LGPL v3; full LGPL v3 and GPL v3 texts accompany this file.\n"
              "Qt sources: https://code.qt.io/cgit/qt/qtbase.git/ (v6.12.0)\n"
              "Bindings: https://code.qt.io/cgit/pyside/pyside-setup.git/ (v6.12.0)\n"
              "Other shipped modules: Qt SVG and Qt Image Formats.\n"
              "This software is based in part on the work of the Independent JPEG Group.\n\n"
              "Component notices below cover the shipped Windows Qt Core, GUI, Widgets,\n"
              "Network, SVG and image-format libraries/plugins. Optional features within\n"
              "those prebuilt libraries are conservatively covered; these are not a\n"
              "claim that every feature is used by the Python application.\n\n")

    def read(url):
        notice = Notice()
        notice.feed(fetch(url).decode("utf-8"))
        if not notice.name or not notice.blocks:
            raise RuntimeError("Missing original notice text: " + url)
        return (notice.name, url, notice.blocks)

    with ThreadPoolExecutor(max_workers=8) as pool:
        notices = list(pool.map(read, urls))
    chunks = [header]
    for name, url, blocks in notices:
        chunks.extend(["=" * 78, name, "Source: " + url, "\n\n".join(blocks), ""])
    return "\n".join(chunks), notices


def qt_notices():
    text, notices = collect_qt_notices()
    target = ROOT / "LICENSES/QT-THIRD-PARTY.txt"
    if target.exists():
        previous = target.read_text(encoding="utf-8")
        marker = "\n" + "=" * 78 + "\nFULL LICENSE TEXT: "
        position = previous.find(marker)
        if position >= 0:
            text += previous[position:]
    target.write_text(text, encoding="utf-8")
    print("Refreshed", len(notices), "Qt notices in one file")


if __name__ == "__main__":
    fonts()
    qt_notices()
