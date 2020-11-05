#!/usr/bin/env python3
import argparse
import pandas as pd
import re
# pd.options.display.max_columns = 10


def get_pipe(infile, delim='\t', col_names=False):
    if col_names:
        header = 0
    else:
        header = None
    df = pd.read_csv(infile, sep=delim, header=header, names=['idx_text', 'page'])
    return df


def get_indent(infile, delim='\t'):
    """This function takes an input file and converts it to a dictionary based on indenting/delimiting character.
    It assumes that the character used to indent sub-levels of a category is the same character used to separate the
    text and page number on a line."""
    lines = []
    re_string = r'^({s}*)([^{s}]+)({s})(\d+)$'.format(s=delim)
    exp = re.compile(re_string)  # used to separate a line into its constituent parts
    with open(infile) as f:
        for cnt, line in enumerate(f):
            lines.append({'cnt': cnt, 'line': line})
    post = []
    idx = dict()
    idx_text = dict()
    last_level = 0
    # runs through every line in the file and assigns variables based on its indentation and content
    for line in lines:
        l = line.get('line')
        r = exp.match(l)
        if r:
            tabs = r.group(1)
            tab_no = tabs.count('\t')
            text = r.group(2).strip(' ')
            page = int(r.group(4))
            current_idx = idx.get(tab_no)
            idx_text[tab_no] = text
            if not current_idx:
                current_idx = 1  # initializes index for this level if not present
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
            post.append({'level': tab_no, 'text': text, 'page': page, 'idx': idx.copy(), 'idx_text': idx_text.copy()})
            last_level = tab_no
        else:
            cnt = line.get('cnt')
            print('line', cnt, 'has no regex match.')  # this indicates that your input file probably needs correcting
            break
    return post


def create_pipe_idx(dfo, delim='|'):
    """This function parses the idx_text and creates a unique numeric style text index for each entry."""
    # assign an index column, create a split according to idx_text delimiter, and calculate split length for processing
    dfo = dfo.assign(idx=None)\
        .assign(split=lambda x: x.idx_text.str.split(delim, expand=False))\
        .assign(entry=lambda x: x.split.str[-1])\
        .assign(length=lambda x: x.split.str.len())
    df = dfo  # keep original data frame for debugging

    # loop through the split idx_text length and assign a ".#" according to sub-category
    for i in range(0, 100):  # could use while loop, but the for loop used instead for safety
        # print(i)
        # iterate over the split string, recombining at point i by delimiter
        df = df.assign(pre=lambda x: x.split.str[0: i+1].str.join(delim))\
            .assign(post=lambda x: x.split.str[i+1:len(x.split)].str.join(delim))
        # limit results to items within the subcategory
        dff = df.query('length >= {n}'.format(n=i+1)).reset_index()
        # group by current pre, create a new split for everything before the last split in 'pre'
        # and do a rank / row_number according to this secondary group, ordered by page then pre
        dfg = dff[['pre', 'page']].groupby(by=['pre']).min().sort_values(by=['page']).reset_index() \
            .assign(split=lambda x: x.pre.str.split(delim, expand=False)) \
            .assign(grp=lambda x: x.split.str[0: -1].str.join(delim))
        # create a new idx for the group/subgroup
        dfg['idx_new'] = dfg.sort_values(by=['grp', 'page', 'pre']).groupby(by=['grp'])['page']\
            .rank(method='first', ascending=True).astype(int).astype(str)
        dfg = dfg.sort_values(by=['grp', 'idx_new']).drop(['page'], axis=1)
        if dfg.empty:
            break
        # pull new idx back into main table and append to main idx
        dfj = pd.merge(df, dfg.drop(['split'], axis=1), how='left', on=['pre'])\
            .assign(idx=lambda y: y.apply(lambda x: '.'.join(x[['idx', 'idx_new']].dropna()), axis=1))
        df = dfj.drop(['idx_new'], axis=1)
    df = df.reset_index()
    df_final = df[['entry', 'idx', 'idx_text', 'page']]
    return df_final


def convert_indent_dict(idict, delim='|'):
    """This function converts the output of get_indent() to a data frame."""
    df = pd.DataFrame(columns=['entry', 'idx', 'idx_text', 'page'])
    for d in idict:
        new_d = dict()
        new_d['entry'] = d['text']
        idx_keys = sorted(list(d['idx'].keys()))
        idx_values = []
        idx_text_values = []
        for key in idx_keys:
            idx_values.append(str(d['idx'][key]))
            idx_text_values.append(d['idx_text'][key])
        idx_string = '.'.join(idx_values)
        idx_text = delim.join(idx_text_values)
        new_d['idx'] = idx_string
        new_d['idx_text'] = idx_text
        new_d['page'] = d['page']
        df = df.append(new_d, ignore_index=True)
    return df


if __name__ == "__main__":
    # parses script arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Takes text indices from delimited files and generates an index number.')
    # positional arguments
    parser.add_argument('path', help='path to the tab delimited file')
    parser.add_argument('type',
                        help="Either 'delim' for a single line per entry delimited by a character in "
                             "the first column (e.g. of main|sub1|sub2 {delimiter} page_no) or "
                             "'indent' for files where subcategories are indented by tabs or another "
                             "delimiter from the main category.")
    parser.add_argument('out_file',
                        help='the path to the tab delimited output file.')
    # options
    parser.add_argument('-c', '--colnames', action='store_true',
                        help='input file has column names as first row.')
    parser.add_argument('-d', '--delimiter', default='\t',
                        help='the delimiter used to separate columns/categories in the input file.')
    parser.add_argument('-t', '--index_delimiter', default='|',
                        help="the delimiter used to separate categories in the input file's first column in the case "
                             "of a 'delim' input.")
    args = parser.parse_args()

    if args.type == 'pipe':
        indf = get_pipe(infile=args.path, delim=args.delimiter, col_names=args.colnames)
        outdf = create_pipe_idx(dfo=indf, delim=args.index_delimiter)
    elif args.type == 'indent':
        indict = get_indent(infile=args.path, delim=args.delimiter)
        outdf = convert_indent_dict(idict=indict, delim=args.index_delimiter)
    outdf.to_csv(args.out_file, sep='\t', index=False)


