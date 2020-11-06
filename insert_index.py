#!/usr/bin/env python3
import argparse
import pandas as pd
import sqlite3 as sqlite
# pd.options.display.max_columns = 10


def insert_db(dbpath, inf, pubkey, delim='\t', version=None, full=None, abbr=None, ed=None, note=None, link=None,
              adjust=0, conflict='fail'):
    # adjust input and add columns
    df = pd.read_csv(inf, sep=delim)
    df.insert(0, 'version', value='')
    df['version'] = version
    df.insert(0, 'pubkey', value='')
    df['pubkey'] = pubkey
    df_dict = df.to_dict(orient='records')

    # create a connection and insert data
    con = sqlite.connect(dbpath)
    c = con.cursor()
    if conflict != 'fail':
        conflict_text = 'OR ' + conflict.upper()
    else:
        conflict_text = ''
    pub_sql = "INSERT {conflict} INTO dnd_pub (pubkey, fullname, abbr, edition, notes, link, page_adjust) " \
              "VALUES (?,?,?,?,?,?,?);".format(conflict=conflict_text)
    c.execute(pub_sql, (pubkey, full, abbr, ed, note, link, adjust))
    pub_rows = c.rowcount
    con.commit()

    index_sql = "INSERT {conflict} INTO dnd_index (pubkey, version, entry, idx, idx_text, page) " \
                "VALUES (:pubkey, :version, :entry, :idx, :idx_text, :page);".format(conflict=conflict_text)
    c.executemany(index_sql, df_dict)
    index_rows = c.rowcount
    con.commit()
    con.close()
    return {'pub_rows': pub_rows, 'index_rows': index_rows}


if __name__ == "__main__":
    # parses script arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Takes text indices from delimited files and generates an index number.')
    parser.add_argument('dbpath', help='path to the sqlite database to insert into.')
    parser.add_argument('idx_file', help='the path to the delimited file created with the add_index script or which '
                                         'shares an identical structure.')
    parser.add_argument('pubkey', help='the text primary key to use for this index.')
    parser.add_argument('-d', '--delimiter', default='\t',
                        help='the delimiter used to separate columns/categories in the input file.')
    parser.add_argument('-v', '--version', help='the version of the index being insert (e.g. original or improved).')
    parser.add_argument('-f', '--full', help='the full name of the text that the index belongs to (e.g. Player''s '
                                             'Handbook)')
    parser.add_argument('-a', '--abbr', help='the abbreviation of the text name of the full text (e.g. PHB, DMG).')
    parser.add_argument('-e', '--edition', help='The edition of the text to be inserted (e.g. 5, 3.5).')
    parser.add_argument('-n', '--note', help='any notes about the text.')
    parser.add_argument('-l', '--link', help='the path to the PDF text on the machine. (e.g. /path/to/phb.pdf)')
    parser.add_argument('-p', '--page_adjust', type=int, default=0,
                        help='if the page of the PDF is not the same as the page of the text, the adjustment number '
                             'to correct for that (e.g. 1, -2). Negative numbers need to be quoted.')
    parser.add_argument('-c', '--conflict', default='fail', choices=['fail', 'update', 'replace'],
                        help='either if there is a record conflict, fail/ignore/replace on the record insert.')
    args = parser.parse_args()

    # args = parser.parse_args([r'/home/wade/Games/D&D/dnd-phb-5e-index/utils/dmdb.sqlite',
    #                           r'/home/wade/Games/D&D/dnd-phb-5e-index/utils/converted_indices/volo.txt', 'vgm5e',
    #                           '-v', 'original', '-f', "Volo's Guide to Monsters", '-a', 'VGM', '-e', '5th', '-l',
    #                           r"/home/wade/Games/D&D/sourcebooks/5e/Volo's Guide to Monsters.pdf", '-p', '1', '-c',
    #                           'replace'])
    # args = parser.parse_args([r'/home/wade/Games/D&D/dnd-phb-5e-index/utils/dmdb.sqlite',
    #                           r'/home/wade/Games/D&D/dnd-phb-5e-index/utils/converted_indices/xanathar.txt', 'xge5e',
    #                           '-v', 'original', '-f', "Xanathar's Guide to Everything", '-a', 'XGE', '-e', '5th', '-l',
    #                           r"/home/wade/Games/D&D/sourcebooks/5e/DnD 5e - Xanathar's Guide to Everything.pdf", '-p',
    #                           '1', '-c', 'replace'])

    rows = insert_db(dbpath=args.dbpath, inf=args.idx_file, pubkey=args.pubkey, delim=args.delimiter,
                     version=args.version, full=args.full, abbr=args.abbr, ed=args.edition, note=args.note,
                     link=args.link, adjust=args.page_adjust, conflict=args.conflict)
    print(rows['pub_rows'], 'rows inserted into table dnd_pub')
    print(rows['index_rows'], 'rows inserted into table dnd_index')
    print('Script finished.')
