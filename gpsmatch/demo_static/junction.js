"use strict";

const byId = id => document.getElementById(id);
const svgNS = "http://www.w3.org/2000/svg";
const color = { route: "#235cbd", gps: "#ab4960", estimate: "#006353", truth: "#442c87", nearest: "#935907" };
const instructions = {
  stay: "Continue on the main road",
  exit: "Take the service-road exit",
  uncertain: "Road position uncertain",
  waiting: "Waiting for the junction",
  passed: "Junction passed",
};
const reasons = {
  stay: "Recent readings support the main-road approach.",
  exit: "Recent readings support the main-road approach.",
  uncertain: "Direction withheld until the main-road estimate is stable.",
  waiting: "Directions appear 20–100 m before the fork.",
  passed: "",
};

let replay;
let cursor = 0;
let furthest = 0;
let timer;
let request;
let projection;
let chartWidth = 760;

function svg(parent, tag, attrs, label) {
  const el = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (label) el.textContent = label;
  parent.append(el);
  return el;
}

function percent(value) {
  return value == null ? "Unavailable" : `${(100 * value).toFixed(1)}%`;
}

function positionOnMap([x, y]) {
  const { dx, dy, fx, fy } = projection;
  const along = (x - fx) * dx + (y - fy) * dy;
  const across = (y - fy) * dx - (x - fx) * dy;
  return [389 + 2.55 * along, 147 - 2.55 * across];
}

function line(parent, a, b, stroke, width, extra = {}) {
  svg(parent, "line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke, "stroke-width": width,
    "stroke-linecap": "round", ...extra });
}

function trail(parent, points, stroke, width, opacity = 1, extra = {}) {
  if (points.length < 2) return;
  svg(parent, "polyline", { points: points.map(p => p.join(",")).join(" "), fill: "none",
    stroke, "stroke-width": width, opacity, "stroke-linejoin": "round", "stroke-linecap": "round", ...extra });
}

function roadLabel(map, group, x, offset) {
  const spans = replay.segments.filter(segment => segment.road === group)
    .map(segment => [positionOnMap(segment.a), positionOnMap(segment.b)]);
  const segment = spans.find(([a, b]) => x >= Math.min(a[0], b[0]) && x <= Math.max(a[0], b[0]));
  if (!segment) return;
  const [a, b] = segment;
  const y = a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0]);
  svg(map, "text", { x, y: y + offset, "font-size": 15 }, group === "main" ? "MAIN ROAD" : "SERVICE ROAD");
}

function drawMap(frame) {
  const map = byId("map");
  map.replaceChildren();
  for (const segment of replay.segments) {
    const a = positionOnMap(segment.a);
    const b = positionOnMap(segment.b);
    line(map, a, b, "#bdcbc6", segment.road === "main" ? 19 : 11);
    line(map, a, b, "#fdfdf9", segment.road === "main" ? 14 : 7);
  }
  trail(map, replay.planned_path.map(positionOnMap), color.route, 4, .8);
  const [forkX, forkY] = positionOnMap(replay.fork);
  svg(map, "circle", { cx: forkX, cy: forkY, r: 11, fill: "none", stroke: "#596c71", "stroke-dasharray": "2 3" });
  line(map, [forkX + 5, forkY - 9], [forkX + 19, forkY - 44], "#596c71", 1);
  svg(map, "text", { x: forkX + 22, y: forkY - 46, "font-size": 15 }, "EXIT CONNECTOR");
  roadLabel(map, "main", 555, 32);
  roadLabel(map, "service", 555, -17);
  svg(map, "text", { x: 33, y: 45, "font-size": 15 }, "APPROACH →");

  const history = replay.frames.slice(0, cursor + 1);
  trail(map, history.map(f => positionOnMap(f.gps)), color.gps, 2, .6, { "stroke-dasharray": "2 5" });
  if (byId("truth").checked) trail(map, history.map(f => positionOnMap(f.truth_xy)), color.truth, 2);
  const [gx, gy] = positionOnMap(frame.gps);
  svg(map, "circle", { id: "gps-point", cx: gx, cy: gy, r: 6, fill: color.gps, stroke: "white", "stroke-width": 1.4 });
  if (frame.burst) svg(map, "circle", { cx: gx, cy: gy, r: 11, fill: "none", stroke: color.gps, "stroke-dasharray": "3 3" });
  if (frame.estimated_xy) {
    const [x, y] = positionOnMap(frame.estimated_xy);
    svg(map, "circle", { id: "estimated-point", cx: x, cy: y, r: 8, fill: "none", stroke: color.estimate, "stroke-width": 3 });
  }
  if (byId("truth").checked) {
    const [x, y] = positionOnMap(frame.truth_xy);
    svg(map, "circle", { id: "truth-point", cx: x, cy: y, r: 14, fill: "none", stroke: color.truth, "stroke-width": 2 });
  }
  if (byId("nearest").checked && frame.nearest_xy) {
    const [x, y] = positionOnMap(frame.nearest_xy);
    svg(map, "rect", { id: "nearest-point", x: x-11, y: y-11, width: 22, height: 22, fill: "none",
      stroke: color.nearest, "stroke-width": 2, transform: `rotate(45 ${x} ${y})` });
  }
  if (byId("truth").checked) svg(map, "text", { x: 33, y: 234, style: `fill:${color.truth}` }, "○ Ground truth");
  if (byId("nearest").checked) svg(map, "text", { x: 33, y: 257, style: `fill:${color.nearest}` }, "◇ Nearest road");
}

function chartX(index) {
  return 45 + index * (chartWidth - 65) / (replay.frames.length - 1);
}

function drawTimeline() {
  const chart = byId("confidence");
  const y = value => 92 - 70 * value;
  chartWidth = chart.clientWidth;
  chart.setAttribute("viewBox", `0 0 ${chartWidth} 124`);
  const right = chartX(replay.frames.length - 1);
  chart.replaceChildren();
  const seen = replay.frames.slice(0, furthest + 1);
  const burst = seen.filter(frame => frame.burst);
  if (burst.length) {
    const left = chartX(burst[0].t) - 7;
    svg(chart, "rect", { x: left, y: 14, width: chartX(burst.at(-1).t) - left + 7, height: 78, fill: "#fae7cf" });
  }
  for (const tick of [0, .5, 1]) {
    line(chart, [45, y(tick)], [right, y(tick)], "#dbe3e3", 1);
    svg(chart, "text", { x: 39, y: y(tick) + 4, "text-anchor": "end" }, `${100 * tick}%`);
  }
  const threshold = y(replay.threshold);
  line(chart, [45, threshold], [right, threshold], "#6e7c82", 1, { "stroke-dasharray": "5 5" });
  line(chart, [chartX(cursor), 18], [chartX(cursor), 96], "#415969", 1);
  let points = [];
  for (const frame of seen) {
    if (frame.confidence == null) {
      trail(chart, points, color.estimate, 2);
      points = [];
    } else {
      points.push([chartX(frame.t), y(frame.main_confidence)]);
    }
  }
  trail(chart, points, color.estimate, 2);
  for (const frame of seen) {
    if (frame.confidence == null) continue;
    const cx = chartX(frame.t);
    const cy = y(frame.main_confidence);
    svg(chart, "circle", { cx, cy, r: frame.t === cursor ? 5 : 2.6, fill: color.estimate });
    if (frame.prompt_started) {
      svg(chart, "circle", { cx, cy, r: 7, fill: "none", stroke: color.route, "stroke-width": 2 });
    }
  }
  const end = replay.frames.at(-1).t;
  for (let t = 0; t <= end; t += 5) {
    svg(chart, "text", { x: chartX(t), y: 114, "text-anchor": "middle" }, `${t}s`);
  }
}

function render() {
  const frame = replay.frames[cursor];
  const last = replay.frames.length - 1;
  const name = road => replay.road_names[road] || "Unmatched";
  const summary = replay.summary;
  byId("status").dataset.status = frame.status;
  byId("instruction").textContent = instructions[frame.status];
  byId("reason").textContent = reasons[frame.status];
  byId("road").textContent = name(frame.road);
  byId("maneuver").textContent = instructions[replay.maneuver];
  byId("score").textContent = percent(frame.confidence);
  byId("scrub").value = cursor;
  byId("time").textContent = `${frame.t} / ${last} s`;
  byId("step").disabled = cursor === last;
  byId("sample").textContent = `${frame.t}s · ${name(frame.road)} · ${percent(frame.confidence)} confidence`
    + (frame.burst ? " · GPS burst" : "")
    + (byId("truth").checked ? ` · True road: ${name(frame.truth_road)}` : "")
    + (byId("nearest").checked ? ` · Nearest: ${name(frame.nearest_road)}` : "");
  byId("summary").hidden = furthest !== last;
  byId("summary-note").textContent = furthest === last ? "Road estimates within 100 m of the fork." : "Available at the end of the replay.";
  const wrong = (count, unmatched) => `${count} / ${summary.near_fork_samples}${unmatched ? ` (${unmatched} unmatched)` : ""}`;
  byId("hmm-wrong").textContent = wrong(summary.wrong_estimates, summary.unmatched);
  byId("nearest-wrong").textContent = wrong(summary.nearest_wrong, summary.nearest_unmatched);
  byId("uncertain").textContent = `${summary.uncertain_seconds} s`;
  byId("lead").textContent = summary.prompt_lead_seconds == null ? "No timely prompt" : `${summary.prompt_lead_seconds.toFixed(1)} s before fork`;
  drawMap(frame);
  drawTimeline();
}

function pause() {
  clearInterval(timer);
  timer = undefined;
  byId("play").textContent = "Play";
}

function goTo(index) {
  cursor = Math.min(replay.frames.length - 1, Math.max(0, index));
  furthest = Math.max(cursor, furthest);
  render();
  if (cursor === replay.frames.length - 1) pause();
}

async function load() {
  pause();
  request?.abort();
  request = new AbortController();
  const { signal } = request;
  replay = undefined;
  for (const id of ["play", "step", "restart", "scrub", "truth", "nearest"]) byId(id).disabled = true;
  for (const id of ["map", "confidence", "sample"]) byId(id).replaceChildren();
  byId("summary").hidden = true;
  byId("summary-note").textContent = "Available at the end of the replay.";
  byId("time").textContent = "0 / 0 s";
  byId("status").dataset.status = "waiting";
  byId("instruction").textContent = "Waiting for replay";
  for (const id of ["road", "maneuver", "score"]) byId(id).textContent = "—";
  byId("reason").textContent = "";
  byId("load-status").textContent = "Loading replay…";
  try {
    const response = await fetch(`/api/junction/replay?scenario=${encodeURIComponent(byId("scenario").value)}`, { signal });
    if (!response.ok) throw new Error("Request failed");
    const data = await response.json();
    if (signal.aborted) return;
    replay = data;
    const [fx, fy] = replay.fork;
    const [sx, sy] = replay.planned_path[0];
    const length = Math.hypot(fx - sx, fy - sy);
    projection = { fx, fy, dx: (fx - sx) / length, dy: (fy - sy) / length };
    byId("location").textContent = replay.name;
    byId("scrub").max = replay.frames.length - 1;
    byId("load-status").textContent = "";
    for (const id of ["play", "step", "restart", "scrub", "truth", "nearest"]) byId(id).disabled = false;
    furthest = 0;
    goTo(0);
  } catch {
    if (!signal.aborted) byId("load-status").textContent = "Could not load the replay. Switch presets to retry.";
  }
}

byId("scenario").addEventListener("change", load);
byId("play").addEventListener("click", () => {
  if (timer !== undefined) return pause();
  if (cursor === replay.frames.length - 1) {
    furthest = 0;
    goTo(0);
  }
  byId("play").textContent = "Pause";
  timer = setInterval(() => goTo(cursor + 1), 1000);
});
byId("step").addEventListener("click", () => { pause(); goTo(cursor + 1); });
byId("restart").addEventListener("click", () => { pause(); furthest = 0; goTo(0); });
byId("scrub").addEventListener("input", event => { pause(); goTo(Number(event.target.value)); });
for (const id of ["nearest", "truth"]) byId(id).addEventListener("change", render);
byId("confidence").addEventListener("click", event => {
  if (!replay) return;
  const bounds = byId("confidence").getBoundingClientRect();
  const x = event.clientX - bounds.left;
  pause();
  goTo(Math.round((x - 45) / (chartWidth - 65) * (replay.frames.length - 1)));
});
window.addEventListener("resize", () => { if (replay) drawTimeline(); });
load();
