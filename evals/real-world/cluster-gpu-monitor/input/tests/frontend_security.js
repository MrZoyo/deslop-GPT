"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const componentsSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "components.js"),
  "utf8",
);
const rankingSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "ranking.js"),
  "utf8",
);
const appSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "app.js"),
  "utf8",
);
const overviewSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "overview.js"),
  "utf8",
);
const clusterSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "cluster.js"),
  "utf8",
);
const hostSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "host.js"),
  "utf8",
);
const i18nSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "i18n.js"),
  "utf8",
);
const echarts = require(path.join(__dirname, "..", "web", "vendor", "echarts.min.js"));

const context = { window: {} };
vm.createContext(context);
vm.runInContext(componentsSource, context);
vm.runInContext(i18nSource, context);

assert.equal(
  context.window.UI.escapeHtml(`<img src=x onerror="alert('x')"> &`),
  "&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt; &amp;",
);
assert.equal(context.window.UI.escapeHtml(null), "");
assert.match(rankingSource, /escapeHtml\(x\.name\)/);
assert.doesNotMatch(rankingSource, /\$\{x\.name\}/);
assert.doesNotMatch(appSource, /\$\{e\.message\}/);
assert.equal(echarts.version, "6.1.0");

const i18n = context.window.I18n;
assert.equal(i18n.localize("legacy", "fr"), "legacy");
assert.equal(i18n.localize({ zh: "中文", en: "English" }, "en"), "English");
assert.equal(i18n.localize({ zh: "中文", en: "English" }, "fr"), "中文");
assert.equal(i18n.localize({ en: "English", zh: "中文" }, "fr"), "English");
assert.equal(i18n.localize({ en: "Only translation" }, "fr"), "Only translation");
assert.equal(i18n.localize({ zh: "简体" }, "zh-CN"), "简体");
assert.equal(i18n.localize({ "zh-CN": "简体" }, "zh"), "简体");
assert.equal(i18n.localize(null, "zh"), "");
assert.match(componentsSource, /I18n\.localize\(b\.text_i18n \?\? b\.text\)/);
assert.match(componentsSource, /I18n\.localize\(b\.tooltip_i18n \?\? b\.tooltip\)/);
assert.match(overviewSource, /I18n\.localize\(group\.description_i18n \?\? group\.description\)/);
assert.match(overviewSource, /I18n\.localize\(c\.note_i18n \?\? c\.note\)/);
assert.match(overviewSource, /I18n\.localize\(h\.note_i18n \?\? h\.note\)/);
assert.match(clusterSource, /I18n\.localize\(c\.note_i18n \?\? c\.note\)/);
assert.match(hostSource, /I18n\.localize\(host\.note_i18n \?\? host\.note\)/);
