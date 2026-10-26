import pandas as pd
class NORSAdapter:
    def read(self,path):
        df=pd.read_csv(path,low_memory=False)
        required={'Year','State','Primary Mode','Etiology'}
        if not required<=set(df): raise ValueError(f'NORS missing {required-set(df)}')
        return df  # Historical outbreak evidence; never join to sampling labels.
