import pandas as pd
class EstablishmentAdapter:
    def read(self,path):
        df=pd.read_csv(path,dtype=str)
        if not {'establishment_id','state','latitude','longitude'}<=set(df): raise ValueError('Directory schema mismatch')
        mo=df[df.state.eq('MO')].copy()
        for c in ['latitude','longitude']: mo[c]=pd.to_numeric(mo[c],errors='coerce')
        return mo.dropna(subset=['latitude','longitude'])
