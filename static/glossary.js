/* Plain-language glossary with hover / tap / keyboard "explain" popovers.
 *
 * window.Glossary.apply(rootNode) scans the text under rootNode and wraps known
 * medical/trial terms in a small button. Hovering, tapping, or focusing a term
 * shows a plain-language definition. Definitions come from this file only (not
 * from external data), and terms are wrapped by rebuilding text nodes -- never
 * via innerHTML on page content -- so external trial text stays inert.
 */
(function () {
  "use strict";

  // Keys are lowercase; matching also accepts a trailing "s" (simple plurals).
  var GLOSSARY = {
    "randomized": "You're placed into a treatment group by chance (like a coin flip) so the groups can be compared fairly.",
    "randomization": "Assigning participants to treatment groups by chance, to keep the comparison fair.",
    "placebo": "A look-alike treatment with no active medicine, used for comparison. In cancer trials it's usually added to standard care, not given instead of it.",
    "double-blind": "Neither you nor your study doctor knows which treatment group you're in, which keeps the results fair.",
    "open-label": "Everyone knows which treatment you're getting; it isn't hidden.",
    "blinded": "Some people in the study don't know which treatment you're getting, to keep results fair.",
    "phase": "What stage of testing a treatment is in — from early safety (Phase 1) to comparing against standard care (Phase 3).",
    "arm": "One group of participants in a study. Different arms may receive different treatments.",
    "cohort": "A group of participants who are followed together in a study.",
    "inclusion criteria": "The requirements you must meet to be able to join a study.",
    "exclusion criteria": "The reasons someone would not be able to join a study.",
    "eligibility criteria": "The full list of requirements that decide who can join a study.",
    "intervention": "The treatment or approach being tested in the study.",
    "interventional": "A study where participants receive a treatment that is being tested.",
    "observational": "A study where researchers observe people without assigning a treatment.",
    "biomarker": "Something measured in your body (like a gene or protein) that can help guide treatment.",
    "her2-positive": "A breast cancer with extra HER2 protein, which certain drugs can target.",
    "metastatic": "Cancer that has spread from where it started to other parts of the body.",
    "adjuvant": "Treatment given after the main treatment (like surgery) to lower the chance the cancer returns.",
    "neoadjuvant": "Treatment given before the main treatment (like surgery), often to shrink the cancer first.",
    "overall survival": "How long people live after starting treatment — a common way to measure benefit.",
    "progression-free survival": "How long people live without their cancer getting worse.",
    "adverse event": "Any unwanted medical problem during a study; it may or may not be caused by the treatment.",
    "serious adverse event": "A severe side effect — for example, one needing hospital care.",
    "infusion": "Medicine given slowly into a vein, usually at a clinic over some time.",
    "intravenous": "Given into a vein (often shortened to IV).",
    "oral": "Taken by mouth, such as a pill or capsule.",
    "lesion": "An area of abnormal tissue, such as a tumor.",
    "remission": "A period when signs of the cancer have shrunk or disappeared.",
    "recurrence": "The cancer coming back after a period of improvement.",
    "relapse": "The cancer returning or worsening after a period of improvement.",
    "standard of care": "The usual, widely accepted treatment for your condition.",
    "efficacy": "How well a treatment works under study conditions.",
    "dose": "The amount of a treatment given at one time.",
    "cycle": "A repeating treatment period (for example, a 21-day cycle) that may mix treatment days and rest days.",
    "informed consent": "Learning what a study involves and agreeing, in writing, to take part.",
    "chemotherapy": "Drugs that kill or slow the growth of cancer cells.",
    "immunotherapy": "Treatment that helps your own immune system fight cancer.",
    "targeted therapy": "Drugs that attack specific features of cancer cells.",
    "neutropenia": "A low level of certain white blood cells, which raises the risk of infection.",
    "febrile neutropenia": "A fever together with a low white-blood-cell count — treated as an emergency.",
    "performance status": "A rating of how well you can carry out everyday activities.",
    "washout period": "A stretch of time off certain medicines before starting a study.",
    "quality of life": "How the treatment and illness affect your day-to-day well-being.",
    "time toxicity": "The time a treatment takes from your life — visits, travel, and hospital stays — not just its physical side effects.",
    "enrollment": "The number of participants a study plans to include."
  };

  // Build one case-insensitive regex, longest phrases first so they win.
  var terms = Object.keys(GLOSSARY).sort(function (a, b) { return b.length - a.length; });
  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  var RE = new RegExp("\\b(?:" + terms.map(esc).join("|") + ")s?\\b", "gi");

  function canonicalKey(matched) {
    var lc = matched.toLowerCase();
    if (GLOSSARY[lc]) return lc;
    if (lc.charAt(lc.length - 1) === "s" && GLOSSARY[lc.slice(0, -1)]) return lc.slice(0, -1);
    return null;
  }

  function makeTerm(display, def) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "term";
    btn.dataset.def = def;
    btn.appendChild(document.createTextNode(display));
    // Read out for screen readers without needing the popover.
    var sr = document.createElement("span");
    sr.className = "visually-hidden";
    sr.textContent = " (definition: " + def + ")";
    btn.appendChild(sr);
    return btn;
  }

  function replaceInTextNode(node) {
    var text = node.nodeValue;
    RE.lastIndex = 0;
    var frag = document.createDocumentFragment();
    var last = 0;
    var m;
    var replaced = false;
    while ((m = RE.exec(text))) {
      var key = canonicalKey(m[0]);
      if (!key) continue;
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      frag.appendChild(makeTerm(m[0], GLOSSARY[key]));
      last = m.index + m[0].length;
      replaced = true;
    }
    if (!replaced) return;
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }

  var SKIP = { A: 1, BUTTON: 1, SCRIPT: 1, STYLE: 1, TEXTAREA: 1 };

  function apply(root) {
    if (!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = node.parentNode;
        if (!p || SKIP[p.nodeName]) return NodeFilter.FILTER_REJECT;
        if (p.classList && p.classList.contains("term")) return NodeFilter.FILTER_REJECT;
        RE.lastIndex = 0;
        return RE.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var targets = [];
    var n;
    while ((n = walker.nextNode())) targets.push(n);
    targets.forEach(replaceInTextNode);
  }

  // ---- Shared popover (created once) ----
  var pop = null;
  var current = null;
  var pinned = false;

  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement("div");
    pop.id = "glossary-pop";
    pop.setAttribute("role", "tooltip");
    pop.hidden = true;
    document.body.appendChild(pop);
    return pop;
  }

  function show(termEl) {
    ensurePop();
    pop.textContent = termEl.dataset.def;
    pop.hidden = false;
    var r = termEl.getBoundingClientRect();
    var top = r.bottom + window.scrollY + 6;
    var left = r.left + window.scrollX;
    var maxLeft = window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 12;
    if (left > maxLeft) left = maxLeft;
    if (left < 8) left = 8;
    pop.style.top = top + "px";
    pop.style.left = left + "px";
    current = termEl;
  }

  function hide() {
    if (pop) pop.hidden = true;
    current = null;
  }

  function initEvents() {
    document.addEventListener("mouseover", function (e) {
      var t = e.target.closest && e.target.closest(".term");
      if (t && !pinned) show(t);
    });
    document.addEventListener("mouseout", function (e) {
      var t = e.target.closest && e.target.closest(".term");
      if (t && !pinned) hide();
    });
    document.addEventListener("focusin", function (e) {
      var t = e.target.closest && e.target.closest(".term");
      if (t) show(t);
    });
    document.addEventListener("focusout", function () {
      if (!pinned) hide();
    });
    document.addEventListener("click", function (e) {
      var t = e.target.closest && e.target.closest(".term");
      if (t) {
        e.preventDefault();
        if (pinned && current === t) { pinned = false; hide(); }
        else { pinned = true; show(t); }
      } else if (pinned) {
        pinned = false;
        hide();
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { pinned = false; hide(); }
    });
    window.addEventListener("resize", hide);
  }

  initEvents();
  window.Glossary = { apply: apply };
})();
