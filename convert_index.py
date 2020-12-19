#!/usr/bin/env python3
import argparse
import os
import json
from classes import Index


if __name__ == "__main__":
    # parses script arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Takes text indices and converts them to alternative formats. See '
                                                 'README for info on accepted input formats.')
    # positional arguments
    parser.add_argument('path', help='The file path to the input file.')
    parser.add_argument('out_file',
                        help="The path to the output file. The type of output file written will depend on the "
                             "extension of the output file. A 'json' extension will produce a tree style JSON file. A "
                             "'csv' or 'txt' extension will produce a delimited file written with 'delim' option. A "
                             "'db' or 'sqlite' extension will write the results to a sqlite database.")
    # options
    parser.add_argument('-d', '--delim', default='\t',
                        help='The field delimiter to use in the output file.')
    parser.add_argument('-i', '--index_delimiter', default='|',
                        help="The delimiter used to separate categories in the output file's idx_text column in the "
                             "case of a delimited or db output.")
    parser.add_argument('-k', '--pubkey', help='The text primary key to use for this index, in the case of a database '
                                               'output.')
    parser.add_argument('-v', '--version', help="the version of the index (e.g. 'original' or 'improved').")
    parser.add_argument('-l', '--link', help='The path to the PDF text on the machine. (e.g. /path/to/phb.pdf)')
    parser.add_argument('-a', '--abbr', help='The abbreviation of the text name of the full text (e.g. PHB, DMG).')
    parser.add_argument('-p', '--page_adjust', type=int, default=0,
                        help='If the page of the PDF is not the same as the page of the text, the adjustment number '
                             'to correct for that (e.g. 1, -2). Negative numbers need to be quoted.')
    parser.add_argument('-c', '--conflict', default='fail', choices=['fail', 'update', 'replace'],
                        help='If there is a record conflict on a database insert, then fail/ignore/replace on '
                             'the record insert.')

    # bibTeX options
    parser.add_argument('--author', help="The author(s) of the text")
    parser.add_argument('--title', help="The full title of the text the index references (e.g. Player's Handbook)")
    parser.add_argument('--edition', type=float, help="The numerical edition of the text (e.g. 1, 3.5)")
    parser.add_argument('--publisher', help="The name of the publisher of the text.")
    parser.add_argument('--month', help="The month of publication of this edition.")
    parser.add_argument('--year', type=int, help="The year the text of this edition was published.")
    parser.add_argument('--volume', help='The volume number of the text')
    parser.add_argument('--series', help="The name of the series  or set of books the index belongs to")
    parser.add_argument('--address', help="The address of the institution of publisher")
    parser.add_argument('--note', help='Any additional information about the text.')
    parser.add_argument('--isbn', help='The ISBN of the text.')

    args = parser.parse_args()

    my_index = Index(path=args.path, dbpath=args.out_file, delimiter=args.index_delimiter, pubkey=args.pubkey,
                     abbr=args.abbr, link=args.link, adjust=args.page_adjust, conflict=args.conflict,
                     version=args.version, author=args.author, title=args.title, publisher=args.publisher,
                     year=args.year, volume=args.volume, series=args.series, address=args.address, edition=args.edition,
                     month=args.month, note=args.note, isbn=args.isbn)
    my_index.text_to_dict()
    if os.path.splitext(args.out_file)[1] == '.json':
        my_index.dict_to_tree()
        with open(args.out_file, 'w', encoding='utf-8') as file:
            json.dump(my_index.tree_index, file, ensure_ascii=False, indent=4)
    elif os.path.splitext(args.out_file)[1] in ['.db', '.sqlite']:
        rows = my_index.dict_to_db()
        print(rows['pub_rows'], 'rows inserted into table pub')
        print(rows['index_rows'], 'rows inserted into table indices')
    else:
        my_index.dict_to_df()
        my_index.df_index.to_csv(args.out_file, sep=args.delim, index=False)

    print('Script finished.')
