#!/usr/bin/env bash
# ---------------------------------------------------------------
# Shared environment for every script in this project.
#   source scripts/env.sh
#
# Pins the toolchain to the versions actually verified on this
# machine so that a stray `java` on PATH cannot change the runtime
# out from under Spark.
# ---------------------------------------------------------------

export PATH="/opt/homebrew/bin:$PATH"

# Spark 4.2.0 is built against Java 21. The system default here is
# Java 26, which Spark does not claim support for, so both spark-submit
# and the sbt-forked JVM are pinned to 21 explicitly.
export AGRI_JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export JAVA_HOME="$AGRI_JAVA_HOME"

# This machine's hostname resolves to a loopback address, which makes
# Spark warn and then guess at a bind address. Pinning removes the
# ambiguity for local runs.
export SPARK_LOCAL_IP="127.0.0.1"

export AGRI_PROJECT_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Sized for this machine: 16 GB total RAM, 10 cores. Left as env vars
# so the scalability experiments can sweep them without code edits.
export AGRI_DRIVER_MEMORY="${AGRI_DRIVER_MEMORY:-8g}"
export AGRI_SHUFFLE_PARTITIONS="${AGRI_SHUFFLE_PARTITIONS:-32}"
