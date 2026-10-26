import pandas as pd
class BEAMAdapter:
    def read(self,path):
        df=pd.read_csv(path,low_memory=False)
        if not any('serotype' in str(c).lower() or 'hhs' in str(c).lower() or 'pathogen' in str(c).lower() for c in df): raise ValueError('BEAM schema unconfirmed; inspect exported metadata')
        return df
