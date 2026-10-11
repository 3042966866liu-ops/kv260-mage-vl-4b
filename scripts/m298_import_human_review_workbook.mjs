#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  coverageFailures,
  coverageSummary,
  expectedReviewRows,
  parseReviewRows,
} from "./m298_human_review_contract.mjs";

const defaults = {
  workspace: "C:/Users/30429/Desktop/TeLLMe_FPGA_2026",
  workbook: "outputs/m296_bact_annotation/M296_BACT人工复核表.xlsx",
  manifest: "data/bact_target_scene/M296_TARGET_SCENE_MANIFEST_DRAFT.json",
  labels: "data/bact_target_scene/M298_HUMAN_REVIEW_LABELS.json",
  result: "deployment/mage_vl4b/M298_HUMAN_REVIEW_IMPORT_RESULT.json",
  artifactTool:
    "C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs",
};

function parseArgs(argv) {
  const args = { ...defaults };
  const mapping = {
    "--workspace": "workspace",
    "--workbook": "workbook",
    "--manifest": "manifest",
    "--labels": "labels",
    "--result": "result",
    "--artifact-tool": "artifactTool",
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = mapping[argv[index]];
    if (!key || index + 1 >= argv.length) throw new Error(`M298_ARGUMENT_FAIL token=${argv[index]}`);
    args[key] = argv[index + 1];
    index += 1;
  }
  return args;
}

function resolveUnder(workspace, value) {
  const resolved = path.resolve(workspace, value);
  const relative = path.relative(workspace, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) throw new Error(`M298_PATH_ESCAPE_FAIL path=${value}`);
  return resolved;
}

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function atomicJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.partial`;
  await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(temporary, filePath);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const workspace = path.resolve(args.workspace);
  const workbookPath = resolveUnder(workspace, args.workbook);
  const manifestPath = resolveUnder(workspace, args.manifest);
  const labelsPath = resolveUnder(workspace, args.labels);
  const resultPath = resolveUnder(workspace, args.result);
  const artifactModulePath = path.resolve(args.artifactTool);
  const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(artifactModulePath).href);

  const workbookBytes = await fs.readFile(workbookPath);
  const manifestBytes = await fs.readFile(manifestPath);
  const manifest = JSON.parse(manifestBytes.toString("utf8"));
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
  const sheet = workbook.worksheets.getItem("人工复核");
  const rawRows = await Promise.resolve(sheet.getRange("A5:O16").values);
  const expected = expectedReviewRows(manifest, workspace.replaceAll("\\", "/"));

  let rows;
  let immutableFailures = [];
  try {
    rows = parseReviewRows(rawRows, expected);
  } catch (error) {
    immutableFailures = error.failures ?? [{ error: String(error) }];
    const result = {
      date: "2026-09-03",
      gate: "M298-human-review-workbook-import",
      status: "FAIL_IMMUTABLE_SOURCE_CONTRACT",
      workbook: path.relative(workspace, workbookPath).replaceAll("\\", "/"),
      workbookSha256: sha256(workbookBytes),
      manifest: path.relative(workspace, manifestPath).replaceAll("\\", "/"),
      manifestSha256: sha256(manifestBytes),
      immutableFailures,
      labelsWritten: false,
      formalAccuracyAllowed: false,
      boardExecutionRun: false,
      activeM254M256Changed: false,
    };
    await atomicJson(resultPath, result);
    console.error("M298_HUMAN_REVIEW_IMPORT_FAIL immutable_source_contract");
    return 3;
  }

  const pending = rows.filter((row) => !row.qcPass);
  const coverage = coverageSummary(rows);
  const missingCoverage = coverageFailures(coverage);
  const complete = pending.length === 0 && missingCoverage.length === 0;
  const result = {
    date: "2026-09-03",
    gate: "M298-human-review-workbook-import",
    status: complete ? "PASS_HUMAN_REVIEW_LABELS_FROZEN" : "EXPECTED_FAIL_PENDING_HUMAN_REVIEW",
    classification: complete
      ? "Clip-constant human labels passed immutable-source, completeness and split-coverage contracts. This supports pilot clip/window classification metrics only; it is not bounding-box accuracy or real-world external validity."
      : "Workbook source identity is intact, but one or more human-review or split-coverage requirements remain incomplete. No accuracy evaluation is allowed.",
    workbook: path.relative(workspace, workbookPath).replaceAll("\\", "/"),
    workbookSha256: sha256(workbookBytes),
    manifest: path.relative(workspace, manifestPath).replaceAll("\\", "/"),
    manifestSha256: sha256(manifestBytes),
    rowCount: rows.length,
    qcPassCount: rows.filter((row) => row.qcPass).length,
    pendingCount: pending.length,
    pending: pending.map((row) => ({
      row: row.row,
      clipId: row.clipId,
      sourceFilename: row.sourceFilename,
      reasons: row.rejectionReasons,
    })),
    coverage,
    missingCoverage,
    immutableSourceContractPassed: true,
    filenameHintsUsedAsGroundTruth: false,
    labelsWritten: complete,
    formalAccuracyAllowed: complete,
    labelScope: "clip_constant_propagated_to_sampled_windows_without_fake_bounding_boxes",
    boundingBoxGroundTruthAvailable: false,
    realWorldExternalValidityClaimAllowed: false,
    boardExecutionRun: false,
    activeM254M256Changed: false,
    bootDtbCmaPartitionsChanged: false,
    stableRollbackPreserved: true,
    nextGate: complete
      ? "Freeze four-baseline thresholds using calibration labels only, then execute held-out test exactly once."
      : "A human must watch every complete video and fill the yellow cells until all 12 rows show QC PASS.",
  };

  if (complete) {
    const labels = {
      schema: "tellme-bact-clip-constant-v1",
      date: "2026-09-03",
      sourceManifest: result.manifest,
      sourceManifestSha256: result.manifestSha256,
      sourceWorkbook: result.workbook,
      sourceWorkbookSha256: result.workbookSha256,
      annotationPolicy: "Human full-video labels are authoritative; filename hints and model outputs are not ground truth.",
      scope: "AI_GENERATED_PILOT_CLIP_AND_SAMPLED_WINDOW_CLASSIFICATION",
      clips: rows.map((row) => ({
        clipId: row.clipId,
        split: row.split,
        sourceFilename: row.sourceFilename,
        videoSha256: row.videoSha256,
        annotationStatus: "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT",
        action: row.action,
        knifePresent: row.knifePresent,
        actionConstant: row.actionConstant,
        knifeConstant: row.knifeConstant,
        watchedComplete: row.watchedComplete,
        annotator: row.annotator,
        notes: row.notes,
      })),
    };
    await atomicJson(labelsPath, labels);
    result.labels = path.relative(workspace, labelsPath).replaceAll("\\", "/");
    result.labelsSha256 = sha256(await fs.readFile(labelsPath));
  }
  await atomicJson(resultPath, result);
  if (!complete) {
    console.error(`M298_HUMAN_REVIEW_IMPORT_EXPECTED_FAIL pending=${pending.length} missing_coverage=${missingCoverage.length}`);
    return 2;
  }
  console.log(`M298_HUMAN_REVIEW_IMPORT_PASS rows=${rows.length} labels_sha256=${result.labelsSha256}`);
  return 0;
}

process.exitCode = await main();
