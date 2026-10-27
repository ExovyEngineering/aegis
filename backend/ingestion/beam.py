from backend.ingestion.common import read_table

# These identities describe observed export schemas, never discovery order.
BEAM_SCHEMAS={
    'beam_0':{'Year','HHS_Region','Pathogen','Number_of_isolates','Past_two_years_average'},
    'beam_1':{'Year','Source Type','Source Site','Pathogen','Serotype/Species','Number of isolates'},
    'beam_2':{'Pathogen','Food_category','Serotype','Burden','Trajectory','Year_range'},
    'beam_3':{'Food_category','Year_first_ill','Serotype','No_of_illnesses','No_of_outbreaks','Pathogen'},
    'beam_4':{'Year','Pathogen','Serotype/Species/Subgroup','Number of isolates','Past two years average','% Change'},
}


def beam_identity(columns):
    matches=[identity for identity,required in BEAM_SCHEMAS.items() if required<=set(columns)]
    if len(matches)>1:raise ValueError(f'Ambiguous BEAM export schema matches {matches}')
    return matches[0] if matches else None


class BEAMAdapter:
    def read(self,path):
        df=read_table(path,low_memory=False)
        if beam_identity(df.columns) is None:raise ValueError('BEAM schema unconfirmed; no supported content signature')
        return df
