#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module uses selenium automation to visit a list of sites loaded
   from configuration and either accept or reject cookies retrieving the
   cookies created during the visit and creating statistics around them.
   It also screenshots the site and some of its important elements
   regarding cookies."""
import csv
import logging
import os
import platform
import sqlite3
import sys
from collections import Counter
from shutil import rmtree
from time import sleep
from urllib.parse import urlparse

import arrow
import yaml
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException,
                                        TimeoutException)
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# from PIL import Image
CWD = os.path.dirname(__file__)
DATA_PATH = os.path.join(CWD, "data")
CONFIG_PATH = os.path.join(CWD, "config")
PROFILE_PATH = os.path.abspath(os.path.join(CWD, "profile"))
HEADER_COOKIES = [
    "host_key",
    "name",
    "value",
    "path",
    "expires_utc",
    "is_secure",
    "is_httponly",
    "has_expires",
    "is_persistent",
    "priority",
    "samesite",
    "source_scheme",
]
HEADER_STATS = [
    "url",
    "total",
    "session",
    "max_exp_days",
    "avg_exp_days",
    "secure_flag",
    "httponly_flag",
    "samesite_none_flag",
    "samesite_lax_flag",
    "samesite_strict_flag",
]

LOG = logging.getLogger()


def _set_logging():
    """
    Setup logging based on envvars and opinated defaults
    """
    log_level = os.getenv("TRIKI_LOG_LEVEL", "INFO")
    quiet = os.getenv("TRIKI_NO_LOG_FILE")
    handlers = [logging.StreamHandler()]
    if not quiet:
        handlers.append(logging.FileHandler("triki.log"))
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(levelname)s: %(message)s",
        handlers=handlers,
    )


def _config():
    """
    read sites configuration and accept and reject flows for cookie extraction
    """
    config = None
    try:
        with open("%s/sites.yaml" % CONFIG_PATH, "r", encoding="utf8") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except Exception as e:
        LOG.error("Could not load triki configuration: %s", e)
        raise e
    return config


def _get_duration_in_days(expires_utc):
    """
    via: https://stackoverflow.com/questions/43518199/cookies-expiration-time-format
    and https://stackoverflow.com/questions/51343828/how-to-parse-chrome-bookmarks-date-added-value-to-a-date
    """
    now = arrow.utcnow()
    epoch_start = arrow.get(1601, 1, 1)
    expiration_date = epoch_start.shift(microseconds=int(expires_utc))
    days = (expiration_date - now).days
    return days


def _sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_cookies():
    """
    Access google chrome profile cookies sqlite databasex
    """
    results = []
    db = os.path.join(PROFILE_PATH, "Default", "Cookies")
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = _sqlite_dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cookies order by host_key, expires_utc desc")
        results = cursor.fetchall()
        LOG.info("Encontradas %s cookies", len(results))
    except Exception as e:
        LOG.error("get_cookies: %s", e)
        raise e
    return results


def export_cookies(cookies, path):
    """
    Export cookies pickling them to file
    """
    try:
        with open(path, "w") as f:
            writer = csv.DictWriter(
                f, fieldnames=HEADER_COOKIES, extrasaction="ignore", restval=0
            )
            writer.writeheader()
            writer.writerows(cookies)
    except Exception as e:
        LOG.error(e)
        raise e


def export_stats(stats, path):
    """
    Export cookies pickling them to file
    """
    try:
        with open(path, "w") as f:
            writer = csv.DictWriter(
                f, fieldnames=HEADER_STATS, extrasaction="ignore", restval=0
            )
            writer.writeheader()
            writer.writerow(stats)
    except Exception as e:
        LOG.error(e)
        raise e


def cookie_stats(cookies, url):
    """
    Compute cookie statistics
    """
    stats = {"url": url}
    LOG.debug("We have found %s cookies for %s", len(cookies), url)
    stats["total"] = len(cookies)
    session_cookies = [cookie for cookie in cookies if not int(cookie["is_persistent"])]
    LOG.debug("There are %s session cookies", len(session_cookies))
    stats["session"] = len(session_cookies)

    # Compute expiration maximum and average in days
    delta_expiration_days = [
        _get_duration_in_days(cookie["expires_utc"])
        for cookie in cookies
        if int(cookie["is_persistent"])
    ]
    if delta_expiration_days:
        stats["max_exp_days"] = max(delta_expiration_days)
        LOG.debug("max expiration in days is %s", max(delta_expiration_days))
        stats["avg_exp_days"] = int(
            round(sum(delta_expiration_days) / len(delta_expiration_days))
        )
        LOG.debug("average expiration in days: %s", stats["avg_exp_days"])
    else:
        stats["max_exp_days"] = 0
        stats["avg_exp_days"] = 0
    # Get secure and httponly stats
    secure = 0
    http_only = 0
    for cookie in cookies:
        if int(cookie["is_secure"]):
            secure += 1
        if int(cookie["is_httponly"]):
            http_only += 1
    stats["secure_flag"] = secure
    LOG.debug("There are %s secure cookies", stats["secure_flag"])
    stats["httponly_flag"] = http_only
    LOG.debug("There are %s httpOnly cookies", stats["httponly_flag"])

    #  SameSite
    same_site = Counter([str(cookie["samesite"]) for cookie in cookies])
    LOG.debug("same_site %s", same_site)
    stats["samesite_none_flag"] = same_site["-1"]
    stats["samesite_lax_flag"] = same_site["0"]
    stats["samesite_strict_flag"] = same_site["1"]
    LOG.debug(
        "There are %s cookies with SameSite set to None", stats["samesite_none_flag"]
    )
    LOG.debug(
        "There are %s cookies with SameSite set to Lax", stats["samesite_lax_flag"]
    )
    LOG.debug(
        "There are %s cookies with SameSite set to Strict",
        stats["samesite_strict_flag"]
    )
    return stats


def _locate_element(driver, el):
    """
    locate an element inside the page using selenium capabilities
    """
    element = None
    # Check if we expect multiple elements to be selected
    multiple = False
    match = None
    try:
        multiple = el["multiple"]
        match = el["match"].strip().lower()
    except KeyError:
        pass

    try:
        if multiple:
            selection = driver.find_elements(el["by"], el["value"])
            LOG.debug("found %s", len(selection))
            # found multiple use match to refine
            if selection and len(selection) >= 1:
                for selected in selection:
                    if match in selected.text.lower():
                        element = selected
                        break
        else:
            element = driver.find_element(el["by"], el["value"])
    except Exception as e:
        LOG.error("Could not locate the element in the page: %s", el)
        raise e
    return element


def screenshot(driver, el, filepath, filename=None):
    """
    takes a screenshot of an element or the whole site
    """
    if not el:
        el = {"by": "tag name", "value": "body"}
    if not filename:
        filename = el["value"].replace(".", "_")

    element = _locate_element(driver, el)
    element.screenshot("%s/banner_cookies_%s.png" % (filepath, filename))


def navigate_frame(driver, el):
    """
    navigate to iframe by index using selenium capabilities
    """

    if "index" in el:
        driver.switch_to.frame(el["index"])
    else:
        element = _locate_element(driver, el)
        driver.switch_to.frame(element)


def click(driver, el):
    """
    clicks on an element using selenium capabilities
    """
    element = _locate_element(driver, el)
    LOG.debug("element: %s", element)
    if "javascript" in el:
        driver.execute_script("arguments[0].scrollIntoView(true);",element)
        driver.execute_script("arguments[0].click();", element)
    else:
        try:
            element.click()
        except ElementClickInterceptedException as e:
            LOG.debug("try click through javascript after exception")
            driver.execute_script("arguments[0].scrollIntoView(true);",element)
            driver.execute_script("arguments[0].click();", element)


def delay(driver, el, value):
    """
    Wait for something to happen in the site
    """
    TRIKI_AVAILABLE_CONDITIONS = {
        "element_to_be_clickable": EC.element_to_be_clickable,
        "presence_of_element_located": EC.presence_of_element_located,
        "visibility_of_element_located": EC.visibility_of_element_located,
    }
    if el:
        if "condition" in el:
            expected_condition_method = TRIKI_AVAILABLE_CONDITIONS[el["condition"]]
        else:
            expected_condition_method = EC.element_to_be_clickable
        try:
            WebDriverWait(driver, value).until(
                expected_condition_method((el["by"], el["value"]))
            )
        except TimeoutException as e:
            LOG.info("Timeout for explicit wait on %s", el)
            raise e
    else:
        driver.implicitly_wait(value)

def keys(driver, el, value):
    """
    Wait for something to happen in the site
    """
    element = _locate_element(driver, el)
    element.clear()
    element.send_keys(value)

def submit(driver, el):
    """
    clicks on an element using selenium capabilities
    """
    element = _locate_element(driver, el)
    element.submit()


def execute_cookies_flow(site, site_path, hostname):
    """
    Navigates to a site and depending on the selected flow
    accepts or rejects all the cookies and stores results, screenshots
    and statistics on the cookies for the site
    """
    TRIKI_AVAILABLE_ACTIONS = {
        "screenshot": screenshot,
        "navigate_frame": navigate_frame,
        "click": click,
        "delay": delay,
        "sleep": sleep,
        "keys": keys,
        "submit": submit,
    }
    # Clear profile to start fresh always

    if os.path.exists(PROFILE_PATH):
        rmtree(PROFILE_PATH)
    os.makedirs(PROFILE_PATH)
    # Selenium Chrome initialization with a intended profile
    opts = ChromeOptions()
    # Seems that it does not create the Cookies sqlite db
    # opts.add_argument("--headless")
    opts.add_argument("user-data-dir=%s" % PROFILE_PATH)
    prefs = {}
    # Force browser language
    if "language" in site:
        prefs["intl.accept_languages"] = site["language"]
    else:
        # Defaults to spanish
        prefs["intl.accept_languages"] = "es, es-ES"

    # Try to block cookies
    # 1: allow, 2: block
    # via: https://stackoverflow.com/questions/32381946/disabling-cookies-in-webdriver-for-chrome-firefox/32416545
    if "block_all_cookies" in site:
        prefs["profile.default_content_setting_values.cookies"] = 2
        site["flow_type"] += "_block_all"
    # Try to block third party cookies
    # Force browser language
    if "block_third_party_cookies" in site:
        prefs["profile.block_third_party_cookies"] = True
        site["flow_type"] += "_block_third_party"

    if "enable_do_not_track" in site:
        prefs["enable_do_not_track"] = True
        site["flow_type"] += "_do_not_track"

    opts.add_experimental_option("prefs", prefs)
    # Fix window size to be consistent across
    opts.add_argument("window-size=1920,1080")
    opts.add_argument("--log-level=3")

    driver = Chrome(options=opts)
    try:
        LOG.info("Analysing %s %sing all cookies", site["url"], site["flow_type"])
        driver.get(site["url"])
        if not os.path.exists(site_path):
            os.makedirs(site_path)
        for step in site["flow"]:
            function = TRIKI_AVAILABLE_ACTIONS[step["action"]]
            if step["action"] == "screenshot":
                if "filename" not in step:
                    step["filename"] = None
                function(driver, step["element"], site_path, step["filename"])
            elif step["action"] == "navigate_frame":
                function(driver, step["element"])
            elif step["action"] == "click":
                function(driver, step["element"])
            elif step["action"] == "submit":
                function(driver, step["element"])
            elif step["action"] == "keys":
                function(driver, step["element"], step["value"])
            elif step["action"] == "delay":
                function(driver, step["element"], step["value"])
            elif step["action"] == "sleep":
                function(step["value"])
            LOG.info("done with step: %s", step)
    except Exception as e:
        LOG.error("Exception while processing flow %s", e)
        raise
    finally:
        driver.close()

    # Retrieve and compute stats over the site cookies
    # Generate paths
    cookies_path = "%s/cookies_%s_%s.csv" % (
        site_path,
        site["flow_type"],
        hostname.replace(".", "_"),
    )
    stats_path = "%s/stats_%s_%s.csv" % (
        site_path,
        site["flow_type"],
        hostname.replace(".", "_"),
    )

    # Retrieve cookies from sqlite
    cookies = get_cookies()
    LOG.debug(cookies)
    # Export cookies to csv
    export_cookies(cookies, cookies_path)
    # Compute cookie stats
    stats = cookie_stats(cookies, site["url"])
    # Export cookie stats to csv
    export_stats(stats, stats_path)


def run():
    """
    Analyze cookies for a given site
    """
    # Configure logging
    _set_logging()

    # Create output folders if needed
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)

    # Read sites configuration
    config = _config()

    for site in config["sites"]:
        try:
            LOG.debug(site)
            today = arrow.utcnow().format("YYYYMMDD")
            url = urlparse(site["url"])
            site_path = os.path.join(DATA_PATH, url.hostname, today)
            execute_cookies_flow(site, site_path, url.hostname)
        except (KeyboardInterrupt, SystemExit):
            sys.exit()
        except Exception as e:
            LOG.error("Found error while processing %s", site["url"])


    # Delete last profile from selenium execution adding more time for windows
    if platform.system() == "Windows":
        sleep(20)
    if os.path.exists(PROFILE_PATH):
        rmtree(PROFILE_PATH)


if __name__ == "__main__":
    run()
