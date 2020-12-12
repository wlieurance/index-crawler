# Index Crawler

A set of python scripts to convert common text index styles into other formats
(csv, json, sqlite).  Currently the only supported index format is the tab
indented sub-headings, with comma separated pages numbers e.g.

```
Level 1, ##,
	Level 1.1, ##, ##-##, ##
		Level 1.1.1 ##, See note
	Level 1.2
		See also note
```

## Getting Started

Clone into a local directory and make sure you have the prerequisites installed.

`python3 ./convert_index.py -h`  to see all conversion arguments and options.

`python3 ./index_crawler.py -d "path/to/db.sqlite"`  to open up the index search
window. A default location of "script_dir/indices.sqlite" is assumed when no
path is given.  The database provided should be produced from the
*convert_index.py* script (or *Index* class).


### Prerequisites

Install dependencies via the requirements.txt file

`pip install -r requirements.txt`

In addition, you will need to have **Tkinter**  installed on your system.
Tk and Tkinter are may already be installed on your system as part of a standard
python install, but check [tkdocs](https://tkdocs.com/tutorial/install.html) for
specific info on how to get Tkinter on your system if importing fails.


## Contributing

Please read CONTRIBUTING.md for more info.

## Versioning

## Authors

* **Wade Lieurance** - *Initial work* - [wlieurance](https://github.com/wlieurance)

## License

This project is licensed under the GNU GPL v3 License - see the [LICENSE.md](LICENSE.md) file for details.
