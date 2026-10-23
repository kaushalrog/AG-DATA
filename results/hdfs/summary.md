# HDFS verification, 2026-10-23 (`docker/docker-compose.yml`: 1 NameNode + 3 DataNodes, apache/hadoop 3.4.1, amd64 emulation on Apple Silicon)

| Check | Result | Evidence file |
|---|---|---|
| Live DataNodes | 3 | `report_after_restart.txt` |
| Layout created | `/agri/{raw,bronze,silver,features,models,predictions,gold,checkpoints,metadata}` | `du.txt` |
| Silver layer loaded | 691,714,074 B, 1,743 files, 1,742 blocks, `hdfs dfs -put` in 200 s | `fsck_silver.txt`, `load_timing.txt` |
| Replication factor | 3 (default); average block replication 2.92 right after the load, 2.99 after a minute | `fsck_silver.txt`, `fsck_after_restart.txt` |
| Under-replicated blocks | 146 right after the load → 122 → 13 → 6, converging; 0 missing, 0 corrupt, status HEALTHY | `fsck_*.txt` |
| DataNode failure | datanode2 stopped; probe file (3 live replicas) read in full (738,192 B) with an identical checksum | `checksum_before.txt`, `checksum_datanode_down.txt`, `read_bytes_datanode_down.txt` |
| Model artifacts | `fc_main_v3` pipelines copied to `/agri/models/` | `du.txt` |

## Caveats
* **One physical disk.** All three DataNodes share the Docker VM's disk on one laptop. Replication therefore shows HDFS behaviour (placement, failover, re-replication), not durability against hardware loss.
* **Dead-node detection.** During the 20-second outage the NameNode still listed 3 live DataNodes. Its default heartbeat timeout marks a node dead only after about 10.5 minutes. The read succeeded because the client fails over to another replica. Re-replication after a confirmed dead node was not observed in this run.
* **Small files.** The silver layer is 1,743 files of about 0.4 MB each, written by Spark with many partitions per year. That is below the 128 MB block size, so the NameNode carries per-file overhead. A compaction step (`repartition(1)` per `year=`) is recommended before production use.
* **No HA.** There is a single NameNode.
* The volumes also hold data from earlier sessions (`/agri/raw`, `/agri/processed`, `/agri/features`); these were not created by this run.
