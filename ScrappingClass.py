import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from pprint import pprint
from anytree import AnyNode, RenderTree, AsciiStyle, Node, PreOrderIter, AbstractStyle
# print = pprint
from collections import namedtuple
from datetime import datetime as dt
from time import perf_counter


def find_elem_by_xpath(elem, xpath):
    lstElem = []
    elems = elem.find_elements(By.XPATH, xpath)
    for elem in elems:
        dict_attr = {}
        dict_attr['elem'] = elem
        dict_attr['tag_name'] = elem.tag_name
        dict_attr['text'] = elem.text
        # dict_attr['parent'] = elem.parent
        dict_attr['accessible_name'] = elem.accessible_name
        dict_attr['aria_role'] = elem.aria_role
        lstElem.append(dict_attr)
    return lstElem


def filter_elems_list(elems, attr, value):
    elems = list(filter(lambda e: e[attr] == value, elems))
    if len(elems) == 1:
        return elems[0]
    elif len(elems) == 0:
        return None
    else:
        return elems


def obtain_elems_list_attr(elems, attr='text'):
    return [e[attr] for e in elems if attr in e]


def scrap_text_row_name(row_elem, class_tag):
    # get cells within the row, and text of the cells within the row
    cell_elems = find_elem_by_xpath(row_elem, rf'.//div[starts-with(@class, "{class_tag}")]')
    return obtain_elems_list_attr(cell_elems, 'text')


class YFscapper:
    CLASSTAG_HEADING = 'D(tbhg)'
    CLASSTAG_HEADING_NAME = 'D(ib)'
    CLASSTAG_CELL = 'Ta(c)'
    CLASSTAG_ROWS = 'rw-expnded'
    CLASSTAG_ROW_NAME = 'D(tbc)'

    DELIMITER = 'Level_'
    ID_LEVEL = 'level'
    ID_NODES = 'node'
    ID_NUMBERING = 'Sequence'
    STYLE_LEN = 2
    STYLE = [r'=>', r'=>', r'=>']

    def __init__(self, code='AAPL', statement_selectors=('financials', 'balance-sheet', 'cash-flow')):
        self.code = code
        self.statement_selectors = statement_selectors
        self.index_name = dict()
        self.index_tree = dict()
        self.raw_statements = dict()
        self.statements = dict()
        self.driver = None

    def get_statements(self, verbose=True):
        self.driver = webdriver.Chrome()
        for e in self.statement_selectors:
            start = perf_counter()
            if verbose:
                print(f'Obtaining data for {e} of {self.code}.')
            self.index_name[e], self.raw_statements[e] = self._get_statement_table(e)
            if verbose:
                final = (perf_counter() - start)
                print(f'Obtained data in {final:.1f} secs.')
        self.driver.quit()

    def tidy_statements(self):
        for k, df in self.raw_statements.items():
            index_df, body_df = self._tidy_statements(df)
            tree, index_df = self._tree_from_index(self.index_name[k], index_df)
            self.statements[k] = pd.concat([index_df, body_df], axis=1)
            self.index_tree[k] = tree

    def export_statements(self, path=None):
        actual_path = path if path else f'statements_{self.code}_{dt.now().strftime("%y%m%d")}.xlsx'
        # print(actual_path)
        with pd.ExcelWriter(actual_path) as xwsr:
            _ = [v.to_excel(xwsr, k) for k, v in self.statements.items()]

    def _get_statement_table(self, statement):
        self.driver.get(rf"https://finance.yahoo.com/quote/{self.code}/{statement}", )
        main = self.driver.find_element(By.XPATH, "//body")

        # click expand all button
        buttons = find_elem_by_xpath(main, ".//button")
        expand_btn = filter_elems_list(buttons, 'text', 'Expand All')
        expand_btn['elem'].click()

        # get tbhg rows (table heading)
        tb_hg_rows = find_elem_by_xpath(main, rf'.//div[starts-with(@class, "{self.CLASSTAG_HEADING}")]')
        tb_hg_row = filter_elems_list(tb_hg_rows, 'aria_role', 'none')

        index_name = scrap_text_row_name(tb_hg_row['elem'], self.CLASSTAG_HEADING_NAME)[0]
        columns = scrap_text_row_name(tb_hg_row['elem'], self.CLASSTAG_CELL)

        # get rw-expnded (expanded row)
        expnd_rows = find_elem_by_xpath(main, rf'.//div[starts-with(@class, "{self.CLASSTAG_ROWS}")]')
        expnd_rows = filter_elems_list(expnd_rows, 'aria_role', 'none')

        # for each expanded rows get the indexes and cells values
        lst_index = []
        lst_value = []
        for expnd_row in expnd_rows:
            index = scrap_text_row_name(expnd_row['elem'], self.CLASSTAG_ROW_NAME)
            cells = scrap_text_row_name(expnd_row['elem'], self.CLASSTAG_CELL)
            # as row is expanded, hence more than one row per expnd_row
            # so reshape to by length of index
            arr_cells = np.array(cells).reshape(len(index), -1)
            lst_index.append(index)
            lst_value.append(arr_cells)

        dataframe = pd.DataFrame(index=np.hstack(lst_index), data=np.vstack(lst_value), columns=columns)
        dataframe.index.name = index_name
        return index_name, dataframe

    def _tidy_statements(self, statement):
        srs_count = statement.index.value_counts()
        srs_count.name = self.ID_LEVEL

        colname_idx = statement.index.name
        statement = statement.reset_index()
        statement = statement.join(srs_count, on=colname_idx).drop_duplicates()
        statement = statement.reset_index(drop=True)

        index_df = statement.loc[:, [colname_idx, self.ID_LEVEL]]
        body_df = statement.drop(columns=[colname_idx, self.ID_LEVEL])
        return index_df, body_df

    def _tree_from_index(self, index_name, index):
        """
        :param index_name: the name of index from scrapping (e.g. "Breakdown")
        :param index: the index from scrapping (e.g. Total Revenue
        :return: an organised tree structure for index

        As some item in the index is layered under another
        it is to be organised in a tree structure using the Anytree library
        """

        # obtain a list of node using anytree
        lst_nodes = [Node(e[index_name]) for num, e in index.to_dict('index').items()]

        # Organise the index to levels, and dictionary of index elems for each level
        # {level=1: {1: {elem_name1},
        #            3: {elem_name2},
        #            5: {elem_name3},},
        #  level=2: {2: {elem_name4},
        #            4: {elem_name5}}}
        # elem_name4 is under elem_name1, and elem_name5 is under elem_name2, there is nothing under elem_name3
        int_maxlvl = index[self.ID_LEVEL].max()
        dict_lvl = {idx: index[index[self.ID_LEVEL] == idx] for idx in range(1, int_maxlvl + 1)}
        dict_lvl = {idx: df.to_dict('index') for idx, df in dict_lvl.items()}

        # init the first level
        root = Node('root', children=[lst_nodes[idx] for idx in dict_lvl[1]])
        # add other lvl as children
        for lvl, elems in dict_lvl.items():
            if lvl != 1:
                prev_lvl_keys = dict_lvl[lvl - 1]
                for idx, elem in elems.items():
                    # search for its parent based on seq, get the last smaller seq
                    prev_lvl_prev_idx = [*filter(lambda x: x < idx, prev_lvl_keys)][-1]
                    lst_nodes[idx].parent = lst_nodes[prev_lvl_prev_idx]

        # add numbering to nodes, skipping root
        for node in PreOrderIter(root):
            num = 1
            for child in node.children:
                child.num = f'{num}.'
                num += 1
                if node.name != 'root':
                    child.num = f'{node.num}{child.num}'
        number = [node.num for node in [*PreOrderIter(root)][1:]]

        # get list of rendered in custom format
        objStyle = AbstractStyle(self.STYLE[0], self.STYLE[1], self.STYLE[2])
        temp = [*RenderTree(root, style=objStyle)]
        name = [e1[self.STYLE_LEN:].replace(self.STYLE[0], self.STYLE[1]) + e2.name for _, e1, e2 in temp[1:]]

        dict_df = {self.ID_NUMBERING: number, index_name: name}
        index = pd.DataFrame(dict_df, index=index.index)

        return root, index


if __name__ == '__main__':
    objYFS = YFscapper()
    objYFS.get_statements()
    objYFS.tidy_statements()
    objYFS.export_statements()






