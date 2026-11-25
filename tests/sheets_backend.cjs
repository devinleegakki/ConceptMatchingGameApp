const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');

const context = vm.createContext({
  Utilities: {DigestAlgorithm: {SHA_256:'sha256'},
    computeDigest: (algo, str) => Array.from(crypto.createHash(algo).update(str).digest())}
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../google_sheets/Code.gs'),'utf8'), context);

function sheet() {
  const rows = [['headers']];
  return {
    appendRow(row) { rows.push(row); },
    getDataRange() { return {getValues: () => rows}; },
    getRange(r,c) { return {setValues(values) { rows[r-1].splice(c-1,values[0].length,...values[0]); }}; }
  };
}
function setup() {
  const tabs = {Users:sheet(), Attempts:sheet()};
  const book = {getSheetByName: name => tabs[name]};
  return (action, data={}) => context.dispatch(book, {action,key:'1'.repeat(32),name:'Guest-Robin',...data});
}
function attempt(run, id, level, failed=false) {
  const pairs = level === 1 ? 4 : 6;
  return {run_id:'r_'+run.repeat(32),attempt_id:'a_'+id.repeat(32), level, pairs,
    matched:failed ? 0 : pairs, steps:pairs+1, max_combo:failed ? 0 : pairs-1,
    duration:120, remaining:failed ? 0 : 60, failed, finished_at:'2026-11-24T07:00:00Z'};
}

test('guest, replay after lost response, promotion and private sign-in', () => {
  const api=setup(), a=attempt('a','1',1);
  assert.equal(api('profile').kind,'guest');
  assert.equal(api('attempt',{attempt:a}).points,85);
  api('attempt',{attempt:a});
  assert.equal(api('profile').attempts,1);
  api('register',{name:'Luna'});
  assert.equal(api('login').name,'Luna');
  assert.equal(api('profile').history[0].points,85);
  assert.throws(() => api('login',{key:'2'.repeat(32)}),/Unknown/);
  assert.equal(api('profile',{key:'2'.repeat(32)}).attempts,0);
});
test('rank only complete runs, keep timeout history and best per player', () => {
  const api=setup();
  api('attempt',{attempt:attempt('a','1',1)});
  api('attempt',{attempt:attempt('b','2',2)});
  api('attempt',{attempt:attempt('a','3',2,true)});
  assert.equal(api('leaderboard').length,0);
  const second=api('attempt',{attempt:attempt('a','4',2)}).points;
  assert.equal(api('leaderboard')[0].points,85+second);
  assert.equal(api('profile').attempts,4);
  assert.equal(api('profile').passed,3);
  assert.equal(api('profile').best,85+second);
  assert.equal(api('leaderboard')[0].me,true);
});
test('reject invalid level results', () => {
  const api=setup(), a=attempt('a','1',1);
  assert.throws(() => api('attempt',{attempt:{...a, max_combo:99}}),/Inconsistent/);
  assert.equal(api('profile').attempts,0);
});
