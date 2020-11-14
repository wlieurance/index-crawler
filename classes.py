import pandas as pd
import sqlite3 as sqlite
import re
import os


class Index:
    """
    This class contains methods and functions for creating and storing, and converting text indices in the form of
    the following, where ## are page number integers an the white space preceding the text are tabs :
    Level 1, ##,
        Level 1.1, ##, ##-##, ##
            Level 1.1.1 ##, See note
        Level 1.2
            See also note
    """

    def __init__(self, path, dbpath=None, delimiter='|', pubkey=None, abbr=None, link=None, adjust=0, conflict='fail',
                 version=None, author=None, title=None, publisher=None, year=None, volume=None, series=None,
                 address=None, edition=None, month=None, note=None, isbn=None):
        # index specific attributes
        self.path = path  # the file path to the index text
        self.dbpath = dbpath  # the path to the sqlite database
        self.version = version  # the index version (e.g. 'original', 'improved', etc.)
        self.delimiter = delimiter  # the delimiter to use to separate index text (e.g. level|sublevel|item)
        self.pubkey = pubkey  # the unique key that identifies this entry in the database
        self.abbr = abbr  # an abbreviation or acronym of the text title
        self.link = link  # the path to the pdf of the document
        self.adjust = adjust  # the number of pages to adjust the pdf such that it opens to the proper index page
        self.conflict = conflict  # ['fail', 'update', 'replace'] for db insert

        # BibTex attributes
        self.author = author  # the author(s) of the text
        self.title = title  # the full title of the text the index references (e.g. Player's Handbook)
        self.edition = edition  # the text edition of the text (e.g. '5th', )
        self.publisher = publisher  # the name of the publisher of the text
        self.month = month  # the month of publication of this edition
        self.year = year  # the year the index text of this edition was published
        self.volume = volume  # the volume number of the index text
        self.series = series  # the name of the series  or set of books the index belongs to
        self.address = address  # the address of the institution of publisher
        self.note = note  # any additional info
        self.isbn = isbn  # the ISBN of the index text

        # data storage attributes
        # a pandas data frame that is the index
        self.dict_index = None  # a list of dictionary entries that is the index
        self.df_index = pd.DataFrame(columns=['entry', 'idx', 'idx_text', 'page', 'notes'])
        self.tree_index = None  # an item-children tree like list of dictionary items that is the index

    @staticmethod
    def idx_dict_to_text(idx, delim='.'):
        """This function takes an input dictionary in the form of {1: 'a', 2: 'b'} and returns 'a.b'"""
        idx_keys = sorted(list(idx.keys()))
        idx_values = []
        for key in idx_keys:
            idx_values.append(str(idx[key]))
        idx_string = delim.join(idx_values)
        return idx_string

    def dict_to_df(self):
        """This function converts the output of get_indent() to a data frame."""
        for d in self.dict_index:
            new_d = dict()
            new_d['entry'] = d['text']
            new_d['idx'] = self.idx_dict_to_text(idx=d['idx'])
            new_d['idx_text'] = self.idx_dict_to_text(idx=d['idx_text'], delim=self.delimiter)
            new_d['page'] = d['p']
            new_d['notes'] = d['note']
            self.df_index = self.df_index.append(new_d, ignore_index=True)
        if self.version:
            self.df_index.insert(0, 'version', self.version)
        if self.pubkey:
            self.df_index.insert(0, 'pubkey', self.pubkey)

    def text_to_dict(self):
        """This function takes an input text index and converts it to a dictionary based on initial tab level."""
        lines = []
        last_level = 0
        idx = dict()
        idx_text = dict()
        with open(self.path) as f:
            for cnt, line in enumerate(f):
                lines.append({'cnt': cnt, 'line': line.strip(' ').strip('\r').strip('\n')})
        # used to separate a line into its constituent parts using regex
        re_list = [
            r'^(?P<tabs>\t*)',  # 1. name=tabs; capture the tabs at the bol
            r'(?P<text>[^\t]*?)',  # 2. name=text; capture any non-tab value up to next group (lazy)
            r'(?:[.,]\s+)?',  # 3. optional non-capture of either '.' or ',' followed by whitespace
            r'(?P<note>See.+?)?',  # 4. name=note; optional capture text starting with 'See' up to next group (lazy)
            r'(?:[\.,]\s+)?',  # 5. see 2
            r'(?P<p>\d(?:[\d\-,\s])*)?$'  # 6. name=p; opt. capture digits sep. by '-' or ', ' for page no. up to eol
            ]
        re_string = ''.join(re_list)
        exp = re.compile(re_string)
        outlist = []
        for item in lines:
            raw_text = item['line']
            matches = exp.match(raw_text)
            if matches:
                tabs = matches.group('tabs')
                tab_no = tabs.count('\t')
                text = matches.group('text').strip(' ')
                note = matches.group('note')
                p = matches.group('p')

                # test if line is just a 'See also note'
                if not text and not p and note[:3].lower() == 'see':
                    note_list = [x for x in [outlist[-1]['note'], note] if x]
                    note_string = '; '.join(note_list)
                    outlist[-1]['note'] = note_string
                else:
                    # adjust rolling index
                    current_idx = idx.get(tab_no)
                    idx_text[tab_no] = text
                    # initializes index for this level if not present
                    if not current_idx:
                        current_idx = 1
                        idx[tab_no] = current_idx
                    else:
                        idx[tab_no] = current_idx + 1  # increments the index at the current level

                    # if the indentation level has dropped, remove dictionary keys that no longer apply
                    if tab_no < last_level:
                        keys = list(idx.keys())
                        for key in keys:
                            if key > tab_no:
                                idx.pop(key)
                                idx_text.pop(key)
                    outlist.append({'tab_no': tab_no, 'text': text, 'note': note, 'p': p, 'idx': idx.copy(),
                                    'idx_text': idx_text.copy()})
                    last_level = tab_no
            else:
                print('line', item['cnt'], 'has no regex match.')
                break
        self.dict_index = outlist

    def construct_tree(self, current_list, level=0):
        sub_list = []
        for i, item in enumerate(current_list):
            level_actual = item['tab_no']
            # print("level_actual:", level_actual, "level", level, item['text'])
            if level == level_actual:
                # recursive call to process any children/subcategories that might exist for this entry
                if len(current_list) > 1:
                    children = self.construct_tree(current_list=current_list[i+1:], level=level+1)
                else:
                    children = None
                dic = {}
                text = item.get('text')
                note = item.get('note')
                p = item.get('p')
                idx = item.get('idx')
                if text:
                    dic['text'] = item['text']
                if note:
                    dic['note'] = item['note']
                if p:
                    plist = [x.strip() for x in p.split(',')]
                    if len(plist) > 1:
                        dic['p'] = plist
                    else:
                        dic['p'] = plist[0]
                if idx:
                    dic['idx'] = self.idx_dict_to_text(idx=item['idx'])
                if children:
                    dic['children'] = children
                # print(dic)
                sub_list.append(dic)
            elif level > level_actual:
                print("level > sublevel", sub_list)
                return sub_list
        # print("end of for loop", sub_list)
        return sub_list

    def dict_to_tree(self):
        self.tree_index = self.construct_tree(current_list=self.dict_index, level=0)

    def create_db(self):
        con = sqlite.connect(self.dbpath)
        c = con.cursor()
        sql_list = [
            "CREATE TABLE IF NOT EXISTS indices (pubkey TEXT, version TEXT, entry TEXT, idx TEXT, idx_text TEXT, "
            "page TEXT, notes TEXT, PRIMARY KEY (pubkey, version, idx));",
            "CREATE TABLE IF NOT EXISTS pub (pubkey TEXT PRIMARY KEY, author TEXT, title TEXT, abbr TEXT, edition TEXT,"
            " publisher TEXT, month TEXT, year INTEGER, volume TEXT, series TEXT, address TEXT, note TEXT, isbn TEXT,"
            " link TEXT, adjust INTEGER DEFAULT (0));"
        ]
        for sql in sql_list:
            # print(sql)
            c.execute(sql)
        con.commit()
        con.close()

    def dict_to_db(self):
        assert self.dbpath is not None, 'db creation requires dbpath'
        assert self.pubkey is not None, 'db creation requires pubkey'
        assert self.version is not None, 'db creation requires version'
        if not os.path.exists(self.dbpath):
            db_exists = False
        else:
            db_exists = True  # for future reference
        self.create_db()
        if self.dict_index is None:
            self.text_to_dict()
        if self.df_index.empty:
            self.dict_to_df()
        df_dict = self.df_index.to_dict(orient='records')

        # create a connection and insert data
        con = sqlite.connect(self.dbpath)
        c = con.cursor()
        if self.conflict != 'fail':
            conflict_text = 'OR ' + self.conflict.upper()
        else:
            conflict_text = ''
        pub_sql = "INSERT {conflict} INTO pub (pubkey, author, title, abbr, edition, publisher, month, year, volume, " \
                  "series, address, note, isbn, link, adjust) " \
                  "VALUES (:pubkey, :author, :title, :abbr, :edition, :publisher, :month, :year, :volume, :series, " \
                  ":address, :note, :isbn, :link, :adjust);".format(conflict=conflict_text)
        c.execute(pub_sql, {'pubkey': self.pubkey, 'author': self.author, 'title': self.title, 'abbr': self.abbr,
                            'edition': self.edition, 'publisher': self.publisher, 'month': self.month,
                            'year': self.year, 'volume': self.volume, 'series': self.series, 'address': self.address,
                            'note': self.note, 'isbn': self.isbn, 'link': self.link, 'adjust': self.adjust})
        pub_rows = c.rowcount
        con.commit()
        index_sql = "INSERT {conflict} INTO indices (pubkey, version, entry, idx, idx_text, page, notes) " \
                    "VALUES (:pubkey, :version, :entry, :idx, :idx_text, :page, :notes);".format(conflict=conflict_text)
        c.executemany(index_sql, df_dict)
        index_rows = c.rowcount
        con.commit()
        con.close()
        return {'pub_rows': pub_rows, 'index_rows': index_rows}



