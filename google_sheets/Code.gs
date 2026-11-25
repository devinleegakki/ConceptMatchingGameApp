// Bind this script to a PRIVATE scores spreadsheet and run setupScores once.
const USERS = ["key_hash", "display_name", "kind"];
const ATTEMPTS = ["player", "run_id", "attempt_id", "level", "matched", "pairs", "steps",
  "max_combo", "remaining", "duration", "failed", "points", "finished_at"];

function setupScores() {
  const book = SpreadsheetApp.getActiveSpreadsheet();
  sheetWithHeaders(book, "Users", USERS);
  sheetWithHeaders(book, "Attempts", ATTEMPTS);
  PropertiesService.getScriptProperties().setProperty("SCORES_BOOK_ID", book.getId());
}

function sheetWithHeaders(book, name, headers) {
  const tab = book.getSheetByName(name) || book.insertSheet(name);
  if (!tab.getLastRow()) tab.appendRow(headers);
  const found = tab.getRange(1, 1, 1, headers.length).getValues()[0];
  if (!headers.every((h, i) => found[i] === h)) throw Error("Unexpected headers in " + name);
  return tab;
}

function requireValue(ok, message) {
  if (!ok) throw Error(message);
}

function keyHash(key) {
  requireValue(typeof key === "string" && /^[0-9a-f]{32}$/.test(key), "Invalid player code.");
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, key);
  return "u_" + digest.map(b => ((b + 256) % 256).toString(16).padStart(2, "0")).join("");
}

function validateName(name) {
  requireValue(typeof name === "string" && /^[A-Za-z0-9][A-Za-z0-9 _-]{1,27}$/.test(name),
    "Use 2–28 English letters, numbers, spaces, underscores or hyphens for the name.");
}

function validatedScore(a) {
  requireValue(a && [1, 2].includes(a.level) && a.pairs === (a.level === 1 ? 4 : 6), "Invalid level.");
  requireValue(typeof a.finished_at === "string" && /^\d{4}-\d{2}-\d{2}T/.test(a.finished_at) &&
    Number.isFinite(Date.parse(a.finished_at)), "Invalid finish time.");
  for (const k of ["matched", "steps", "max_combo", "remaining", "duration"]) {
    requireValue(Number.isSafeInteger(a[k]) && a[k] >= 0 && a[k] <= 10000000, "Invalid score data.");
  }
  requireValue(a.matched <= a.pairs && a.steps >= a.matched && a.max_combo <= a.matched &&
    a.duration > 0 && a.remaining <= a.duration && typeof a.failed === "boolean" &&
    (a.failed ? a.remaining === 0 && a.matched < a.pairs : a.matched === a.pairs),
    "Inconsistent result.");
  for (const k of ["run_id", "attempt_id"]) {
    requireValue(typeof a[k] === "string" && /^[ra]_[0-9a-f]{32}$/.test(a[k]) &&
      a[k].startsWith(k === "run_id" ? "r_" : "a_"), "Invalid challenge ID.");
  }
  const matchNumerator = Math.max(0, 70*a.matched - 5*(a.steps-a.matched)*a.pairs);
  const numerator = (matchNumerator + 20*a.max_combo)*a.duration + (a.failed ? 0 : 10*a.remaining*a.pairs);
  return Math.floor(numerator/(a.pairs*a.duration) + 0.5);
}

function records(tab, headers) {
  return tab.getDataRange().getValues().slice(1).map(row =>
    Object.fromEntries(headers.map((h,i) => [h,row[i]])));
}

function bestRuns(attempts) {
  const runs = new Map();
  const best = new Map();
  for (const a of attempts) {
    if (a.failed) continue;
    const key = a.player + "/" + a.run_id;
    const run = runs.get(key) || {};
    run[a.level] = Math.max(a.points, run[a.level] || 0);
    runs.set(key, run);
    if (run[1] !== undefined && run[2] !== undefined) {
      best.set(a.player, Math.max(best.get(a.player) || 0, run[1]+run[2]));
    }
  }
  return best;
}

function dispatch(book, body) {
  const usersTab = book.getSheetByName("Users");
  const attemptsTab = book.getSheetByName("Attempts");
  const users = records(usersTab, USERS);
  const id = keyHash(body.key);
  let user = users.find(u => u.key_hash === id);
  if (body.action === "login") {
    requireValue(user && user.kind === "member", "Unknown sign-in code.");
    return {name: user.display_name};
  }
  requireValue(["register","profile","leaderboard","attempt"].includes(body.action), "Unknown action.");
  if (!user || body.action === "register") {
    validateName(body.name);
    const kind = body.action === "register" ? "member" : "guest";
    if (user) {
      usersTab.getRange(users.indexOf(user)+2, 2, 1, 2).setValues([[body.name, kind]]);
      user.display_name = body.name;
      user.kind = kind;
    } else {
      usersTab.appendRow([id, body.name, kind]);
      user = {key_hash:id, display_name:body.name, kind};
      users.push(user);
    }
  }
  if (body.action === "register") return {name:user.display_name};
  const all = records(attemptsTab, ATTEMPTS);
  if (body.action === "attempt") {
    const a = body.attempt;
    const points = validatedScore(a);
    const prior = all.find(row => row.attempt_id === a.attempt_id);
    if (prior) {
      requireValue(prior.player === id && prior.run_id === a.run_id && prior.level === a.level, "Attempt ID conflict.");
      return {points:prior.points};
    }
    const row = {...a, player:id, points, finished_at:new Date(a.finished_at).toISOString()};
    attemptsTab.appendRow(ATTEMPTS.map(k => row[k]));
    return {points};
  }
  if (body.action === "profile") {
    const mine = all.filter(a => a.player === id);
    return {name:user.display_name, kind:user.kind, attempts:mine.length,
      passed:mine.filter(a => !a.failed).length, best:bestRuns(mine).get(id) ?? null,
      history:mine.sort((a,b) => new Date(b.finished_at)-new Date(a.finished_at)).slice(0,10)
        .map(a => ({level:a.level, points:a.points, failed:a.failed, date:a.finished_at}))};
  }
  const names = new Map(users.map(u => [u.key_hash, u.display_name]));
  return Array.from(bestRuns(all), ([player,points]) => ({name:names.get(player), points, me:player===id}));
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  let result;
  try {
    const body = JSON.parse(e.postData.contents);
    lock.waitLock(15000);
    const book = SpreadsheetApp.openById(PropertiesService.getScriptProperties().getProperty("SCORES_BOOK_ID"));
    result = {ok:true, data:dispatch(book, body)};
    SpreadsheetApp.flush();
  } catch (error) {
    result = {ok:false, error:String(error.message || error)};
  } finally {
    if (lock.hasLock()) lock.releaseLock();
  }
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}
