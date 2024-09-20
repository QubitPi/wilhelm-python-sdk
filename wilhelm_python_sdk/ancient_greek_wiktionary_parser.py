# Copyright Jiaqi (Hutao of Emberfire)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import requests

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup


def parse_all_conjugation_tables(url: str) -> dict:
    html = requests.get(url).text

    parsed_html = BeautifulSoup(html)

    tables = parsed_html.body.find_all("div", attrs={"class": "NavFrame"})

    conjugation_tables = {}
    for table in tables:
        tense, conjugation_table = parse_single_conjugation_table(table)
        conjugation_tables[tense] = conjugation_table

    return conjugation_tables


def parse_single_conjugation_table(table):
    tense = table.find("div", attrs={"class": "NavHead"}).text.strip()

    table = table.find('table', attrs={'class': 'grc-conj'})
    table_body = table.find('tbody')

    conjugation_table = []

    # fill out headers first
    multi_row_header = ""
    multi_row_header_fill_remainings = 0
    rows = table_body.find_all('tr')
    for row in rows:
        yaml_table_row = []

        if multi_row_header_fill_remainings > 0:
            multi_row_header_fill_remainings -= 1
            yaml_table_row.append(multi_row_header)

        headers = row.find_all('th')
        for header in headers:
            header_value = header.get_text().strip()

            row_span = header.get('rowspan')
            if row_span:
                yaml_table_row.append(header_value)

                multi_row_header = header_value
                multi_row_header_fill_remainings = int(row_span) - 1

                continue

            col_span = header.get("colspan")
            if col_span is None:
                yaml_table_row.append(header_value)
            else:
                yaml_table_row.extend([header_value] * int(col_span))

        conjugation_table.append(yaml_table_row)

    # now fill out table cells
    for idx, row in enumerate(rows):
        for cell in row.find_all('td'):
            cell_text = cell.get_text().strip()

            col_span = cell.get('colspan')

            if col_span is None:
                conjugation_table[idx].append(cell_text)
            else:
                conjugation_table[idx].extend([cell_text] * int(col_span))

    # post-processing
    # drop "Notes" row
    conjugation_table = conjugation_table[0:len(conjugation_table) - 1]\
        if conjugation_table[len(conjugation_table) - 1][0] == "Notes:" else conjugation_table

    return tense, conjugation_table

    # add double quotes to cell that contains a comma, which is the YAML list element separator
    # for i in range(len(conjugation_table)):
    #     for j in range(len(conjugation_table[i])):
    #         cell = conjugation_table[i][j]
    #         conjugation_table[i][j] = "\"{cell}\"".format(cell=cell) if "," in cell else cell

    # equalize column width
    # widths = [max(map(len, col)) for col in zip(*conjugation_table)]
    # for row in conjugation_table:
    #     print("- [" + ", ".join((val.ljust(width) for val, width in zip(row, widths))) + "]")