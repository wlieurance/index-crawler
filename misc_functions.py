def get_pipe(infile, delim='\t', col_names=False):
    if col_names:
        header = 0
    else:
        header = None
    df = pd.read_csv(infile, sep=delim, header=header, names=['idx_text', 'page'])
    return df


# These functions is deprecated as input indices shouldn't come in a categorical pipe format anymore.
# function is retained for later reference.
def create_pipe_idx(dfo, delim='|'):
    """This function parses the idx_text and creates a unique numeric style text index for each entry. idx_text
    should be passed into the function in the format of category1|category2|entry in the case of a pipe delimiter."""
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