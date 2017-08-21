#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# © 2017 Jacopo Jannone


from __future__ import print_function  # For those still using Python 2
import sys
import requests
from lxml import html
from time import sleep
import os
import re
import textwrap
import argparse
try:
    import readline
except ImportError:
    # readline does not exist on Windows
    pass
try:
   input = raw_input # If we are on Python 2
except NameError:
   pass

# Strings and constants
progr_desc = "Cerca e scarica torrent da TNTVillage."
query_desc = "termine di ricerca"
more_desc = "mostra 21 risultati per pagina anzi che 7."
search_url = "http://www.tntvillage.scambioetico.org/src/releaselist.php"
tot_pag_addr = "//div[@class='pagination']/form/span/b[3]/text()"
result_table_addr = "//div[@class='showrelease_tb']/table/tr"
title_addr = "./td[7]/a/text()"
desc_addr = "./td[7]/text()"
dl_addr = "//div[@class='showrelease_tb']/table/tr[{}]/td[1]/a/@href"
title_str = "\033[1m{}\033[0m"
desc_str = "\033[2m{}\033[0m"
dloading_str = "Download del file {} di {} in corso..."
loading_str = "Caricamento dati in corso..."
prompt_dl = "[0-9] Download: "
prompt_dl_next = "[0-9] Download / [s] Successivo: "
prompt_dl_prev = "[0-9] Download / [p] Precedente: "
prompt_dl_prev_next = "[0-9] Download / [p] Precedente / [s] Successivo: "
search_str = "\033[1mCerca: \033[0m"
next_keys = ("s", "S")
prev_keys = ("p", "P")
all_keys = next_keys + prev_keys
if (os.name != 'nt'):
    no_results_str = "\033[31mLa ricerca non ha prodotto nessun risultato.\033[0m"
    _, columns = os.popen('stty size', 'r').read().split()
else:
    no_results_str = "\033[1mLa ricerca non ha prodotto nessun risultato.\033[0m"
    con_data = os.popen("mode con", "r").read()
    print(con_data)
    sys.exit()



def valid_dl(value, start, stop):
    # Returns true if ALL of the comma-separated numbers input by the
    # user are within the range of the displayed items.
    if (value == -1):
        return False
    for i in [x.strip() for x in value.split(",")]:
        try:
            if not (start <= int(i) < stop):
                return False
        except ValueError:
            return False
    return True


def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


def do_search(search_input, chunks_size):
    # Core function. Searches TNT for the input string, shows the result
    # on screen, and parses the next action.
    try:
        count = 1
        cur_page = 1
        cur_chunk = 0
        results_per_chunk = 0
        page_back = False  # Needed afterwards
        chunk_back = False  # Also needed afterwards
        result_rows = {}  # We use a dict to associate the numbers
                          # shown next to each result with the actual
                          # row number of that result in the table
                          # parsed from TNT.

        while True:
            command = -1  # What the user wants to do after the results
                          # are shown
            prev_count = count
            if (cur_chunk == 0) and not (chunk_back):
                print(loading_str)
                result = requests.post(
                    search_url,
                    data={"cat": "0",
                          "page": cur_page,
                          "srcrel": search_input})
                search_tree = html.fromstring(result.content.decode('utf-8'))

                # Total number of pages we got from our search
                tot_pages = int(search_tree.xpath(tot_pag_addr)[0])

                # Results table
                table = search_tree.xpath(result_table_addr)

                if (len(table) <= 1):
                    # If there are no results
                    print(no_results_str)
                    break

                # We split each page into several "chunks", with
                # chunks_size results each. This is done so that the
                # result screen is easier to read and the user doesn't
                # need to scroll up and down.
                chunks = []
                alt_count = count
                for idx, row in enumerate(table):
                    if (idx == 0):
                        # The first row of the table is the header. We
                        # can ignore it.
                        continue
                    if (((idx - 1) % chunks_size) == 0):
                        chunks.append([])
                    chunks[-1].append(row)
                    result_rows[alt_count] = idx + 1
                    alt_count += 1

            clear_terminal()

            if (page_back):
                # Explanation below
                cur_chunk = len(chunks) - 1

            for row in chunks[cur_chunk]:
                # This below is just for aesthetic reasons.
                title_text = textwrap.TextWrapper(
                    initial_indent="[{:02}]\t".format(count),
                    width=int(columns),
                    subsequent_indent="        ")
                desc_text = textwrap.TextWrapper(
                    initial_indent="        ",
                    width=int(columns),
                    subsequent_indent="        ")
                print(title_text.fill(
                    title_str.format(row.xpath(title_addr)[0].strip())))
                print(desc_text.fill(
                    desc_str.format(row.xpath(desc_addr)[0].strip())))
                print()
                count += 1

            results_per_chunk = len(chunks[cur_chunk])

            if (len(chunks) == 1) and (tot_pages == 1):
                # If there is only one chunk and one page the user can
                # only choose what to download.
                while not valid_dl(command, prev_count, count):
                    command = input(prompt_dl).strip()
            else:
                if (cur_chunk == 0) and (cur_page == 1):
                    # Else, if we are displaying the first chunk on the
                    # first page, the user can either choose what do
                    # download or go to the next chunk.
                    while (not valid_dl(command, prev_count, count)
                           and (command not in next_keys)):
                        command = input(prompt_dl_next).strip()

                elif ((cur_chunk == len(chunks) - 1)
                      and (cur_page == tot_pages)):
                    # If we are displaying the last chunk on the last
                    # page, the user can either choose what to download
                    # or go to the previous chunk.
                    while (not valid_dl(command, prev_count, count)
                           and (command not in prev_keys)):
                        command = input(prompt_dl_prev).strip()
                else:
                    # Else, the user can choose what do wonload or go
                    # to the next or previous chunk.
                    while (not valid_dl(command, prev_count, count)
                           and (command not in all_keys)):
                        command = input(prompt_dl_prev_next).strip()

            page_back = False  # Just bear with me for a moment
            chunk_back = False  # Ditto
            if (command in next_keys):
                # Let's go to the next chunk or page.
                if (cur_chunk == len(chunks) - 1):
                    cur_page += 1
                    cur_chunk = 0
                else:
                    cur_chunk += 1
                clear_terminal()

            elif (command in prev_keys):
                # Let's go to the previous chunk or page.
                if (cur_chunk == 0):
                    cur_page += -1
                    # The flag below is needed so that the function
                    # knows that we went back from page x to page x-1.
                    # This way, we know that after downloading the page
                    # x-1 we must set the current chunk to the last one
                    # of that page.
                    page_back = True
                else:
                    cur_chunk += -1
                    # Similarly, the flag below is needed so that the
                    # function knows it does not have to re-download the
                    # page after we went back from chunk 1 to chunk 0 of
                    # the same page.
                    chunk_back = True
                count += -chunks_size - results_per_chunk
                clear_terminal()

            elif valid_dl(command, prev_count, count):
                # Let's download things.
                dl_list = [int(x.strip()) for x in command.split(",")]
                wait_needed = False  # See below
                clear_terminal()
                for idx, i in enumerate(dl_list):
                    if (wait_needed):
                        # TNT strictly controls every request sent to
                        # their servers. If we request multiple files
                        # within a very short period of time, our IP
                        # address will get banned from TNT. So, after
                        # downloading our first file, we wait for a few
                        # seconds before downloading the next one.
                        sleep(2)
                    print(dloading_str.format(idx + 1, len(dl_list)))
                    dl_url = search_tree.xpath(
                        dl_addr.format(result_rows[i]))[0]
                    result = requests.get(dl_url)
                    disp = result.headers['content-disposition']

                    # We get the filename so that we can save the file
                    # with the correct name.
                    fname = re.findall(
                        "filename=(.+)", disp)[0].split("; ")[0][1:-1]
                    with open(fname, "wb") as outfile:
                        outfile.write(result.content)
                    wait_needed = True

                # We're done. Exit the loop and quit.
                break

    except (KeyboardInterrupt, EOFError) as _:
        # On CTRL+C we do a clean exit
        clear_terminal()
        sys.exit(0)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=progr_desc)
    parser.add_argument("query", metavar="query", type=str, help=query_desc)
    parser.add_argument("-m", "--more", action="store_true", help=more_desc)
    args = parser.parse_args()
    if (args.more):
        chunks_size = 21
    else:
        chunks_size = 7
    do_search(args.query, chunks_size)


if __name__ == "__main__":
    main()
