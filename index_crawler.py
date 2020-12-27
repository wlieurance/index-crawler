#!/usr/bin/env python3
import tkinter
import os
import sqlite3 as sqlite
import argparse

# local
from classes import ExportForm

if __name__ == "__main__":
    # parses script arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Creates a Tkinter window to search indices in a database format.')
    parser.add_argument('-d', '--dbpath', help='The file path to the database file created with convert_index.py '
                        'or via the "Index" class in classes.py')
    args = parser.parse_args()

    try:
        scrptdir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        scrptdir = os.getcwd()
    if args.dbpath:
        dbpath = args.dbpath
    else:
        dbpath = os.path.join(scrptdir, "indices.sqlite")
        print("DB not provided. Using default path:", dbpath)
    assert os.path.exists(dbpath), ' '.join((dbpath, 'does not exist.'))
    conn = sqlite.connect(dbpath)
    root = tkinter.Tk()
    root.title("Index Crawler")
    icon = tkinter.PhotoImage(file='icon.png')
    root.iconphoto(False, icon)
    mf = ExportForm(root, conn, scrptdir)
    root.mainloop()
    conn.close()

