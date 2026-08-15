// ============================================================
// Real-Time Agricultural Market Anomaly Detection
// and Price Forecasting at Large Scale
//
// School of AI  |  Faculty: Dr. Sreeja
// ============================================================
//
// Versions are pinned to the toolchain actually installed and
// verified on this machine (see PROJECT_STATUS.md):
//   Apache Spark 4.2.0
//   Scala        2.13.18
//   OpenJDK      21.0.12  (the JVM Spark itself runs on)

ThisBuild / organization := "com.agribigdata"
ThisBuild / version      := "0.1.0"

// Must match the Scala version Spark 4.2.0 was compiled against.
// Mixing Scala minor lines across the Spark boundary breaks binary
// compatibility, so this is not a free choice.
ThisBuild / scalaVersion := "2.13.18"

lazy val sparkVersion = "4.2.0"

// Spark's own JVM is 21. Emitting class files for a newer JVM than the
// one the executors run on would fail at load time, so we pin the target.
ThisBuild / javacOptions ++= Seq("-source", "21", "-target", "21")

lazy val root = (project in file("."))
  .settings(
    name := "agri-bigdata",

    scalacOptions ++= Seq(
      "-deprecation",
      "-feature",
      "-unchecked",
      "-release", "21"
    ),

    libraryDependencies ++= Seq(
      // --- Core distributed engine -------------------------------
      // "provided": these jars already ship with the Spark install, so
      // bundling them into the assembly would duplicate (and possibly
      // conflict with) the cluster's own copies.
      "org.apache.spark" %% "spark-core"  % sparkVersion % Provided,
      "org.apache.spark" %% "spark-sql"   % sparkVersion % Provided,
      "org.apache.spark" %% "spark-mllib" % sparkVersion % Provided,

      // --- Kafka source for Structured Streaming -----------------
      // NOT provided: the Kafka connector is an external module that is
      // not on the default spark-submit classpath.
      "org.apache.spark" %% "spark-sql-kafka-0-10" % sparkVersion,

      // --- Test --------------------------------------------------
      "org.scalatest" %% "scalatest" % "3.2.19" % Test
    ),

    // `sbt run` executes in this JVM, so the Provided jars must be put
    // back on the classpath for local development runs.
    Compile / run := Defaults.runTask(
      Compile / fullClasspath,
      Compile / run / mainClass,
      Compile / run / runner
    ).evaluated,

    Compile / runMain := Defaults.runMainTask(
      Compile / fullClasspath,
      Compile / run / runner
    ).evaluated,

    // Spark spawns its own threads and calls System.exit; forking keeps
    // that out of the sbt JVM.
    //
    // Forking also lets us choose the JVM. sbt itself launches under
    // whatever `java` is first on PATH (Java 26 on this machine), but
    // Spark 4.2.0 is built and tested against Java 21 and its use of
    // sun.misc.Unsafe is not guaranteed on 26. AGRI_JAVA_HOME pins the
    // forked JVM to the same Java 21 that spark-shell uses.
    run / javaHome := sys.env.get("AGRI_JAVA_HOME").map(file),
    Test / javaHome := sys.env.get("AGRI_JAVA_HOME").map(file),
    run / fork := true,
    Test / fork := true,

    // Spark 4 on JDK 17+ needs these opens for its unsafe memory access
    // and reflective serializer setup.
    run / javaOptions ++= Seq(
      "-Xmx6g",
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
      "--add-opens=java.base/java.io=ALL-UNNAMED",
      "--add-opens=java.base/java.net=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
      // Required to bring a DateType column back to the driver: Spark's
      // DateTimeUtils.toJavaDate reaches into sun.util.calendar.ZoneInfo
      // via a MethodHandle, which the module system blocks by default on
      // JDK 17+. Without this, any .head()/.collect() touching a date
      // fails with EXPRESSION_DECODING_FAILED.
      "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED",
      "--add-opens=java.base/java.text=ALL-UNNAMED",
      "--add-opens=java.base/java.time=ALL-UNNAMED"
    ),
    Test / javaOptions ++= (run / javaOptions).value,

    // Assembly: keep only our code + non-provided deps.
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", "services", _*) => MergeStrategy.concat
      case PathList("META-INF", _*)             => MergeStrategy.discard
      case "module-info.class"                  => MergeStrategy.discard
      case x                                    => MergeStrategy.first
    },
    assembly / assemblyJarName := "agri-bigdata-assembly.jar",
    assembly / mainClass := None
  )
