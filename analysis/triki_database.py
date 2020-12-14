#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import logging
import sqlite3
from shutil import rmtree
from sqlite3 import Error
import csv

CWD = os.path.dirname(__file__)
DATABASE_PATH = os.path.join(CWD, "db")

LOG = logging.getLogger()

# CREATE TABLES

QUERY_CREATE_COOKIES_TABLE = """ CREATE TABLE IF NOT EXISTS cookies (
                                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                url varchar(255) NOT NULL,
                                date DATETIME DEFAULT CURRENT_DATE NOT NULL,
                                flow VARCHAR(15) NOT NULL,
                                block_third_party BOOLEAN NOT NULL,

                                host VARCHAR(255) NOT NULL,
                                name VARCHAR(255) NOT NULL,

                                value VARCHAR(255),
                                path VARCHAR(255)  NOT NULL,
                                expires_utc INTEGER,
                                is_secure BOOLEAN NOT NULL,
                                is_httponly BOOLEAN NOT NULL,
                                has_expires BOOLEAN NOT NULL,
                                is_persistent BOOLEAN NOT NULL,
                                priority BOOLEAN NOT NULL,
                                samesite BOOLEAN NOT NULL,
                                source_scheme integer NOT NULL,

                                UNIQUE (host, name, path, date, flow, block_third_party, url)
                            ); """

QUERY_CREATE_STATS_TABLE = """CREATE TABLE IF NOT EXISTS stats (
                                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                url varchar(255) NOT NULL,
                                date DATETIME DEFAULT CURRENT_DATE NOT NULL,
                                flow VARCHAR(15) NOT NULL,
                                block_third_party BOOLEAN NOT NULL,

                                total INTEGER NOT NULL,
                                session INTEGER NOT NULL,
                                max_exp_days INTEGER NOT NULL,
                                avg_exp_days INTEGER NOT NULL,
                                secure_flag INTEGER NOT NULL,
                                httponly_flag INTEGER NOT NULL,
                                samesite_none_flag INTEGER NOT NULL,
                                samesite_lax_flag INTEGER NOT NULL,
                                samesite_strict_flag INTEGER NOT NULL,

                                UNIQUE (date, flow, block_third_party, url)

                            ); """

# INSERTS (Querys and Values)
# Querys
QUERY_INSERT_TABLE_COOKIES = "INSERT INTO cookies(url, date, flow, block_third_party, host, name, value, path, expires_utc, is_secure, is_httponly, has_expires, is_persistent, priority, samesite, source_scheme) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
QUERY_INSERT_TABLE_STATS = "INSERT INTO stats(url, date, flow, block_third_party, total, session, max_exp_days, avg_exp_days, secure_flag, httponly_flag, samesite_none_flag, samesite_lax_flag, samesite_strict_flag) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"


def _csv_to_db(conn_db, path, url, date, csv_dict, sql):
    for key in csv_dict.keys():
        csv_name = csv_dict[key]
        csv_path = os.path.join(path, csv_name)
        block_third_party = "third_party" in key
        flow = key.split("_")[0]
        attributes_rows = [url, date, flow, block_third_party]
        values = []
        with open(csv_path, newline='') as File:
            reader = csv.reader(File)
            reader = list(reader)[1:]
            for row in reader:
                if sql == QUERY_INSERT_TABLE_STATS:
                    row = row[1:]
                row = attributes_rows + row
                values.append(tuple(row))
            try:
                _insert_table(conn_db, sql, values)
            except Error as e:
                LOG.error(e)
                raise e


def _save_csv_to_db(conn_db, site_dict):
    root_path = site_dict["root_path"]
    url = site_dict["url"]
    for dir_name in site_dict["dates"].keys():
        cookies_dict = site_dict["dates"][dir_name]["cookies"]
        stats_dict = site_dict["dates"][dir_name]["stats"]
        path = os.path.join(root_path, dir_name)
        _csv_to_db(conn_db, path, url, dir_name, cookies_dict, QUERY_INSERT_TABLE_COOKIES)
        _csv_to_db(conn_db, path, url, dir_name, stats_dict, QUERY_INSERT_TABLE_STATS)


def _save_to_db(conn_db, site_dict):
    url = site_dict["url"]
    try:
        _save_csv_to_db(conn_db, site_dict)
        LOG.info("Insert: %s.", url)
    except Exception as e:
        LOG.error("Insert failed: %s (%s)", url, e)


def _get_directories(path):
    with os.scandir(path) as directories:
        return [directory.name for directory in directories if directory.is_dir()]


def _get_CSVs(path):
    csv_dict = {
        "cookies": {},
        "stats": {}
    }

    with os.scandir(path) as files:
        for _file in files:
            if _file.is_file() and _file.name.endswith('.csv'):
                type_list = _file.name.split("_")[:3]
                is_block = "block" in type_list[2]
                table_name = type_list[0]
                if is_block:
                    flow_name = type_list[1] + "_third_party"
                else:
                    flow_name = type_list[1]
                csv_dict[table_name][flow_name] = _file.name

        return csv_dict


def _import_data_to_db(conn_db, data_path):
    site_dict = {}
    LOG.info("[!] Browsing data path...\n")
    site_dir = _get_directories(data_path)

    for site_name in site_dir:
        site_path = os.path.join(data_path, site_name)
        site_dict["url"] = site_name
        site_dict["root_path"] = site_path
        site_dict["dates"] = {}
        dates_per_site = _get_directories(site_path)
        for date_site in dates_per_site:
            date_site_path = os.path.join(site_path, date_site)
            csv_per_date_dict = _get_CSVs(date_site_path)
            site_dict["dates"][date_site] = csv_per_date_dict
        _save_to_db(conn_db, site_dict)

    LOG.info("[*] Site data imported successfully!\n")


def _insert_table(conn, sql, values):
    cur = conn.cursor()
    for value in values:
        cur.execute(sql, value)
    conn.commit()
    return cur.lastrowid


def _create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        conn.commit()
    except Error as e:
        raise e


def _create_database(conn):
    query_table_list = [QUERY_CREATE_COOKIES_TABLE, QUERY_CREATE_STATS_TABLE]
    for query in query_table_list:
        _create_table(conn, query)
    LOG.info("[*] Successful database creation.\n")


def _create_connection(db_file):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
        raise e


def _set_logging():
    """
    Setup logging based on envvars and opinated defaults
    """
    log_level = os.getenv('TRIKI_DATABASE_LOG_LEVEL', "INFO")
    quiet = os.getenv('TRIKI_DATABASE_LOG_FILE', None)
    handlers = [logging.StreamHandler()]
    if not quiet:
        handlers.append(logging.FileHandler("triki_database.log"))
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(levelname)s: %(message)s",
        handlers=handlers,
    )


def run(params):
    _set_logging()
    try:
        if not params.keep_db:
            LOG.info("[*] Wipe database to start fresh.\n")
            if os.path.exists(DATABASE_PATH):
                rmtree(DATABASE_PATH)
            os.makedirs(DATABASE_PATH)

        conn_db = _create_connection("%s/site_cookies.db" % (DATABASE_PATH))
        if not params.keep_db:
            _create_database(conn_db)

        # Import data
        _import_data_to_db(conn_db, params.data_path)
    except Exception as e:
        LOG.error("Found error %s", e)
    finally:
        # close the connection
        conn_db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--import', '-i', dest="data_path", type=str, default=None, required=True,
                        help='Import data to the database. --import / -i <directory_data>')
    parser.add_argument('--keep-database', '-k', action="store_true", default=False, dest="keep_db",
                        help='Keep existing database, useful to only import new data')

    params = parser.parse_args()
    run(params)
