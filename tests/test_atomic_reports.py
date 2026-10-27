import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from backend.paths import write_json, read_json


def test_polling_readers_never_observe_partial_generated_json(tmp_path):
    path=tmp_path/'response.json';write_json(path,{'revision':-1,'payload':'x'*250000})
    stop=Event()
    def writer():
        try:
            for i in range(30):write_json(path,{'revision':i,'payload':'x'*250000})
        finally:stop.set()
    def reader():
        reads=0
        while not stop.is_set() or reads<2:
            value=read_json(path)
            assert len(value['payload'])==250000 and -1<=value['revision']<=29
            reads+=1
            time.sleep(.001)  # Independent polling requests release their read handles.
        return reads
    with ThreadPoolExecutor(max_workers=3) as pool:
        a=pool.submit(reader);b=pool.submit(reader);w=pool.submit(writer)
        w.result();assert a.result()>=2 and b.result()>=2
    assert json.loads(path.read_text())['revision']==29
    assert not list(tmp_path.glob('*.tmp'))


def test_serialization_failure_preserves_prior_generated_response(tmp_path):
    path=tmp_path/'response.json';write_json(path,{'version':1})
    circular=[];circular.append(circular)
    with pytest.raises(ValueError):write_json(path,circular)
    assert json.loads(path.read_text())=={'version':1}
