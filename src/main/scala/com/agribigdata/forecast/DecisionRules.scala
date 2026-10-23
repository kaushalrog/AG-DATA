package com.agribigdata.forecast

import com.fasterxml.jackson.databind.ObjectMapper

import java.io.File
import scala.jdk.CollectionConverters._

/** Loads conf/decision_rules.json, the single source of decision thresholds shared with the API. */
final case class DecisionRules(version: String, weeklyPerishable: Double, weeklyDurable: Double,
                               fixedCost: Double, perishable: Seq[String])

object DecisionRules {
  def load(path: String = sys.env.getOrElse("AGRI_DECISION_RULES", "conf/decision_rules.json")): DecisionRules = {
    val n = new ObjectMapper().readTree(new File(path))
    DecisionRules(
      n.get("version").asText(),
      n.get("weekly_holding_cost").get("perishable").asDouble(),
      n.get("weekly_holding_cost").get("durable").asDouble(),
      n.get("fixed_transaction_cost").asDouble(),
      n.get("perishable_commodities").elements().asScala.map(_.asText()).toSeq)
  }
}
