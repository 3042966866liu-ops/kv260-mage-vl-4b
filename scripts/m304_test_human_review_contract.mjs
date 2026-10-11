#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import {
  conditionCoverageFailures,
  conditionCoverageSummary,
  coverageFailures,
  coverageSummary,
  expectedReviewRows,
  parseM304ReviewRows,
} from "./m304_human_review_contract.mjs";

const workspace = path.resolve(process.argv[2] ?? ".");
const manifest = JSON.parse(await fs.readFile(path.join(workspace, "data/bact_target_scene/M296_TARGET_SCENE_MANIFEST_DRAFT.json"), "utf8"));
const expected = expectedReviewRows(manifest, workspace.replaceAll("\\", "/"));
const rawRows = expected.map(({ clip, immutable }) => {
  const name = immutable.sourceFilename.toLowerCase();
  const action = immutable.actionHint;
  const knife = immutable.knifeHint === "POSITIVE_HINT" ? "TRUE" : "FALSE";
  return [
    "PASS", immutable.split, immutable.sourceFilename, immutable.durationSeconds, immutable.videoSha256,
    immutable.actionHint, immutable.knifeHint, action, knife, "TRUE", "TRUE", "TRUE", "contract-test", "synthetic contract only",
    immutable.localPath,
    name.includes("lowlight") ? "TRUE" : "FALSE",
    name.includes("occluded") ? "TRUE" : "FALSE",
    name.includes("knife_small") ? "TRUE" : "FALSE",
  ];
});
const parsed = parseM304ReviewRows(rawRows, expected);
assert.equal(parsed.length, 12);
assert.equal(parsed.every((row) => row.qcPass), true);
assert.deepEqual(coverageFailures(coverageSummary(parsed)), []);
assert.deepEqual(conditionCoverageFailures(conditionCoverageSummary(parsed)), []);

const missingCondition = rawRows.map((row) => [...row]);
missingCondition[0][15] = "UNCERTAIN";
assert.equal(parseM304ReviewRows(missingCondition, expected)[0].qcPass, false);

const invalidSmallKnife = rawRows.map((row) => [...row]);
const negativeIndex = invalidSmallKnife.findIndex((row) => row[8] === "FALSE");
invalidSmallKnife[negativeIndex][17] = "TRUE";
const invalidParsed = parseM304ReviewRows(invalidSmallKnife, expected)[negativeIndex];
assert.equal(invalidParsed.qcPass, false);
assert.equal(invalidParsed.rejectionReasons.includes("small_knife_true_without_knife_positive"), true);

console.log("M304_HUMAN_REVIEW_CONTRACT_PASS rows=12 condition_slices=3 negative_paths=2");
