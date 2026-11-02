from backend.ingestion.common import read_table

NORS_COLUMNS={'Year','State','Primary Mode','Etiology'}


class NORSAdapter:
    def read(self,path):
        df=read_table(path,low_memory=False)
        if not NORS_COLUMNS<=set(df):raise ValueError(f'NORS missing {NORS_COLUMNS-set(df)}')
        return df  # Historical outbreak evidence; never join to sampling labels.
