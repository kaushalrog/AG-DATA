"""The LightGBM candidate reproduces ForecastEval's conformal conventions and file layout."""
import numpy as np

from agri.forecast import lgbm as L


def test_bucket_matches_spark_rule_first_edge_with_std_le_edge():
    edges = np.array([0.1, 0.2, 0.3, 0.4])
    std = np.array([0.0, 0.1, 0.1000001, 0.2, 0.35, 0.4, 0.41, 9.0])
    assert L.bucket(std, edges).tolist() == [0, 0, 1, 1, 3, 3, 4, 4]


def test_conformal_csv_round_trip_and_interval_order(tmp_path):
    rng = np.random.default_rng(0)
    std = rng.gamma(2.0, 0.05, 20000)
    res = rng.normal(0, 1, 20000) * std
    edges, q = L.fit_conformal(std, res)
    p = tmp_path / "conformal_h7.csv"
    with open(p, "w") as f:
        f.write("horizon,bucket,quantile,residual_q,std30_upper_edge\n")
        for k in range(L.N_BUCKETS):
            e = edges[k] if k < len(edges) else float("inf")
            for pr in L.QUANTILES:
                f.write(f"h7,{k},{pr:.7f},{q[(k, pr)]:.9g},{'Infinity' if np.isinf(e) else f'{e:.9g}'}\n")
    e2, q2 = L.read_conformal(p)
    assert np.allclose(e2, edges, rtol=1e-8)
    assert all(abs(q2[k] - q[k]) < 1e-8 for k in q)
    iv = L.intervals(np.zeros(5), np.array([0.01, 0.05, 0.1, 0.2, 1.0]), e2, q2)
    assert np.all(iv["lo90"] <= iv["lo80"]) and np.all(iv["lo80"] <= 0) and np.all(0 <= iv["hi80"]) and np.all(iv["hi80"] <= iv["hi90"])
    # wider intervals in more volatile buckets
    assert iv["hi80"][-1] - iv["lo80"][-1] > iv["hi80"][0] - iv["lo80"][0]


def test_feature_order_matches_scala_base_features():
    import re
    src = open("src/main/scala/com/agribigdata/forecast/Features.scala").read()
    block = re.search(r"val BaseFeatures: Seq\[String\] = Seq\((.*?)\)", src, re.S).group(1)
    assert re.findall(r'"(\w+)"', block) == L.BASE
