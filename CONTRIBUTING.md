# To Do

1. Add functionality to **index_crawler.py** so that the json or csv outputs from **convert_index.py** can also be used as inputs
2. Add a listbox or dropdown menu of some kind which can be used to select
the specific index to be queired (right now all indices are queried).
3. If you are a Tkinter veteran, the *ExportForm* class could probably use a
good overhaul, as it was one of my first forays into Tkinter in python.
4.  The *ExportForm* class could use a dynamic listbox resizer, to either resize
the list boxes manually, all-at-once with a form resize, or both.
5. The *ExportForm* class could use an interactive picker or file menu item to
choose the json, csv or db for reading.
The *ExportForm* class needs to be moved to **classes.py** file without breaking
the Tkinter calls in the main function.
6. The **Index** class needs a method to export a BibTex bibliography,
into a separate .bib file and also embedded into the json.

If you have any other ideas or want to contribute in some way please don't 
hesitate to contact me!
