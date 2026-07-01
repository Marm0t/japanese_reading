const LEVELS = [1, 2, 3, 4];
const COURSES = ["hiragana", "katakana"];
const EXAM_LENGTH = 10;
const RECENT_COOLDOWN = 20;
const LEVEL_ICONS = { 1: "🥚", 2: "🐣", 3: "🐓", 4: "🐉" };
const STORAGE_KEY = "yomu:v1";
const EMPTY_STATE = {
  name: "", mode: "learning", course: "hiragana", level: null, showSpaces: true,
  total: 0, correct: 0, currentStreak: 0, bestStreak: 0,
  totalResponseMs: 0, timedAnswers: 0, daily: {}, exams: []
};

const qs = (selector) => document.querySelector(selector);
const elements = {
  form: qs("#answerForm"), input: qs("#answerInput"), button: qs("#checkButton"), feedback: qs("#feedback"),
  showAnswer: qs("#showAnswer"), question: qs("#questionText"), round: qs("#roundCount"), timer: qs("#questionTimer"),
  modeLabel: qs("#modeLabel"), learningMode: qs("#learningMode"), examMode: qs("#examMode"),
  practiceContent: qs("#practiceContent"), examResult: qs("#examResult"), examScore: qs("#examScore"), examSummary: qs("#examSummary"),
  restartExam: qs("#restartExam"), returnLearning: qs("#returnLearning"), difficultyScreen: qs("#difficultyScreen"), trainerScreen: qs("#trainerScreen"),
  difficultyButtons: document.querySelectorAll(".difficulty-card"), menu: qs("#menuDialog"), openMenu: qs("#openMenu"), closeMenu: qs("#closeMenu"),
  nameForm: qs("#nameForm"), nameInput: qs("#nameInput"), editName: qs("#editName"), profileName: qs("#profileName"),
  avatar: qs("#avatarLetter"), menuAvatar: qs("#menuAvatar"), currentLevel: qs("#currentLevel"),
  levelButtons: document.querySelectorAll("#levelOptions button"), courseButtons: document.querySelectorAll("#courseOptions button"), spaceToggle: qs("#spaceToggle"),
  correct: qs("#correctStat"), accuracy: qs("#accuracyStat"), streak: qs("#streakStat"), averageTime: qs("#averageTimeStat"), allTime: qs("#allTimeStat"), reset: qs("#resetStats")
};

let state = loadState();
const FUNNY_NAMES = ["Sleepy Tanuki", "Mochi Ninja", "Capybara Sensei", "Rice Samurai", "Udon Fox", "Serious Penguin"];
if (!state.name || /[\u0400-\u04ff]/i.test(state.name)) state.name = FUNNY_NAMES[Math.floor(Math.random() * FUNNY_NAMES.length)];
let mode = state.mode === "exam" ? "exam" : "learning";
let course = COURSES.includes(state.course) ? state.course : "hiragana";
let level = LEVELS.includes(Number(state.level)) ? Number(state.level) : null;
let questions = [];
let current = null;
let recentIds = [];
let answered = false;
let round = 0;
let questionStartedAt = Date.now();
let examSession = null;
let loadToken = 0;
saveState();

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return { ...EMPTY_STATE, ...saved, daily: saved?.daily || {}, exams: saved?.exams || [] };
  } catch { return { ...EMPTY_STATE, daily: {}, exams: [] }; }
}
function saveState() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
function localDateKey() {
  const now = new Date();
  return new Date(now - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}
function todayStats() { return state.daily[localDateKey()] || { total: 0, correct: 0, totalResponseMs: 0, timedAnswers: 0 }; }
function elapsedMs() { return Math.max(0, Date.now() - questionStartedAt); }
function formatSeconds(ms) { return `${(ms / 1000).toFixed(1)} s`; }
function normalize(value) {
  return value.trim().toLowerCase()
    .replace(/[\s\-–—_.’']/g, "")
    .replace(/[āâ]/g, "aa").replace(/[īî]/g, "ii").replace(/[ūû]/g, "uu")
    .replace(/[ēê]/g, "ee").replace(/ō/g, "ou").replace(/ô/g, "ou");
}
function acceptedRomaji(value) {
  const normalized = normalize(value);
  const answers = [normalized];
  if (/(?:desu|masu)$/.test(normalized)) answers.push(normalized.slice(0, -1));
  return answers;
}
function answerLines(item, includeKana = false) {
  const lines = [item.romaji[0]];
  if (includeKana) lines.push(item.kana);
  if (item.kanji) lines.push(item.kanji);
  if (item.translation) lines.push(item.translation);
  return lines.join("\n");
}
function renderQuestion() {
  if (!current) return;
  elements.question.replaceChildren();
  current.kana.split(/\s+/).forEach((word) => {
    const span = document.createElement("span");
    span.className = `question-word${state.showSpaces ? " with-space" : ""}`;
    span.textContent = word;
    elements.question.append(span);
  });
}

async function loadQuestions() {
  if (!level) return;
  const token = ++loadToken;
  elements.question.textContent = "…";
  elements.input.disabled = true;
  elements.button.disabled = true;
  try {
    const response = await fetch(`data/${course}-${String(level).padStart(2, "0")}.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (token !== loadToken) return;
    questions = data;
    recentIds = [];
    elements.input.disabled = false;
    elements.button.disabled = false;
    setMode("learning");
  } catch (error) {
    elements.question.textContent = "読み込みエラー";
    elements.feedback.textContent = "Could not load the reading database. Run the app through server.py.";
    elements.feedback.className = "feedback wrong";
    console.error(error);
  }
}

function randomQuestion(pool = questions) {
  const available = pool.filter((item) => !recentIds.includes(item.id));
  const source = available.length ? available : pool;
  return source[Math.floor(Math.random() * source.length)];
}
function chooseQuestion() {
  if (mode === "exam" && examSession?.answers >= EXAM_LENGTH) return showExamResult();
  const pool = mode === "exam" ? questions.filter((item) => !examSession.used.has(item.id)) : questions;
  current = randomQuestion(pool);
  if (!current) return;
  if (mode === "exam") examSession.used.add(current.id);
  else {
    recentIds.push(current.id);
    if (recentIds.length > Math.min(RECENT_COOLDOWN, questions.length - 1)) recentIds.shift();
  }
  round += 1;
  answered = false;
  questionStartedAt = Date.now();
  elements.practiceContent.hidden = false;
  elements.examResult.hidden = true;
  renderQuestion();
  elements.question.classList.toggle("is-sentence", level === 4);
  elements.round.textContent = mode === "exam" ? `${round} / ${EXAM_LENGTH}` : `Question ${round}`;
  elements.input.value = "";
  elements.input.className = "";
  elements.input.readOnly = false;
  elements.button.textContent = "Check";
  elements.showAnswer.hidden = mode === "exam";
  elements.showAnswer.disabled = false;
  elements.feedback.className = "feedback";
  elements.feedback.textContent = mode === "exam" ? "One attempt · no hints" : "Read the kana and type it in romaji";
  updateTimer();
  elements.input.focus({ preventScroll: true });
}
function updateTimer() { if (!answered && !elements.practiceContent.hidden) elements.timer.textContent = formatSeconds(elapsedMs()); }

function submitAnswer(event) {
  event.preventDefault();
  if (answered) return chooseQuestion();
  const answer = normalize(elements.input.value);
  if (!answer) {
    elements.feedback.textContent = "Enter an answer first";
    elements.feedback.className = "feedback wrong";
    return elements.input.focus();
  }
  const responseMs = elapsedMs();
  const isCorrect = current.romaji.some((valid) => acceptedRomaji(valid).includes(answer));
  recordAttempt(isCorrect, responseMs);
  elements.input.classList.remove("is-correct", "is-wrong");
  if (isCorrect) {
    const details = [current.kanji, current.translation].filter(Boolean);
    elements.feedback.textContent = `Correct in ${formatSeconds(responseMs)}!${details.length ? `\n${details.join("\n")}` : ""}`;
    elements.feedback.className = "feedback correct answer-shown";
    elements.input.classList.add("is-correct");
    finishQuestion();
  } else if (mode === "learning") {
    elements.feedback.textContent = "Not quite. Fix your answer and try again";
    elements.feedback.className = "feedback wrong";
    elements.input.classList.add("is-wrong");
    elements.input.select();
    questionStartedAt = Date.now();
  } else {
    elements.feedback.textContent = `Incorrect.\n${answerLines(current)}`;
    elements.feedback.className = "feedback wrong answer-shown";
    elements.input.classList.add("is-wrong");
    finishQuestion();
  }
  if (mode === "exam") {
    examSession.answers += 1;
    examSession.correct += isCorrect ? 1 : 0;
    examSession.totalMs += responseMs;
    if (examSession.answers === EXAM_LENGTH) elements.button.textContent = "Results";
  }
  saveState(); renderStats();
}
function recordAttempt(isCorrect, responseMs) {
  const key = localDateKey();
  state.daily[key] ||= { total: 0, correct: 0, totalResponseMs: 0, timedAnswers: 0 };
  state.total += 1; state.totalResponseMs += responseMs; state.timedAnswers += 1;
  state.daily[key].total += 1; state.daily[key].totalResponseMs += responseMs; state.daily[key].timedAnswers += 1;
  if (isCorrect) {
    state.correct += 1; state.daily[key].correct += 1; state.currentStreak += 1; state.bestStreak = Math.max(state.bestStreak, state.currentStreak);
  } else state.currentStreak = 0;
}
function finishQuestion() { answered = true; elements.button.textContent = "Next"; elements.showAnswer.disabled = true; elements.input.readOnly = true; elements.button.focus({ preventScroll: true }); }
function revealAnswer() {
  if (answered || mode === "exam") return;
  recordAttempt(false, elapsedMs());
  elements.feedback.textContent = `Answer:\n${answerLines(current)}`;
  elements.feedback.className = "feedback correct answer-shown";
  finishQuestion(); saveState(); renderStats();
}
function setMode(nextMode) {
  mode = nextMode; state.mode = mode; round = 0; recentIds = [];
  examSession = mode === "exam" ? { answers: 0, correct: 0, totalMs: 0, used: new Set(), completed: false } : null;
  elements.learningMode.classList.toggle("active", mode === "learning");
  elements.examMode.classList.toggle("active", mode === "exam");
  elements.learningMode.setAttribute("aria-pressed", String(mode === "learning"));
  elements.examMode.setAttribute("aria-pressed", String(mode === "exam"));
  elements.modeLabel.textContent = mode === "exam" ? "Exam" : "Learn";
  elements.timer.hidden = mode !== "exam";
  saveState(); chooseQuestion();
}
function showExamResult() {
  if (!examSession.completed) {
    state.exams.push({ date: new Date().toISOString(), course, level, correct: examSession.correct, total: EXAM_LENGTH, totalMs: examSession.totalMs });
    state.exams = state.exams.slice(-20); examSession.completed = true; saveState();
  }
  answered = true; elements.practiceContent.hidden = true; elements.examResult.hidden = false;
  elements.round.textContent = "Done"; elements.timer.textContent = formatSeconds(examSession.totalMs);
  elements.examScore.textContent = `${examSession.correct}/${EXAM_LENGTH}`;
  elements.examSummary.textContent = `Average time: ${formatSeconds(examSession.totalMs / EXAM_LENGTH)}`;
  elements.restartExam.focus({ preventScroll: true });
}
function renderStats() {
  const today = todayStats();
  elements.correct.textContent = today.correct;
  elements.accuracy.textContent = today.total ? `${Math.round(today.correct / today.total * 100)}%` : "—";
  elements.streak.textContent = state.currentStreak;
  elements.averageTime.textContent = today.timedAnswers ? formatSeconds(today.totalResponseMs / today.timedAnswers) : "—";
  elements.allTime.textContent = `Total attempts: ${state.total} · best streak: ${state.bestStreak} · exams: ${state.exams.length}`;
  elements.profileName.textContent = state.name;
  const initial = state.name.trim().charAt(0).toLocaleUpperCase("en-US");
  elements.avatar.textContent = LEVEL_ICONS[level] || "☰"; elements.menuAvatar.textContent = initial;
  elements.currentLevel.textContent = level ? `Level ${level}` : "Not selected";
  elements.spaceToggle.checked = state.showSpaces;
  elements.levelButtons.forEach((button) => button.classList.toggle("active", Number(button.dataset.level) === level));
  elements.courseButtons.forEach((button) => button.classList.toggle("active", button.dataset.course === course));
}
function selectLevel(value) {
  const next = Number(value); if (!LEVELS.includes(next)) return;
  level = next; state.level = level; state.currentStreak = 0;
  elements.difficultyScreen.hidden = true; elements.trainerScreen.hidden = false;
  if (elements.menu.open) elements.menu.close();
  renderStats(); saveState(); loadQuestions();
}
function selectCourse(value) {
  if (!COURSES.includes(value) || value === course) return;
  course = value; state.course = course; state.currentStreak = 0;
  renderStats(); saveState(); if (level) loadQuestions();
}
function keepAnswerFormVisible() { if (document.activeElement === elements.input) setTimeout(() => elements.form.scrollIntoView({ block: "center", behavior: "smooth" }), 180); }

elements.form.addEventListener("submit", submitAnswer);
elements.input.addEventListener("focus", keepAnswerFormVisible);
if (window.visualViewport) window.visualViewport.addEventListener("resize", keepAnswerFormVisible);
elements.showAnswer.addEventListener("click", revealAnswer);
elements.learningMode.addEventListener("click", () => setMode("learning"));
elements.examMode.addEventListener("click", () => setMode("exam"));
elements.restartExam.addEventListener("click", () => setMode("exam"));
elements.returnLearning.addEventListener("click", () => setMode("learning"));
elements.difficultyButtons.forEach((button) => button.addEventListener("click", () => selectLevel(button.dataset.level)));
elements.levelButtons.forEach((button) => button.addEventListener("click", () => selectLevel(button.dataset.level)));
elements.courseButtons.forEach((button) => button.addEventListener("click", () => selectCourse(button.dataset.course)));
elements.spaceToggle.addEventListener("change", () => { state.showSpaces = elements.spaceToggle.checked; saveState(); renderQuestion(); });
elements.openMenu.addEventListener("click", () => { renderStats(); elements.nameForm.hidden = true; elements.menu.showModal(); });
elements.closeMenu.addEventListener("click", () => elements.menu.close());
elements.menu.addEventListener("click", (event) => { if (event.target === elements.menu) elements.menu.close(); });
elements.editName.addEventListener("click", () => { elements.nameInput.value = state.name; elements.nameForm.hidden = false; elements.nameInput.focus(); });
elements.nameForm.addEventListener("submit", (event) => { event.preventDefault(); state.name = elements.nameInput.value.trim() || FUNNY_NAMES[Math.floor(Math.random() * FUNNY_NAMES.length)]; saveState(); renderStats(); elements.nameForm.hidden = true; });
elements.reset.addEventListener("click", () => {
  if (!confirm("Reset all statistics? Your name and settings will be kept.")) return;
  state = { ...EMPTY_STATE, name: state.name, mode, course, level, showSpaces: state.showSpaces, daily: {}, exams: [] };
  saveState(); renderStats();
});

renderStats();
if (level === null) { elements.difficultyScreen.hidden = false; elements.trainerScreen.hidden = true; }
else { elements.difficultyScreen.hidden = true; elements.trainerScreen.hidden = false; loadQuestions(); }
setInterval(updateTimer, 200);
