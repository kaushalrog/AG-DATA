package com.agribigdata.forecast

import org.apache.spark.sql.DataFrame

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths, StandardOpenOption}
import scala.sys.process._

/** Small, dependency-free writers for experiment outputs (all inputs are small, already-aggregated tables). */
object ResultsIO {

  def dir(p: String): Path = { val d = Paths.get(p); Files.createDirectories(d); d }

  private def cell(v: Any): String = v match {
    case null => ""
    case d: Double if d.isNaN => ""
    case d: Double => f"$d%.6g"
    case s: String if s.exists(c => c == ',' || c == '"' || c == '\n') => "\"" + s.replace("\"", "\"\"") + "\""
    case x => x.toString
  }

  /** Collects a SMALL aggregated DataFrame and writes it as CSV. */
  def writeCsv(df: DataFrame, path: String): Unit = {
    val rows = df.collect()
    val header = df.columns.mkString(",")
    val body = rows.map(r => r.toSeq.map(cell).mkString(","))
    Files.writeString(Paths.get(path), (header +: body).mkString("\n") + "\n")
  }

  def writeLines(path: String, header: String, lines: Seq[Seq[Any]]): Unit =
    Files.writeString(Paths.get(path), (header +: lines.map(_.map(cell).mkString(","))).mkString("\n") + "\n")

  def appendLine(path: String, line: String): Unit = {
    dir(Paths.get(path).getParent.toString)
    Files.writeString(Paths.get(path), line + "\n", StandardCharsets.UTF_8,
      StandardOpenOption.CREATE, StandardOpenOption.APPEND)
  }

  def json(v: Any): String = v match {
    case null => "null"
    case s: String => "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\""
    case d: Double if d.isNaN || d.isInfinite => "null"
    case b: Boolean => b.toString
    case n: Number => n.toString
    case m: Map[_, _] => m.map { case (k, x) => json(k.toString) + ": " + json(x) }.mkString("{", ", ", "}")
    case s: Seq[_] => s.map(json).mkString("[", ", ", "]")
    case a: Array[_] => json(a.toSeq)
    case o => json(o.toString)
  }

  def gitCommit: String = try { "git rev-parse --short HEAD".!!.trim } catch { case _: Throwable => "unknown" }
  def gitDirty: Boolean = try { "git status --porcelain".!!.trim.nonEmpty } catch { case _: Throwable => true }
}
