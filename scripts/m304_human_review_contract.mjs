import {
  coverageFailures,
  coverageSummary,
  expectedReviewRows,
  parseReviewRows,
  upper,
} from "./m298_human_review_contract.mjs";

export { coverageFailures, coverageSummary, expectedReviewRows };

export const CONDITION_FIELDS = Object.freeze([
  ["lowLight", 15, "low_light"],
  ["occlusion", 16, "occlusion"],
  ["smallKnife", 17, "small_knife"],
]);

export function parseM304ReviewRows(rawRows, expectedRows) {
  if (!Array.isArray(rawRows) || rawRows.length !== expectedRows.length) {
    throw new Error(`M304_ROW_COUNT_FAIL expected=${expectedRows.length} observed=${rawRows?.length ?? "invalid"}`);
  }
  if (rawRows.some((row) => !Array.isArray(row) || row.length < 18)) {
    throw new Error("M304_ROW_SHAPE_FAIL expected_columns=18");
  }
  const baseRows = parseReviewRows(rawRows.map((row) => row.slice(0, 15)), expectedRows);
  return baseRows.map((base, index) => {
    const raw = rawRows[index];
    const rejectionReasons = [...base.rejectionReasons];
    const conditions = {};
    for (const [key, columnIndex, reasonPrefix] of CONDITION_FIELDS) {
      const value = upper(raw[columnIndex]);
      if (!["TRUE", "FALSE"].includes(value)) rejectionReasons.push(`${reasonPrefix}_not_definite`);
      conditions[key] = value === "TRUE" ? true : value === "FALSE" ? false : null;
    }
    if (conditions.smallKnife === true && base.knifePresent !== true) {
      rejectionReasons.push("small_knife_true_without_knife_positive");
    }
    return {
      ...base,
      conditions,
      qcPass: rejectionReasons.length === 0,
      rejectionReasons,
    };
  });
}

export function conditionCoverageSummary(rows) {
  const output = {};
  for (const split of ["calibration", "test"]) {
    const selected = rows.filter((row) => row.split === split && row.qcPass);
    output[split] = Object.fromEntries(
      CONDITION_FIELDS.map(([key]) => [key, {
        trueCount: selected.filter((row) => row.conditions[key] === true).length,
        falseCount: selected.filter((row) => row.conditions[key] === false).length,
      }]),
    );
  }
  return output;
}

export function conditionCoverageFailures(summary) {
  const failures = [];
  for (const [key, , reasonPrefix] of CONDITION_FIELDS) {
    if (summary.test[key].trueCount < 1) failures.push(`test_${reasonPrefix}_positive_slice_missing`);
    if (summary.test[key].falseCount < 1) failures.push(`test_${reasonPrefix}_negative_slice_missing`);
  }
  return failures;
}
