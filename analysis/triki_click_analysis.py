#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aux module to calculate differences between sites when accepting or rejecting cookies
   Relies on a yaml configuration file created for browser cookie analysis automation"""
import os
import json
import logging
import yaml
from collections import Counter

# from PIL import Image
CWD = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(CWD, "..", "config")

LOG = logging.getLogger()


def _set_logging():
    """
    Setup logging based on envvars and opinated defaults
    """
    log_level = os.getenv("TRIKI_LOG_LEVEL", "INFO")
    quiet = os.getenv("TRIKI_NO_LOG_FILE")
    handlers = [logging.StreamHandler()]
    if not quiet:
        handlers.append(logging.FileHandler("triki_click_analysis.log"))
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


def clean_incomplete_flows(d):

    result = {}
    for url in d.copy():
        if len(d[url].keys()) < 2:
            continue
        else:
            result[url] = d[url]["reject"] - d[url]["accept"]
    sorted_d = {k: v for k, v in sorted(result.items(), key=lambda item: item[1])}
    return sorted_d


def run():
    """
    Analyze cookies for a given site
    """
    # Configure logging
    _set_logging()

    # Read sites configuration
    config = _config()
    click_stats = {}
    for site in config["sites"]:
        if site["flow_type"] == "browse":
            continue

        if site["url"] not in click_stats:
            click_stats[site["url"]] = {}
        clicks = 0
        for step in site["flow"]:
            if step["action"] == "click":
                clicks += 1
        click_stats[site["url"]][site["flow_type"]] = clicks
    result = clean_incomplete_flows(click_stats)
    with open("%s/click_stats.json" % (CWD), "w") as f_out:
        f_out.write(json.dumps(result))
    freq = Counter(result.values())
    for key in freq:
        LOG.info("There are %s percentage of sites that differ in %s clicks between accepting and rejecting cookies", round((freq[key]*100/len(result))), key)
    LOG.debug(result)


if __name__ == "__main__":
    run()
