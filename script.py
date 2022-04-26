import logging
import os
import sys
import urllib
import requests

import twill
from bs4 import BeautifulSoup
from twill.commands import formclear, fv, go, show, submit

USERNAME = ""
PASSWORD = ""
LOG_LEVEL = logging.INFO
CONTENTS_URL = "https://moodle.ucl.ac.uk/course/resources.php?id=5900"
LINKS_FILENAME = "links.txt"
UPDATE_LINKS = False
DISCARD_TYPES = ["ppsx", "video"]
ACCEPT_TYPES = ["*"]


def login(logger):
    go("https://moodle.ucl.ac.uk")
    formclear("2")
    fv("2", "username", USERNAME)
    fv("2", "password", PASSWORD)
    submit("2")
    logger.info("Logged in")
    return requests.utils.dict_from_cookiejar(twill.browser._session.cookies)


def get_links(logger):
    null_out = open(os.devnull, "w")
    std_out = sys.stdout
    file_out = open("file_out.html", "w")
    html = get_html(CONTENTS_URL, null_out, std_out)
    soup = BeautifulSoup(html, "html.parser")
    c1_elements = soup.find_all("td", {"class": "c1"})
    links = []
    for c1_element in c1_elements:
        link = c1_element.find("a", href=True)["href"]
        if "url" in link:
            # logger.debug(f"url {link}")
            pass  # ignore, mostly youtube videos
        elif "folder" in link:
            logger.debug(f"folder {link}")
            html = get_html(link, null_out, std_out)
            soup = BeautifulSoup(html, "html.parser")
            link_elements = soup.find_all("span", {"class": "fp-filename-icon"})
            for link_element in link_elements:
                sub_link = link_element.find("a", href=True)["href"]
                content_type, content_size = query_headers(sub_link, cookies)
                if ACCEPT_TYPES[0] != "*":
                    if content_type in ACCEPT_TYPES:
                        links.append(sub_link)
                        logger.debug(f"sub link: {sub_link}")
                else:
                    links.append(sub_link)
                    logger.debug(f"sub link: {sub_link}")
        elif "resource" in link:
            # logger.debug(f"resource {link}")
            content_type, content_size = query_headers(link, cookies)
            if content_type == "html":
                html = get_html(link, null_out, std_out)
                soup = BeautifulSoup(html, "html.parser")
                file_links = soup.find_all("div", {"class": "resourceworkaround"})
                for file_link in file_links:
                    sub_link = file_link.find("a", href=True)["href"]
                    content_type, content_size = query_headers(sub_link, cookies)
                if ACCEPT_TYPES[0] != "*":
                    if content_type in ACCEPT_TYPES:
                        links.append(sub_link)
                        logger.debug(f"resource sub link: {sub_link}")
                else:
                    links.append(sub_link)
                    logger.debug(f"resource sub link: {sub_link}")
            else:
                for type in DISCARD_TYPES:
                    if content_type == type:
                        break
                links.append(link)
                logger.debug(f"link: {link}")
    return links


def get_html(link, null_out, std_out):
    go(link)
    twill.set_output(null_out)
    html = show()
    twill.set_output(std_out)
    return html


def download(url, cookies, logger):
    response = requests.get(url, stream=True, cookies=cookies)

    if not response.ok:
        raise Exception("Could not get file from " + url)

    logger.debug(f"url: {url}")
    file_name = response.headers.get("Content-Disposition").split("filename=")[1]
    file_name = file_name[1:-1]
    logger.debug(f"file name:{file_name}")
    with open(file_name, "wb") as handle:
        for block in response.iter_content(1024):
            handle.write(block)
        logger.info(f"Downloaded {file_name}")


def query_headers(url, cookies):
    response = requests.get(url, stream=True, cookies=cookies)
    headers = response.headers

    Content_Disposition_Exists = bool(
        {key: value for key, value in headers.items() if key == "Content_Disposition"}
    )
    if Content_Disposition_Exists is True:
        # do something with the file
        pass
    else:
        Content_Type = {
            value for key, value in headers.items() if key == "Content-Type"
        }

        compression_formats = [
            "application/gzip",
            "application/vnd.rar",
            "application/x-7z-compressed",
            "application/zip",
            "application/x-tar",
        ]
        compressed_file = bool(
            [
                file_format
                for file_format in compression_formats
                if file_format in Content_Type
            ]
        )

        image_formats = [
            "image/bmp",
            "image/gif",
            "image/jpeg",
            "image/png",
            "image/svg+xml",
            "image/tiff",
            "image/webp",
        ]
        image_file = bool(
            [
                file_format
                for file_format in image_formats
                if file_format in Content_Type
            ]
        )

        video_formats = ["video/mp4", "video/mpeg", "video/webm", "video/x-msvideo"]
        video_file = bool(
            [
                file_format
                for file_format in video_formats
                if file_format in Content_Type
            ]
        )

        word_formats = [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        word_file = bool(
            [file_format for file_format in word_formats if file_format in Content_Type]
        )

        excel_formats = [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
        excel_file = bool(
            [
                file_format
                for file_format in excel_formats
                if file_format in Content_Type
            ]
        )

        ppsx_formats = [
            "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
            "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
            "application/vnd.ms-powerpoint.slideshow.macroEnabled.12",
        ]
        ppsx_file = bool(
            [file_format for file_format in ppsx_formats if file_format in Content_Type]
        )

        pptx_formats = [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]
        pptx_file = bool(
            [file_format for file_format in pptx_formats if file_format in Content_Type]
        )

        text_formats = ["application/rtf", "text/plain"]
        text_file = bool(
            [file_format for file_format in text_formats if file_format in Content_Type]
        )

        content_size = get_content_size(headers)
        if compressed_file is True:
            return "compressed", content_size
        elif image_file is True:
            return "image", content_size
        elif video_file is True:
            return "video", content_size
        elif excel_file is True:
            return "excel", content_size
        elif word_file is True:
            return "word", content_size
        elif pptx_file is True:
            return "pptx", content_size
        elif ppsx_file is True:
            return "ppsx", content_size
        elif image_file is True:
            return "image", content_size
        elif text_file is True:
            return "text", content_size
        elif "application/pdf" in Content_Type:
            return "pdf", content_size
        elif "text/html" in "".join(str(Content_Type)):
            return "html", content_size
        else:
            return "unknown", content_size


def get_content_size(headers):
    Content_Length = [
        value for key, value in headers.items() if key == "Content-Length"
    ]
    if len(Content_Length) > 0:
        Content_Size = "".join(map(str, Content_Length))
        return int(Content_Size)
    else:
        return 0


if __name__ == "__main__":
    logging.basicConfig(
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)
    cookies = login(logger)
    if UPDATE_LINKS or not os.path.exists(LINKS_FILENAME):  # load links, save to file
        links = get_links(logger)
        with open(LINKS_FILENAME, "w+") as handle:
            for link in links:
                handle.write(link)
                handle.write("\n")
    else:  # load links from file
        with open(LINKS_FILENAME, "r") as handle:
            links = handle.readlines()
    for link in links:
        logger.debug(f"Link: {link}")
        download(link, cookies, logger)
    logger.info(f"Done. Downloaded {len(links)} files in total.")
