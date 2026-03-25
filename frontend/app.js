const API_BASE_URL = (window.APP_CONFIG?.API_BASE_URL || "").replace(/\/$/, "");

const state = {
  selectedDate: new Date().toISOString().slice(0, 10),
  meta: null,
  session: null,
  dashboard: null,
  nutrition: null,
  workout: null,
  sleep: null,
  wellbeing: null,
};

const els = {
  selectedDate: document.getElementById("selectedDate"),
  refreshBtn: document.getElementById("refreshBtn"),
  statusBanner: document.getElementById("statusBanner"),
  authForms: document.getElementById("authForms"),
  appPanel: document.getElementById("appPanel"),
  sessionSummary: document.getElementById("sessionSummary"),
  sessionActions: document.getElementById("sessionActions"),
  loginForm: document.getElementById("loginForm"),
  registerForm: document.getElementById("registerForm"),
  mealSelect: document.getElementById("mealSelect"),
  foodSelect: document.getElementById("foodSelect"),
  customFoodFields: document.getElementById("customFoodFields"),
  nutritionForm: document.getElementById("nutritionForm"),
  nutritionList: document.getElementById("nutritionList"),
  muscleSelect: document.getElementById("muscleSelect"),
  exerciseSelect: document.getElementById("exerciseSelect"),
  strengthFields: document.getElementById("strengthFields"),
  cardioFields: document.getElementById("cardioFields"),
  inclineField: document.getElementById("inclineField"),
  workoutForm: document.getElementById("workoutForm"),
  workoutList: document.getElementById("workoutList"),
  workoutMeta: document.getElementById("workoutMeta"),
  sleepForm: document.getElementById("sleepForm"),
  deleteSleepBtn: document.getElementById("deleteSleepBtn"),
  sleepSummary: document.getElementById("sleepSummary"),
  wellbeingForm: document.getElementById("wellbeingForm"),
  otherActivityField: document.getElementById("otherActivityField"),
  wellbeingList: document.getElementById("wellbeingList"),
  netCalories: document.getElementById("netCalories"),
  netCaloriesCopy: document.getElementById("netCaloriesCopy"),
  healthScore: document.getElementById("healthScore"),
  healthReasons: document.getElementById("healthReasons"),
  gymCalories: document.getElementById("gymCalories"),
  gymDuration: document.getElementById("gymDuration"),
  nutritionTotals: document.getElementById("nutritionTotals"),
  macroTotals: document.getElementById("macroTotals"),
};

function showBanner(message, tone = "info") {
  els.statusBanner.textContent = message;
  els.statusBanner.className = `status-banner ${tone}`;
}

function hideBanner() {
  els.statusBanner.className = "status-banner hidden";
  els.statusBanner.textContent = "";
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const config = {
    method: options.method || "GET",
    credentials: "include",
    headers,
  };

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, config);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }

  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumber(value, digits = 0) {
  return Number(value || 0).toFixed(digits);
}

function listMarkup(items, emptyMessage, actions = () => "") {
  if (!items?.length) {
    return `<div class="list-item"><span>${emptyMessage}</span></div>`;
  }

  return items
    .map((item) => {
      const summary = item.summary || "";
      return `
        <div class="list-item">
          <div>
            <strong>${escapeHtml(item.title || "")}</strong>
            <span>${escapeHtml(summary)}</span>
          </div>
          <div>${actions(item)}</div>
        </div>
      `;
    })
    .join("");
}

function updateSessionView() {
  const authenticated = Boolean(state.session?.authenticated);
  els.authForms.classList.toggle("hidden", authenticated);
  els.appPanel.classList.toggle("hidden", !authenticated);

  if (authenticated) {
    const user = state.session.user;
    els.sessionSummary.innerHTML = `
      <div>
        <strong>${escapeHtml(user.name || user.email)}</strong>
        <small>${escapeHtml(user.email)} • ${escapeHtml(user.role)}</small>
      </div>
      <small>Connected to ${escapeHtml(API_BASE_URL)}</small>
    `;
    els.sessionActions.innerHTML = `<button id="logoutBtn" class="ghost-btn" type="button">Logout</button>`;
    document.getElementById("logoutBtn").addEventListener("click", handleLogout);
  } else {
    els.sessionSummary.innerHTML = `
      <div>
        <strong>Not signed in</strong>
        <small>Use the API-backed forms below to create an account or login.</small>
      </div>
      <small>${escapeHtml(API_BASE_URL)}</small>
    `;
    els.sessionActions.innerHTML = "";
  }
}

function populateNutritionOptions() {
  if (!state.meta?.food_catalog) return;

  const meals = Object.keys(state.meta.food_catalog);
  els.mealSelect.innerHTML = [`<option value="">Select meal</option>`, ...meals.map((meal) => `<option value="${escapeHtml(meal)}">${escapeHtml(meal)}</option>`)].join("");
  els.foodSelect.innerHTML = `<option value="">Select food</option>`;
}

function populateFoodOptions() {
  const meal = els.mealSelect.value;
  const foods = meal ? Object.keys(state.meta.food_catalog[meal]) : [];
  els.foodSelect.innerHTML = [
    `<option value="">Select food</option>`,
    ...foods.map((food) => `<option value="${escapeHtml(food)}">${escapeHtml(food)}</option>`),
    `<option value="OTHERS">Custom entry</option>`,
  ].join("");
}

function populateWorkoutOptions() {
  if (!state.meta?.exercise_options) return;
  const muscles = Object.keys(state.meta.exercise_options);
  els.muscleSelect.innerHTML = muscles
    .map((muscle) => `<option value="${escapeHtml(muscle)}">${escapeHtml(muscle)}</option>`)
    .join("");
  syncExerciseOptions();
}

function syncExerciseOptions() {
  const muscle = els.muscleSelect.value;
  const exercises = state.meta?.exercise_options?.[muscle] || [];
  els.exerciseSelect.innerHTML = exercises
    .map((exercise) => `<option value="${escapeHtml(exercise)}">${escapeHtml(exercise)}</option>`)
    .join("");
  updateWorkoutMode();
}

function updateWorkoutMode() {
  const exercise = els.exerciseSelect.value;
  const cardio = state.meta?.cardio_exercises?.includes(exercise);
  els.strengthFields.classList.toggle("hidden", cardio);
  els.cardioFields.classList.toggle("hidden", !cardio);
  els.inclineField.classList.toggle("hidden", exercise !== "Inclined Walking");
  document.getElementById("weightInput").disabled = cardio;
}

function updateWellbeingMode() {
  const activity = els.wellbeingForm.elements.activity.value;
  els.otherActivityField.classList.toggle("hidden", activity !== "OTHERS");
}

function renderDashboard() {
  const dashboard = state.dashboard;
  if (!dashboard) return;

  const net = dashboard.net_calories || 0;
  const score = dashboard.health_score || 0;
  const reasons = (dashboard.health_reasons || []).map((reason) => reason.message).join(" • ") || "No health reasons yet.";
  const nutrition = dashboard.nutrition || {};
  const gym = dashboard.gym || {};

  els.netCalories.textContent = `${formatNumber(net)} kcal`;
  els.netCaloriesCopy.textContent = net < 0 ? "Calorie deficit recorded." : "Calorie surplus recorded.";
  els.healthScore.textContent = `${score}/100`;
  els.healthReasons.textContent = reasons;
  els.gymCalories.textContent = `${formatNumber(gym.calories)} kcal`;
  els.gymDuration.textContent = `${formatNumber(gym.duration)} min`;
  els.nutritionTotals.textContent = `${formatNumber(nutrition.calories)} kcal`;
  els.macroTotals.textContent = `Protein ${formatNumber(nutrition.protein)}g • Fat ${formatNumber(nutrition.fat)}g • Sugar ${formatNumber(nutrition.sugar)}g`;
}

function renderNutrition() {
  const items = (state.nutrition?.logs || []).map((item) => ({
    ...item,
    title: `${item.meal} • ${item.food}`,
    summary: `${formatNumber(item.qty, 1)} serving • ${formatNumber(item.calories)} kcal • Protein ${formatNumber(item.protein, 1)}g`,
  }));
  els.nutritionList.innerHTML = listMarkup(items, "No nutrition entries for this date.", (item) => `<button class="delete-btn" type="button" data-action="delete-nutrition" data-id="${item.id}">Delete</button>`);
}

function renderWorkout() {
  const items = (state.workout?.logs || []).map((item) => {
    const isCardio = state.meta?.cardio_exercises?.includes(item.exercise);
    const summary = isCardio
      ? `${formatNumber(item.duration, 1)} min • ${formatNumber(item.speed, 1)} speed • ${formatNumber(item.calories)} kcal`
      : `${item.sets} x ${item.reps} • ${formatNumber(item.weight, 1)} kg • ${formatNumber(item.calories)} kcal`;
    return { ...item, title: `${item.muscle} • ${item.exercise}`, summary };
  });
  els.workoutList.innerHTML = listMarkup(items, "No workouts logged for this date.", (item) => `<button class="delete-btn" type="button" data-action="delete-workout" data-id="${item.id}">Delete</button>`);

  const streak = state.workout?.streak || 0;
  const last = state.workout?.last_workout;
  els.workoutMeta.textContent = last
    ? `Streak: ${streak} day(s). Last workout: ${last.exercise} on ${last.date}.`
    : "No previous workout found yet.";
}

function renderSleep() {
  const entry = state.sleep?.sleep;
  if (!entry) {
    els.sleepSummary.innerHTML = `<div class="list-item"><span>No sleep entry for this date.</span></div>`;
    els.sleepForm.reset();
    return;
  }

  els.sleepForm.elements.hours.value = entry.hours ?? "";
  els.sleepForm.elements.quality.value = entry.quality ?? "";
  els.sleepForm.elements.notes.value = entry.notes ?? "";
  els.sleepSummary.innerHTML = `
    <div class="list-item">
      <div>
        <strong>${formatNumber(entry.hours, 1)} hours</strong>
        <span>Quality ${entry.quality}/10 • ${escapeHtml(entry.notes || "No notes")}</span>
      </div>
    </div>
  `;
}

function renderWellbeing() {
  const items = (state.wellbeing?.logs || []).map((item) => ({
    ...item,
    title: item.activity,
    summary: `${item.minutes} minute(s) on ${item.date}`,
  }));
  els.wellbeingList.innerHTML = listMarkup(items, "No wellbeing activity for this date.", (item) => `<button class="delete-btn" type="button" data-action="delete-wellbeing" data-id="${item.id}">Delete</button>`);
}

async function refreshSession() {
  state.session = await api("/api/session");
  updateSessionView();
}

async function loadMeta() {
  state.meta = await api("/api/meta");
  populateNutritionOptions();
  populateWorkoutOptions();
}

async function loadAppData() {
  if (!state.session?.authenticated) return;
  showBanner("Loading dashboard and logs...", "info");
  const query = `?date=${encodeURIComponent(state.selectedDate)}`;
  const [dashboard, nutrition, workout, sleep, wellbeing] = await Promise.all([
    api(`/api/dashboard${query}`),
    api(`/api/nutrition${query}`),
    api(`/api/workout${query}`),
    api(`/api/sleep${query}`),
    api(`/api/wellbeing${query}`),
  ]);

  state.dashboard = dashboard;
  state.nutrition = nutrition;
  state.workout = workout;
  state.sleep = sleep;
  state.wellbeing = wellbeing;

  renderDashboard();
  renderNutrition();
  renderWorkout();
  renderSleep();
  renderWellbeing();
  showBanner("Data refreshed successfully.", "info");
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const payload = Object.fromEntries(formData.entries());
  await api("/api/login", { method: "POST", body: payload });
  await refreshSession();
  await loadAppData();
  showBanner("Signed in successfully.", "info");
}

async function handleRegister(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const payload = Object.fromEntries(formData.entries());
  await api("/api/register", { method: "POST", body: payload });
  await refreshSession();
  await loadAppData();
  showBanner("Account created successfully.", "info");
}

async function handleLogout() {
  await api("/api/logout", { method: "POST" });
  state.dashboard = null;
  state.nutrition = null;
  state.workout = null;
  state.sleep = null;
  state.wellbeing = null;
  await refreshSession();
  showBanner("Signed out.", "info");
}

async function handleNutritionSubmit(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  payload.date = state.selectedDate;
  await api("/api/nutrition", { method: "POST", body: payload });
  event.currentTarget.reset();
  populateNutritionOptions();
  await loadAppData();
}

async function handleWorkoutSubmit(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  payload.date = state.selectedDate;
  await api("/api/workout", { method: "POST", body: payload });
  await loadAppData();
}

async function handleSleepSubmit(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  payload.date = state.selectedDate;
  await api("/api/sleep", { method: "POST", body: payload });
  await loadAppData();
}

async function handleDeleteSleep() {
  await api("/api/sleep", { method: "DELETE", body: { date: state.selectedDate } });
  await loadAppData();
}

async function handleWellbeingSubmit(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  payload.date = state.selectedDate;
  await api("/api/wellbeing", { method: "POST", body: payload });
  await loadAppData();
}

async function handleListClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const { action, id } = button.dataset;
  if (action === "delete-nutrition") {
    await api(`/api/nutrition/${id}`, { method: "DELETE" });
  } else if (action === "delete-workout") {
    await api(`/api/workout/${id}`, { method: "DELETE" });
  } else if (action === "delete-wellbeing") {
    await api(`/api/wellbeing/${id}`, { method: "DELETE" });
  }

  await loadAppData();
}

async function initialize() {
  try {
    if (!API_BASE_URL) {
      throw new Error("Set window.APP_CONFIG.API_BASE_URL in frontend/config.js before deploying.");
    }

    els.selectedDate.value = state.selectedDate;
    await loadMeta();
    await refreshSession();
    if (state.session?.authenticated) {
      await loadAppData();
    } else {
      showBanner("Configure the backend URL in config.js, then sign in to start using the app.", "info");
    }
  } catch (error) {
    showBanner(error.message, "error");
  }
}

els.selectedDate.addEventListener("change", async (event) => {
  state.selectedDate = event.target.value;
  if (state.session?.authenticated) {
    try {
      await loadAppData();
    } catch (error) {
      showBanner(error.message, "error");
    }
  }
});

els.refreshBtn.addEventListener("click", async () => {
  try {
    hideBanner();
    await refreshSession();
    if (state.session?.authenticated) {
      await loadAppData();
    }
  } catch (error) {
    showBanner(error.message, "error");
  }
});

els.mealSelect.addEventListener("change", populateFoodOptions);
els.foodSelect.addEventListener("change", () => {
  els.customFoodFields.classList.toggle("hidden", els.foodSelect.value !== "OTHERS");
});
els.muscleSelect.addEventListener("change", syncExerciseOptions);
els.exerciseSelect.addEventListener("change", updateWorkoutMode);
els.wellbeingForm.elements.activity.addEventListener("change", updateWellbeingMode);
els.loginForm.addEventListener("submit", async (event) => {
  try {
    await handleLogin(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.registerForm.addEventListener("submit", async (event) => {
  try {
    await handleRegister(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.nutritionForm.addEventListener("submit", async (event) => {
  try {
    await handleNutritionSubmit(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.workoutForm.addEventListener("submit", async (event) => {
  try {
    await handleWorkoutSubmit(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.sleepForm.addEventListener("submit", async (event) => {
  try {
    await handleSleepSubmit(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.deleteSleepBtn.addEventListener("click", async () => {
  try {
    await handleDeleteSleep();
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.wellbeingForm.addEventListener("submit", async (event) => {
  try {
    await handleWellbeingSubmit(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});
els.nutritionList.addEventListener("click", handleListClick);
els.workoutList.addEventListener("click", handleListClick);
els.wellbeingList.addEventListener("click", handleListClick);

initialize();
