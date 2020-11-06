#!/usr/bin/env python3
import argparse
import pandas as pd
import re
import os
import json
# pd.options.display.max_columns = 10


def idx_dict_to_text(idx, delim='.'):
    """This function takes an input dictionary in the form of {1: 'a', 2: 'b'} and returns 'a.b'"""
    idx_keys = sorted(list(idx.keys()))
    idx_values = []
    for key in idx_keys:
        idx_values.append(str(idx[key]))
    idx_string = delim.join(idx_values)
    return idx_string


def dict_to_df(inlist, delim='|'):
    """This function converts the output of get_indent() to a data frame."""
    df = pd.DataFrame(columns=['entry', 'idx', 'idx_text', 'page', 'notes'])
    for d in inlist:
        new_d = dict()
        new_d['entry'] = d['text']
        new_d['idx'] = idx_dict_to_text(d['idx'])
        new_d['idx_text'] = idx_dict_to_text(d['idx_text'], delim=delim)
        new_d['page'] = d['p']
        new_d['notes'] = d['note']
        df = df.append(new_d, ignore_index=True)
    return df


def indent_to_dict(infile):
    """This function takes an input text index and converts it to a dictionary based on initial tab level."""
    lines = []
    last_level = 0
    idx = dict()
    idx_text = dict()
    with open(infile) as f:
        for cnt, line in enumerate(f):
            lines.append({'cnt': cnt, 'line': line.strip(' ').strip('\r').strip('\n')})
    # used to separate a line into its constituent parts using regex
    re_list = [
        r'^(?P<tabs>\t*)',  # 1. name=tabs; capture the tabs at the bol
        r'(?P<text>[^\t]*?)',  # 2. name=text; capture any non-tab value up to next group (lazy)
        r'(?:[.,]\s+)?',  # 3. optional non-capture of either '.' or ',' followed by whitespace
        r'(?P<note>See.+?)?',  # 4. name=note; optional capture text starting with 'See' up to next group (lazy)
        r'(?:[\.,]\s+)?',  # 5. see 2
        r'(?P<p>\d(?:[\d\-,\s])*)?$'  # 6. name=p; optional capture digits sep. by '-' or ', ' for page no. up to eol
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
    return outlist


def multilevel_dict(in_list, level=0):
    current_list = in_list
    sub_list = []
    for i in range(0, len(in_list)):
        level_actual = in_list[i]['tab_no']
        if level == level_actual:
            # recursive call to process any children/subcategories that might exist for this entry
            if i < len(current_list):
                children = multilevel_dict(current_list[i+1:], level + 1)
            else:
                children = None
            dic = {}
            text = in_list[i].get('text')
            note = in_list[i].get('note')
            p = in_list[i].get('p')
            idx = in_list[i].get('idx')
            if text:
                dic['text'] = in_list[i]['text']
            if note:
                dic['note'] = in_list[i]['note']
            if p:
                plist = [x.strip() for x in p.split(',')]
                if len(plist) > 1:
                    dic['p'] = plist
                else:
                    dic['p'] = plist[0]
            if idx:
                dic['idx'] = idx_dict_to_text(in_list[i]['idx'])
            if children:
                dic['children'] = children
            # print(dic)
            sub_list.append(dic)
        elif level > level_actual:
            return sub_list
    return sub_list


if __name__ == "__main__":
    # parses script arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Takes text indices from delimited files and generates an index number.')
    # positional arguments
    parser.add_argument('path', help='Path to the tab delimited file.')
    parser.add_argument('out_file',
                        help='The path to the output file. If the output file is *.json, a multi-level JSON file will '
                             'be written, else a single-level delimited file will be written.')
    # options
    parser.add_argument('-d', '--delim', default='\t',
                        help='The field delimiter to use in the output file.')
    parser.add_argument('-i', '--index_delimiter', default='|',
                        help="The delimiter used to separate categories in the output file's idx_text column in the "
                             "case of a delimited output.")
    args = parser.parse_args()

    mid_list = indent_to_dict(infile=args.path)
    if os.path.splitext(args.out_file)[1] == '.json':
        leveled_list = multilevel_dict(mid_list, level=0)
        with open(args.out_file, 'w', encoding='utf-8') as f:
            json.dump(leveled_list, f, ensure_ascii=False, indent=4)
    else:
        outdf = dict_to_df(inlist=mid_list, delim=args.index_delimiter)
        outdf.to_csv(args.out_file, sep='\t', index=False)


