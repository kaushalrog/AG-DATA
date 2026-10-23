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
