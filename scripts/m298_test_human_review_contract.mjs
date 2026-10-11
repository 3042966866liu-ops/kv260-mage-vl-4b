#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { coverageFailures, coverageSummary, expectedReviewRows, parseReviewRows } from "./m298_human_review_contract.mjs";

const workspace = "C:/Users/30429/Desktop/TeLLMe_FPGA_2026";
const manifest = JSON.parse(await fs.readFile(path.join(workspace, "data/bact_target_scene/M296_TARGET_SCENE_MANIFEST_DRAFT.json"), "utf8"));
const expected = expectedReviewRows(manifest, workspace);
const actions = ["WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING", "WORKING"];

function validRows() {
  return expected.map((item, index) => [
    "PASS",
    item.immutable.split,
    item.immutable.sourceFilename,
    item.immutable.durationSeconds,
    item.immutable.videoSha256,
    item.immutable.actionHint,
    item.immutable.knifeHint,
    actions[index % 6],
    index % 2 === 0 ? "TRUE" : "FALSE",
    "TRUE",
    "TRUE",
    "TRUE",
    "synthetic-contract-test",
    "synthetic row; never emitted as dataset truth",
    item.immutable.localPath,
  ]);
}

const parsed = parseReviewRows(validRows(), expected);
assert.equal(parsed.length, 12);
assert.equal(parsed.every((row) => row.qcPass), true);
const coverage = coverageSummary(parsed);
assert.deepEqual(coverageFailures(coverage), []);

const pendingRows = validRows();
pendingRows[0][7] = "";
const pending = parseReviewRows(pendingRows, expected);
assert.equal(pending[0].qcPass, false);
assert.deepEqual(pending[0].rejectionReasons, ["action_not_one_of_five"]);

const ambiguousRows = validRows();
ambiguousRows[0][8] = "UNCERTAIN";
assert.equal(parseReviewRows(ambiguousRows, expected)[0].qcPass, false);

const tamperedRows = validRows();
tamperedRows[0][4] = "0".repeat(64);
assert.throws(() => parseReviewRows(tamperedRows, expected), /M298_IMMUTABLE_SOURCE_CONTRACT_FAIL/);

console.log("M298_HUMAN_REVIEW_CONTRACT_TEST_PASS positive=1 pending=2 tamper_rejected=1");
