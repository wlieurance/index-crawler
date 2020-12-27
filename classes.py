# Index
import pandas as pd
import sqlite3 as sqlite
import re
import os

# ExportForm
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import subprocess
import json


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
                if not text and not note and not p:
                    continue
                elif not text and not note:
                    p_list = [x for x in [outlist[-1]['p'], note] if x]
                    p_string = '; '.join(p_list)
                    outlist[-1]['p'] = p_string
                elif not text and note[:3].lower() == 'see':
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


class ExportForm:
    def __init__(self, master, conn, scrptdir):
        self.master = master
        # self.cframe = Frame(self.master)
        # self.cframe.grid(row=0, column=0, sticky='nsew')

        self.valuePub = []
        self.valueIndex = []
        self.valueEntry = []
        self.valuePages = []
        self.sv_pub = StringVar()
        self.sv_idx = StringVar()
        self.sv_ent = StringVar()

        with open(os.path.join(scrptdir, 'pdf_options.json'), 'r') as f:
            pdf_options = json.load(f)
        self.pdf = None
        for i in pdf_options:
            if os.path.isfile(i['readerpath']):
                self.pdf = i
            else:
                break
        print('pdf options:', self.pdf)

        # self.path_to_reader = os.path.abspath(r'/usr/bin/evince')

        self.style = Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#ccc", width=20)

        # list boxes
        self.lblPub = tk.Label(self.master, text='Indices', fg='blue')
        self.lblPub.grid(row=0, column=0, sticky='w')
        self.txtPub = tk.Entry(self.master, textvariable=self.sv_pub, width=40)
        self.txtPub.grid(row=1, column=0, sticky='ew')
        # self.txtPub.config(fg='gray')
        # self.txtPub.insert(0, "Search indices...")

        self.lblIndex = tk.Label(self.master, text='Entry paths', fg='blue')
        self.lblIndex.grid(row=0, column=2, sticky='w')
        self.txtIndex = tk.Entry(self.master, textvariable=self.sv_idx, width=40)
        self.txtIndex.grid(row=1, column=2, sticky='ew')
        # self.txtIndex.config(fg='gray')
        # self.txtIndex.insert(0, "Search index paths...")

        self.lblEntry = tk.Label(self.master, text='Entries', fg='blue')
        self.lblEntry.grid(row=0, column=4, sticky='w')
        self.txtEntry = tk.Entry(self.master, textvariable=self.sv_ent, width=30)
        self.txtEntry.grid(row=1, column=4, sticky='ew')
        # self.txtEntry.config(fg='gray')
        # self.txtEntry.insert(0, "Search entries...")

        self.lblPages = tk.Label(self.master, text='Select page', fg='blue')
        self.lblPages.grid(row=1, column=6, sticky='w')

        self.lstPub = Listbox(self.master, selectmode=EXTENDED, exportselection=0, width=40)
        self.lstPub.grid(row=2, column=0, sticky='nsew')

        self.lstIndex = Listbox(self.master, selectmode=EXTENDED, exportselection=0, width=40)
        self.lstIndex.grid(row=2, column=2, sticky='nsew')

        self.lstEntry = Listbox(self.master, selectmode=EXTENDED, exportselection=0, width=30)
        self.lstEntry.grid(row=2, column=4, sticky='nsew')

        self.lstPages = Listbox(self.master, selectmode=SINGLE, exportselection=0, width=20)
        self.lstPages.grid(row=2, column=6, sticky='nsew')

        # buttons
        self.btnSelectAll_pub = Button(self.master, width=10, text='Select All', style="TButton",
                                           command=self.selectall_pub)
        self.btnSelectAll_pub.grid(row=4, column=0, sticky='w')

        self.btnSelectAll_idx = Button(self.master, width=10, text='Select All', style="TButton",
                                           command=self.selectall_idx)
        self.btnSelectAll_idx.grid(row=4, column=2, sticky='w')

        self.btnSelectAll_entry = Button(self.master, width=10, text='Select All', style="TButton",
                                             command=self.selectall_ent)
        self.btnSelectAll_entry.grid(row=4, column=4, sticky='w')

        self.btnClearAll_pub = Button(self.master, width=10, text='Clear All', style="TButton",
                                          command=self.clearall_pub)
        self.btnClearAll_pub.grid(row=4, column=0, sticky='e')

        self.btnClearAll_idx = Button(self.master, width=10, text='Clear All', style="TButton",
                                          command=self.clearall_idx)
        self.btnClearAll_idx.grid(row=4, column=2, sticky='e')

        self.btnClearAll_entry = Button(self.master, width=10, text='Clear All', style="TButton",
                                            command=self.clearall_ent)
        self.btnClearAll_entry.grid(row=4, column=4, sticky='e')

        # self.btnGrab = Button(self.master, width=20, text='Export', style="TButton", command=self.grab)
        # self.btnGrab.grid(row=3, column=4, sticky='w')

        # scrollbars
        # Publication listbox
        self.scrollbar_pub_v = Scrollbar(self.master, orient=VERTICAL)
        self.lstPub.config(yscrollcommand=self.scrollbar_pub_v.set)
        self.scrollbar_pub_v.config(command=self.lstPub.yview)
        self.scrollbar_pub_v.grid(row=2, column=1, sticky='ns')
        self.scrollbar_pub_h = Scrollbar(self.master, orient=HORIZONTAL)
        self.lstIndex.config(xscrollcommand=self.scrollbar_pub_h.set)
        self.scrollbar_pub_h.config(command=self.lstPub.xview)
        self.scrollbar_pub_h.grid(row=3, column=0, sticky='ew')

        # Index listbox
        self.scrollbar_idx_v = Scrollbar(self.master, orient=VERTICAL)
        self.lstIndex.config(yscrollcommand=self.scrollbar_idx_v.set)
        self.scrollbar_idx_v.config(command=self.lstIndex.yview)
        self.scrollbar_idx_v.grid(row=2, column=3, sticky='ns')
        self.scrollbar_idx_h = Scrollbar(self.master, orient=HORIZONTAL)
        self.lstIndex.config(xscrollcommand=self.scrollbar_idx_h.set)
        self.scrollbar_idx_h.config(command=self.lstIndex.xview)
        self.scrollbar_idx_h.grid(row=3, column=2, sticky='ew')

        # Entry listbox
        self.scrollbar_ent_v = Scrollbar(self.master, orient=VERTICAL)
        self.lstEntry.config(yscrollcommand=self.scrollbar_ent_v.set)
        self.scrollbar_ent_v.config(command=self.lstEntry.yview)
        self.scrollbar_ent_v.grid(row=2, column=5, sticky='ns')
        self.scrollbar_ent_h = Scrollbar(self.master, orient=HORIZONTAL)
        self.lstEntry.config(xscrollcommand=self.scrollbar_ent_h.set)
        self.scrollbar_ent_h.config(command=self.lstEntry.xview)
        self.scrollbar_ent_h.grid(row=3, column=4, sticky='ew')

        # Pages listbox
        self.scrollbar_pgs_v = Scrollbar(self.master, orient=VERTICAL)
        self.lstPages.config(yscrollcommand=self.scrollbar_pgs_v.set)
        self.scrollbar_pgs_v.config(command=self.lstPages.yview)
        self.scrollbar_pgs_v.grid(row=2, column=7, sticky='ns')
        self.scrollbar_pgs_h = Scrollbar(self.master, orient=HORIZONTAL)
        self.lstPages.config(xscrollcommand=self.scrollbar_pgs_h.set)
        self.scrollbar_pgs_h.config(command=self.lstPages.xview)
        self.scrollbar_pgs_h.grid(row=3, column=6, sticky='ew')

        # set weights for window resize
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=0)
        self.master.grid_columnconfigure(2, weight=4)
        self.master.grid_columnconfigure(3, weight=0)
        self.master.grid_columnconfigure(4, weight=4)
        self.master.grid_columnconfigure(5, weight=0)
        self.master.grid_columnconfigure(6, weight=1)
        self.master.grid_columnconfigure(7, weight=0)
        self.master.grid_rowconfigure(0, weight=0)
        self.master.grid_rowconfigure(1, weight=0)
        self.master.grid_rowconfigure(2, weight=4)
        self.master.grid_rowconfigure(3, weight=0)
        self.master.grid_rowconfigure(4, weight=0)

        init_sql = '\n'.join((
            "SELECT b.title || ' (' || a.version || ')' ",
            "  FROM indices as a ",
            " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
            " WHERE a.page IS NOT NULL ",
            " GROUP BY b.title, a.version ",
            " ORDER BY b.title, a.version;"))
        pub_result = conn.execute(init_sql)
        for row in pub_result:
            self.lstPub.insert(END, row[0])

        # self.btnSelectAll_pub.invoke()
        # idx_result = conn.execute("SELECT idx_text FROM indices WHERE page IS NOT NULL "
        #                           "GROUP BY idx_text, idx ORDER BY idx_text, idx;")
        # for row in idx_result:
        #     # print(row)
        #     self.lstIndex.insert(END, row[0])

        # functions to define what happens on listbox select
        def onselect_Pub(evt):
            self.lstIndex.delete(0, END)
            self.lstEntry.delete(0, END)
            self.lstPages.delete(0, END)
            w = evt.widget
            c = w.curselection()
            value = []
            li = len(c)
            for i in range(0, li):
                value.append(w.get(c[i]))
            # print(value)
            self.valuePub = value
            s = '\n'.join((
                "SELECT idx_text FROM indices AS a ",
                " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                " WHERE b.title || ' (' || a.version || ')' IN ({!s}) ",
                "   AND a.page IS NOT NULL ",
                " GROUP BY a.idx_text ",
                " ORDER BY lower(a.idx_text);"))\
                .format(','.join('?' * len(self.valuePub)))
            result = conn.execute(s, self.valuePub)
            count = 0
            for row in result:
                count += 1
                self.lstIndex.insert(END, row[0])
            if count == 1:
                self.lstIndex.selection_set(0)
                self.lstIndex.event_generate("<<ListboxSelect>>")

        def onselect_Index(evt):
            self.lstEntry.delete(0, END)
            self.lstPages.delete(0, END)
            w = evt.widget
            c = w.curselection()
            value = []
            li = len(c)
            for i in range(0, li):
                value.append(w.get(c[i]))
            # print(value)
            self.valueIndex = value
            s = '\n'.join((
                "SELECT a.entry, a.notes ",
                "  FROM indices AS a ",
                " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                " WHERE a.idx_text IN ({!s}) ",
                "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                "   AND a.page IS NOT NULL ",
                " GROUP BY a.entry ORDER BY a.idx;"))\
                .format(','.join('?' * len(self.valueIndex)), ','.join('?' * len(self.valuePub)))
            result = conn.execute(s, self.valueIndex + self.valuePub)
            count = 0
            for row in result:
                count += 1
                if not row[1]:
                    self.lstEntry.insert(END, row[0])
                else:
                    self.lstEntry.insert(END, ''.join((row[0], ' | (', row[1], ')')))
            if count == 1:
                self.lstEntry.selection_set(0)
                self.lstEntry.event_generate("<<ListboxSelect>>")

        def onselect_Entry(evt):
            self.lstPages.delete(0, END)
            w = evt.widget
            c = w.curselection()
            value = []
            li = len(c)
            for i in range(0, li):
                value.append(w.get(c[i]).split('|')[0].strip())
            # print(value)
            self.valueEntry = value
            s = '\n'.join((
                "SELECT a.pubkey, a.page ",
                "  FROM indices AS a ",
                " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                " WHERE a.entry IN ({!s}) ",
                "   AND a.idx_text IN ({!s}) ",
                "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                "   AND a.page IS NOT NULL ",
                " GROUP BY a.pubkey, a.page ",
                " ORDER BY a.pubkey, a.page;"))\
                .format(','.join('?' * len(self.valueEntry)), ','.join('?' * len(self.valueIndex)),
                        ','.join('?' * len(self.valuePub)))
            result = conn.execute(s, self.valueEntry + self.valueIndex + self.valuePub)
            count = 0
            for row in result:
                pages = [x.strip() for x in row[1].split(',')]
                for p in pages:
                    count += 1
                    self.lstPages.insert(END, ' | '.join((row[0], p)))
            # if count == 1:
            #     self.lstPages.selection_set(0)
            #     self.lstPages.event_generate("<<ListboxSelect>>")

        def onselect_Pages(evt):
            w = evt.widget
            c = w.curselection()
            value = []
            li = len(c)
            for i in range(0, li):
                value.append(tuple(w.get(c[i]).split(' | ')))
            # print(value)
            self.valuePages = value
            for i in self.valuePages:
                pg = int(i[1].split('-')[0])
                rec = conn.execute("SELECT link, adjust FROM pub WHERE pubkey = ?;", (i[0],)).fetchone()
                pdf_path = rec[0]
                pg += int(rec[1])
            if self.pdf and pdf_path:
                pinput = [self.pdf['readerpath']]
                if self.pdf['options'] is not None:
                    pinput += [x for x in self.pdf['options'] if x is not None]
                pinput += [self.pdf['page'].format(str(pg))] + [os.path.abspath(pdf_path)]
                print(pinput)
                process = subprocess.Popen(pinput, shell=False,  stdout=subprocess.PIPE)

        # callback actions if text boxes have been altered
        def callback_pub(sv):
            self.lstPub.delete(0, END)
            # print(cb, type(cb))
            self.lstIndex.delete(0, END)
            self.lstEntry.delete(0, END)
            self.lstPages.delete(0, END)
            cb = sv.get()
            if cb:
                sql = '\n'.join((
                    "SELECT b.title || ' (' || a.version || ')' ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    " GROUP BY b.title, a.version ",
                    "HAVING lower(b.title || ' (' || a.version || ')') LIKE '%{!s}%' ",
                    " ORDER BY b.title, a.version;"))\
                    .format(cb)
                result = conn.execute(sql)
            else:
                sql = '\n'.join((
                    "SELECT b.title || ' (' || a.version || ')' ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    " GROUP BY b.title, a.version ",
                    " ORDER BY b.title, a.version;"))
                result = conn.execute(sql)
            for row in result:
                self.lstPub.insert(END, row[0])

        def callback_idx(sv):
            self.lstIndex.delete(0, END)
            # print(cb, type(cb))
            self.lstEntry.delete(0, END)
            self.lstPages.delete(0, END)
            cb = sv.get()
            if cb:
                sql = '\n'.join((
                    "SELECT idx_text ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                    " GROUP BY a.idx_text, a.idx ",
                    "HAVING idx_text LIKE '%{!s}%' ",
                    "ORDER BY lower(idx_text);"))\
                    .format(','.join('?' * len(self.valuePub)), cb)
                result = conn.execute(sql, self.valuePub)
            else:
                sql = '\n'.join((
                    "SELECT idx_text ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                    " GROUP BY a.idx_text, a.idx ",
                    " ORDER BY lower(idx_text);"))\
                    .format(','.join('?' * len(self.valuePub)))
                result = conn.execute(sql, self.valuePub)
            for row in result:
                self.lstIndex.insert(END, row[0])

        def callback_ent(sv):
            self.lstEntry.delete(0, END)
            # print(cb, type(cb))
            self.lstPages.delete(0, END)
            cb = sv.get()
            if cb:
                sql = '\n'.join((
                    "SELECT a.entry, a.notes ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                    "   AND a.idx_text IN ({!s}) ",
                    " GROUP BY a.entry ",
                    "HAVING entry LIKE '%{!s}%' ",
                    "ORDER BY idx;"))\
                    .format(','.join('?' * len(self.valuePub)), ','.join('?' * len(self.valueIndex)), cb)
                result = conn.execute(sql, self.valuePub, self.valueIndex)
            else:
                sql = '\n'.join((
                    "SELECT a.entry, a.notes ",
                    "  FROM indices as a ",
                    " INNER JOIN pub AS b ON a.pubkey = b.pubkey ",
                    " WHERE a.page IS NOT NULL ",
                    "   AND b.title || ' (' || a.version || ')' IN ({!s}) ",
                    "   AND a.idx_text IN ({!s}) ",
                    " GROUP BY a.entry ",
                    "ORDER BY idx;"))\
                    .format(','.join('?' * len(self.valuePub)), ','.join('?' * len(self.valueIndex)))
                result = conn.execute(sql, self.valuePub, self.valueIndex)
            for row in result:
                if not row[1]:
                    self.lstEntry.insert(END, row[0])
                else:
                    self.lstEntry.insert(END, ''.join((row[0], ' | (', row[1], ')')))

        # event functions for textbox entry mouse clicks
        def onclick_txtPub(evt):
            color = self.txtPub.cget('fg')
            if color == 'gray':
                self.txtPub.delete(0, END)
                self.txtPub.config(fg='black')

        def onclick_txtIndex(evt):
            color = self.txtIndex.cget('fg')
            if color == 'gray':
                self.txtIndex.delete(0, END)
                self.txtIndex.config(fg='black')

        def onclick_txtEntry(evt):
            color = self.txtEntry.cget('fg')
            if color == 'gray':
                self.txtEntry.delete(0, END)
                self.txtEntry.config(fg='black')

        self.txtPub.bind('<Button>', onclick_txtPub)
        self.txtIndex.bind('<Button>', onclick_txtIndex)
        self.txtEntry.bind('<Button>', onclick_txtEntry)
        self.lstPub.bind('<<ListboxSelect>>', onselect_Pub)
        self.lstIndex.bind('<<ListboxSelect>>', onselect_Index)
        self.lstEntry.bind('<<ListboxSelect>>', onselect_Entry)
        self.lstPages.bind('<<ListboxSelect>>', onselect_Pages)
        self.sv_pub.trace("w", lambda name, index, mode, sv=self.sv_pub: callback_pub(sv))
        self.sv_idx.trace("w", lambda name, index, mode, sv=self.sv_idx: callback_idx(sv))
        self.sv_ent.trace("w", lambda name, index, mode, sv=self.sv_ent: callback_ent(sv))

    def selectall_pub(self):
        self.lstPub.select_set(0, END)
        self.lstPub.event_generate("<<ListboxSelect>>")

    def selectall_idx(self):
        self.lstIndex.select_set(0, END)
        self.lstIndex.event_generate("<<ListboxSelect>>")

    def selectall_ent(self):
        self.lstEntry.select_set(0, END)
        self.lstEntry.event_generate("<<ListboxSelect>>")

    def clearall_pub(self):
        self.lstPub.selection_clear(0, END)
        self.lstPub.event_generate("<<ListboxSelect>>")

    def clearall_idx(self):
        self.lstIndex.selection_clear(0, END)
        self.lstIndex.event_generate("<<ListboxSelect>>")

    def clearall_ent(self):
        self.lstEntry.selection_clear(0, END)
        self.lstEntry.event_generate("<<ListboxSelect>>")

    # def grab(self):
    #     w = self.lstPages
    #     c = w.curselection()
    #     value = []
    #     li = len(c)
    #     for i in range(0, li):
    #         value.append(w.get(c[i]))
    #     print(value)
