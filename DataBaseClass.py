import os.path

import pandas as pd, numpy as np
import ScrappingClass

from datetime import datetime as dt
from time import perf_counter


class Database:
    NAME_STOCKS_LIST = 'Symbol'

    def __init__(self, name, path):
        self.path = path
        self.scrapper = ScrappingClass.YFscapper
        self.name = name
        self.stocks = None

    def _get_stock_list(self):
        df_stocks = pd.read_csv(self.path, dtype=str, index_col=None)
        self.stocks = df_stocks[self.NAME_STOCKS_LIST].values

    def download_data(self, directory='.', verbose=False):
        self._get_stock_list()
        time_month = dt.now().strftime("%y'%m")
        for e in self.stocks:

            start = perf_counter()
            actual_path = os.path.join(directory, f'{e}_{time_month}.xlsx')
            objScrapper = self.scrapper(e)

            objScrapper.get_statements(verbose=True)
            objScrapper.tidy_statements()
            objScrapper.export_statements(path=actual_path)
            if verbose:
                final = (perf_counter() - start)
                print(f'Obtained {e} data in {final:.1f} secs.')


if __name__ == "__main__":
    objDB = Database(name='US_Tech_LargeCap_Buy', path='./Database/nasdaq_screener_1645970051286.csv')
    objDB.download_data(directory='./Database', verbose=False)

