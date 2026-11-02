import pandas as pd
import pytest
from scripts.validate_model_timing import split_by_snapshot

SOURCES=[{'path':'old.json','metadata_creation_date':'March 19, 2026'},{'path':'new.json','metadata_creation_date':'October 9, 2026'}]
def rows():
    return pd.DataFrame({'source_file':['old.json','old.json','new.json','new.json','new.json'],'collection_date':['2025-01-01','2025-06-01','2026-03-19','2026-03-20','2026-06-30'],'salmonella_sp_analysis':['Positive','Negative','Positive','Negative','Positive'],'salmonella_sp_analysis_canceled':['NULL']*5})

def test_snapshot_split_has_distinct_sources_and_strictly_later_validation_dates():
    train,test,cutoff,snapshots=split_by_snapshot(rows(),SOURCES)
    assert len(train)==2 and len(test)==2
    assert test.collection_date.min()>cutoff
    assert not set(train.source_file)&set(test.source_file)
    assert cutoff==pd.Timestamp('2026-03-19')

def test_held_out_labels_cannot_change_training_snapshot():
    original=rows();train,_,_,_=split_by_snapshot(original,SOURCES)
    original.loc[original.source_file.eq('new.json'),'salmonella_sp_analysis']='Positive'
    train2,_,_,_=split_by_snapshot(original,SOURCES)
    pd.testing.assert_frame_equal(train,train2)

def test_one_snapshot_date_cannot_establish_prior_snapshot_validation():
    with pytest.raises(ValueError,match='two distinct'):split_by_snapshot(rows(),[SOURCES[0]])

def test_no_later_collection_dates_is_reported_as_infeasible():
    frame=rows();frame['collection_date']='2025-01-01'
    with pytest.raises(ValueError,match='No nonoverlapping'):split_by_snapshot(frame,SOURCES)


def test_nested_same_basename_sources_use_explicit_relative_source_identity():
    frame=rows();frame['source_file']=frame.source_file.map({'old.json':'prior/export.json','new.json':'later/export.json'})
    sources=[{'path':'C:/raw/prior/export.json','source_file':'prior/export.json','metadata_creation_date':'March 19, 2026'},
             {'path':'C:/raw/later/export.json','source_file':'later/export.json','metadata_creation_date':'October 9, 2026'}]
    train,test,_,snapshots=split_by_snapshot(frame,sources)
    assert len(train)==2 and len(test)==2
    assert set(snapshots)=={'prior/export.json','later/export.json'}
