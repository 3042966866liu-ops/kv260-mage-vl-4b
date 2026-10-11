export const ALLOWED_ACTIONS = Object.freeze(["WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING"]);

export function normalise(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

export function upper(value) {
  return normalise(value).toUpperCase();
}

export function expectedReviewRows(manifest, workspace) {
  return [...manifest.clips]
    .sort((a, b) => a.split.localeCompare(b.split) || a.source_filename.localeCompare(b.source_filename))
    .map((clip) => ({
      clip,
      immutable: {
        split: clip.split,
        sourceFilename: clip.source_filename,
        durationSeconds: clip.video_metadata.duration_ms / 1000,
        videoSha256: clip.video_sha256,
        actionHint: clip.filename_hints.action_hint_not_ground_truth,
        knifeHint: clip.filename_hints.knife_hint_not_ground_truth,
        localPath: `${workspace.replaceAll("/", "\\")}\\data\\bact_target_scene\\inbox\\${clip.source_filename}`,
      },
    }));
}

export function parseReviewRows(rawRows, expectedRows) {
  if (!Array.isArray(rawRows) || rawRows.length !== expectedRows.length) {
    throw new Error(`M298_ROW_COUNT_FAIL expected=${expectedRows.length} observed=${rawRows?.length ?? "invalid"}`);
  }
  const parsed = [];
  const immutableFailures = [];
  for (let index = 0; index < expectedRows.length; index += 1) {
    const raw = rawRows[index];
    if (!Array.isArray(raw) || raw.length < 15) throw new Error(`M298_ROW_SHAPE_FAIL row=${index + 5}`);
    const expected = expectedRows[index];
    const observedDuration = Number(raw[3]);
    const checks = [
      ["split", normalise(raw[1]), expected.immutable.split],
      ["source_filename", normalise(raw[2]), expected.immutable.sourceFilename],
      ["video_sha256", normalise(raw[4]).toLowerCase(), expected.immutable.videoSha256.toLowerCase()],
      ["action_hint", upper(raw[5]), upper(expected.immutable.actionHint)],
      ["knife_hint", upper(raw[6]), upper(expected.immutable.knifeHint)],
      ["local_path", normalise(raw[14]).toLowerCase(), expected.immutable.localPath.toLowerCase()],
    ];
    for (const [field, observed, wanted] of checks) {
      if (observed !== wanted) immutableFailures.push({ row: index + 5, field, observed, expected: wanted });
    }
    if (!Number.isFinite(observedDuration) || Math.abs(observedDuration - expected.immutable.durationSeconds) > 0.001) {
      immutableFailures.push({
        row: index + 5,
        field: "duration_seconds",
        observed: raw[3],
        expected: expected.immutable.durationSeconds,
      });
    }

    const action = upper(raw[7]);
    const knife = upper(raw[8]);
    const actionConstant = upper(raw[9]);
    const knifeConstant = upper(raw[10]);
    const watchedComplete = upper(raw[11]);
    const annotator = normalise(raw[12]);
    const notes = normalise(raw[13]);
    const reasons = [];
    if (!ALLOWED_ACTIONS.includes(action)) reasons.push("action_not_one_of_five");
    if (!["TRUE", "FALSE"].includes(knife)) reasons.push("knife_not_definite");
    if (actionConstant !== "TRUE") reasons.push("action_not_constant");
    if (knifeConstant !== "TRUE") reasons.push("knife_not_constant");
    if (watchedComplete !== "TRUE") reasons.push("whole_clip_not_confirmed");
    if (!annotator) reasons.push("annotator_missing");
    parsed.push({
      row: index + 5,
      clipId: expected.clip.clip_id,
      split: expected.clip.split,
      sourceFilename: expected.clip.source_filename,
      videoSha256: expected.clip.video_sha256,
      action,
      knifePresent: knife === "TRUE" ? true : knife === "FALSE" ? false : null,
      actionConstant: actionConstant === "TRUE",
      knifeConstant: knifeConstant === "TRUE",
      watchedComplete: watchedComplete === "TRUE",
      annotator,
      notes,
      qcPass: reasons.length === 0,
      rejectionReasons: reasons,
    });
  }
  if (immutableFailures.length) {
    const error = new Error("M298_IMMUTABLE_SOURCE_CONTRACT_FAIL");
    error.failures = immutableFailures;
    throw error;
  }
  return parsed;
}

export function coverageSummary(rows) {
  const summary = {};
  for (const split of ["calibration", "test"]) {
    const selected = rows.filter((row) => row.split === split && row.qcPass);
    summary[split] = {
      clipCount: selected.length,
      knifePositive: selected.filter((row) => row.knifePresent === true).length,
      knifeNegative: selected.filter((row) => row.knifePresent === false).length,
      actions: Object.fromEntries(ALLOWED_ACTIONS.map((action) => [action, selected.filter((row) => row.action === action).length])),
    };
  }
  return summary;
}

export function coverageFailures(summary) {
  const failures = [];
  for (const split of ["calibration", "test"]) {
    const value = summary[split];
    if (value.knifePositive < 1) failures.push(`${split}_knife_positive_missing`);
    if (value.knifeNegative < 1) failures.push(`${split}_knife_negative_missing`);
    for (const action of ALLOWED_ACTIONS) {
      if (value.actions[action] < 1) failures.push(`${split}_${action.toLowerCase()}_missing`);
    }
  }
  return failures;
}
