import pandas as pd
from backend.ingestion.common import read_table

DIRECTORY_COLUMNS={'establishment_id','establishment_name','state','latitude','longitude','activities'}


class EstablishmentAdapter:
    def read(self,path):
        df=read_table(path,dtype=str)
        if not DIRECTORY_COLUMNS<=set(df):raise ValueError('Directory schema mismatch')
        mo=df[df.state.eq('MO')].copy()
        for c in ['latitude','longitude']: mo[c]=pd.to_numeric(mo[c],errors='coerce')
        # Never render numerically invalid coordinates as verified facilities.
        valid=mo.latitude.between(-90,90)&mo.longitude.between(-180,180)
        result=mo[valid].copy()
        result.attrs['input_rows']=len(df)
        result.attrs['missouri_rows']=len(mo)
        result.attrs['excluded_invalid_coordinates']=int((~valid).sum())
        return result
