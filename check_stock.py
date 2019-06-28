#!/usr/bin/env python3
import pprint
import json
import requests
import sys
import logging
import re
import datetime
from bs4 import BeautifulSoup, NavigableString
from queue import Queue
from threading import Thread
import sqlite3


url_base = 'https://www.lenovo.com/us/en/outletus/laptops/c/LAPTOPS'
url_template = 'https://www.lenovo.com/us/en/outletus/laptops/c/LAPTOPS?q=%3Aprice-asc&page='
base_url = 'https://www.lenovo.com'
products = []
#outlet_products_table = 'outlet_items'
outlet_products_table = 'items'



def _fix_url(url):
    if url.startswith('/'):
        return f'{base_url}{url}'
    else:
        return url


def _get_url_content(url):
    r = requests.get(url, allow_redirects=True)
    if r.status_code != 200:
        logging.fatal(f'Status code is {r.status_code}')
        sys.exit(1)
    if len(r.content) == 0:
        logging.fatal('Returned content has len of 0')
        sys.exit(1)
    return r.content


def _get_soup_from_url(url):
    #print(url)
    return BeautifulSoup(_get_url_content(url), "lxml")


def _extract_laptop_details(container):
    product = {
        'title': None,
        'condition': None,
        'url': None,
        'list_price': None,
        'outlet_price': None,
        'saving': None,
        'left': None,
        'part_no': None,
        'processor': None,
        'os': None,
        'hdd': None,
        'graphics': None,
        'warranty': None,
        'memory': None,
        'battery': None
    }

    for part in container:
        while isinstance(part, NavigableString):
            part = part.next_element

        if not product['url']:
            for link in part.find_all('a', {'class': 'facetedResults-cta'}):
                product['url'] = _fix_url(link.get('href'))

        if not product['title']:
            for h3 in part.find_all('h3', {'class': 'facetedResults-title'}):
                a = h3.find('a')
                details = a.text.rsplit('-', 1)
                product['title'] = details[0].rstrip()
                product['condition'] = details[1].lstrip()

        if not product['list_price']:
            for dd in part.find_all('dd', {'itemprop': 'listPrice'}):
                product['list_price'] = dd.text.lstrip().rstrip()

        if not product['outlet_price']:
            for dd in part.find_all('dd', {'itemprop': 'price'}):
                product['outlet_price'] = dd.text.lstrip().rstrip()

        if not product['saving']:
            for dd in part.find_all('dd', {'itemprop': 'youSave'}):
                product['saving'] = dd.text.lstrip().rstrip()

        if not product['left']:
            for span in part.find_all('span', {'class': 'rci-msg'}):
                no_dt = span.text.split('<', 1)
                product['left'] = no_dt[0].lstrip().rstrip()

        if not product['part_no']:
            for dt in part.find_all('dt', text='Part number:'):
                product['part_no'] = dt.parent.findNext('dd').contents[0]

        if not product['processor']:
            for dt in part.find_all('dt', text='Processor:'):
                product['processor'] = dt.parent.findNext('dd').contents[0]

        if not product['os']:
            for dt in part.find_all('dt', text='Operating System:'):
                product['os'] = dt.parent.findNext('dd').contents[0]

        if not product['hdd']:
            for dt in part.find_all('dt', text='Hard Drive:'):
                product['hdd'] = dt.parent.findNext('dd').contents[0]

        if not product['graphics']:
            for dt in part.find_all('dt', text='Graphics:'):
                product['graphics'] = dt.parent.findNext('dd').contents[0]

        if not product['warranty']:
            for dt in part.find_all('dt', text='Warranty:'):
                product['warranty'] = dt.parent.findNext('dd').contents[0]

        if not product['memory']:
            for dt in part.find_all('dt', text='Memory:'):
                product['memory'] = dt.parent.findNext('dd').contents[0]

        if not product['battery']:
            for dt in part.find_all('dt', text='Battery:'):
                product['battery'] = dt.parent.findNext('dd').contents[0]

    return product


def _find_laptops(soup):
    products = []
    results = soup.find_all('div', id="resultsList")
    try:
        laptops_containers = results[0].find_all('div', {"class" : "facetedResults-item only-allow-small-pricingSummary"})
    except:
        logging.fatal("Couldn't extract laptops_containers")
        sys.exit(1)

    for laptop_container in laptops_containers:
        products.append(_extract_laptop_details(laptop_container))

    return products


def _get_last_page():
    last_page = 0
    soup = _get_soup_from_url(url_base)
    links = soup.find_all('a', rel="next")
    for link in links:
        url = link.get('href')
        page = url.split('page=')[1]
        if str.isdigit(page) and int(page) > last_page:
            last_page = int(page)

    if last_page == 0:
        logging.fatal("Didn't find last page number")
        sys.exit(1)

    return last_page


def run_queue(q):
    global products
    while not q.empty():
        page_no = q.get(timeout=5)
        soup = _get_soup_from_url(f'{url_template}{page_no}')
        products += _find_laptops(soup)
        q.task_done()


def is_sqlite3_table(sqlite_cursor, table_name):
    query = f"SELECT name from sqlite_master WHERE type='table' AND name='{table_name}';"
    cursor = sqlite_cursor.execute(query)
    result = cursor.fetchone()
    if result == None:
        return False
    else:
        return True


def create_sqlite3_table(sqlite, sqlite_cursor):
    query = f"CREATE TABLE IF NOT EXISTS {outlet_products_table} (id INTEGER PRIMARY KEY AUTOINCREMENT, left, memory, graphics, url, os, condition, part_no, list_price, processor, battery, saving, outlet_price, warranty, title, hdd, time_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, time_soldout TIMESTAMP, seenbefore DEFAULT 'true')"
    sqlite_cursor.execute(query)
    sqlite.commit()


def _add_item_to_db(product, sqlite_cursor, table):
    columns = ', '.join(product.keys())
    placeholders = ':' + ', :'.join(product.keys())
    query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
    sqlite_cursor.execute(query, product)


def _item_seen_last_run(part_no, condition, sqlite_cursor, table):
    query = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE part_no='{part_no}' AND condition='{condition}' AND time_soldout IS NULL LIMIT 1);"
    sqlite_cursor.execute(query)
    row = sqlite_cursor.fetchone()
    if row[0] == 0:
        return False
    else:
        return True


def _put_products_in_db(sqlite, sqlite_cursor):
    new_products = []

    if not is_sqlite3_table(sqlite_cursor, outlet_products_table):
        create_sqlite3_table(sqlite, sqlite_cursor)

    for product in products:
        item_seen_before = _item_seen_last_run(product['part_no'], product['condition'], sqlite_cursor, outlet_products_table)
        if not item_seen_before:
            _add_item_to_db(product, sqlite_cursor, outlet_products_table)
            new_products.append(product)

    return new_products



def _get_all_products(last_page):
    queue = Queue(maxsize=0)
    for i in range(1, last_page + 1):
        queue.put(i)
    num_threads = 30

    for _ in range(num_threads):
        worker = Thread(target=run_queue, args=(queue,))
        worker.setDaemon(True)
        worker.start()
    queue.join()


def _mark_all_items_for_reappearance(sqlite, sqlite_cursor, table):
    # Mark all items as not seen
    query = f"UPDATE {table} SET seenbefore = 'false'"
    sqlite_cursor.execute(query)
    # mark now all found items as seen in last run
    i = 0
    for product in products:
        query = f"UPDATE {table} SET seenbefore = 'true' WHERE part_no='{product['part_no']}' AND condition='{product['condition']}'"
        sqlite_cursor.execute(query)
        i += 1
        if i % 50 == 0:
            sqlite.commit()
            i = 0

    sqlite.commit()

    # Set timestamp of sold where its not set yet
    query = f"UPDATE {table} SET time_soldout = '{datetime.datetime.now()}' WHERE seenbefore='false' AND time_soldout IS NULL"
    sqlite_cursor.execute(query)
    sqlite.commit()


if __name__ == "__main__":
    now = datetime.datetime.now()
    time_str = now.strftime("%Y-%m-%d_%H%M")
    hits = []

    last_page = _get_last_page()
    _get_all_products(last_page)

    sqlite = sqlite3.connect('/tmp/example.db')
    sqlite_cursor = sqlite.cursor()

    new_products = _put_products_in_db(sqlite, sqlite_cursor)
    _mark_all_items_for_reappearance(sqlite, sqlite_cursor, outlet_products_table)

    sqlite.commit()
    sqlite.close()

    search_terms = ['t480s', 't490s', 'x390']

    for product in new_products:
        for search_term in search_terms:
            if search_term in product['title'].lower():
                if 't480s' in product['title'].lower() and product['condition'] == 'New':
                    continue
                hits.append(product)

    with open(f'/tmp/data/{time_str}_all_data.json', 'w') as json_file:
        json.dump(products, json_file)

    with open(f'/tmp/data/{time_str}_new.json', 'w') as json_file:
        json.dump(new_products, json_file)

    with open(f'/tmp/data/{time_str}_hits.json', 'w') as json_file:
        json.dump(hits, json_file)

    if len(new_products) > 0:
        print("NEW PRODUCTS")
        pprint.pprint(new_products)
    if len(hits) > 0:
        print('----')
        print("TARGETED HITS")
        pprint.pprint(hits)
