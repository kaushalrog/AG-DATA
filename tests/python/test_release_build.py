"""The build must fail closed on mutation, absent inputs and partial outputs."""
import json
from pathlib import Path
import pytest
from agri.research import release_build as B

@pytest.fixture
def fixture(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(B,'source_state',lambda:{'commit':'fixed','files':{'builder':'hash'}})
    jar=tmp_path/'assembly.jar';jar.write_bytes(b'jar');monkeypatch.setattr(B,'JAR',jar)
    for root in ['silver','panel']:
        Path(root).mkdir();Path(root,'part.parquet').write_bytes(root.encode())
    Path('conf/shards').mkdir(parents=True)
    for shard in 'abcd':Path(f'conf/shards/commodities_{shard}.txt').write_text(shard)
    return {'silver':'silver','panel':'panel','history_start':'2022-10-01','jump_rule':False}

@pytest.mark.parametrize('changed',['silver/part.parquet','panel/part.parquet','assembly.jar','conf/shards/commodities_a.txt'])
def test_prebuild_snapshot_detects_mutated_inputs_artifact_or_config(fixture,changed):
    before=B.snapshot(fixture);Path(changed).write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='changed during build'):B.verify_snapshot(before,B.snapshot(fixture))

def test_missing_panel_is_not_silently_accepted(fixture):
    Path('panel/part.parquet').unlink()
    with pytest.raises(RuntimeError,match='Missing build inputs'):B.snapshot(fixture)

def test_partial_build_is_not_verified(tmp_path):
    (tmp_path/'BUILD_MANIFEST.json').write_text(json.dumps({'kind':'observed_pre_post_build','status':'running'}))
    with pytest.raises(RuntimeError,match='Unverified build'):B.verify(tmp_path)

@pytest.mark.parametrize('change',['jump_rule','inputs','history_start'])
def test_build_pair_requires_only_cleaning_difference(change):
    import copy
    base={'before':{'inputs':{'silver':'fixed'},'shards':{'a':'hash'},'source':{'commit':'fixed'},'jar_sha256':'jar','config':{'jump_rule':True,'history_start':'2022-10-01'}}}
    pair={'cleaned':copy.deepcopy(base),'unfiltered':copy.deepcopy(base)}
    pair['unfiltered']['before']['config']['jump_rule']=False
    B.compatible_pair(pair)
    if change=='inputs':pair['unfiltered']['before']['inputs']['silver']='changed'
    else:pair['unfiltered']['before']['config'][change]=True if change=='jump_rule' else '2023-01-01'
    with pytest.raises(RuntimeError):B.compatible_pair(pair)
