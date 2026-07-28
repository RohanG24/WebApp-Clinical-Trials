(function () {
  "use strict";

  var form = document.getElementById("find-form");
  var button = document.getElementById("find-btn");
  var statusEl = document.getElementById("status");
  var resultsEl = document.getElementById("results");
  var placeholderEl = document.getElementById("placeholder");
  var skeletonEl = document.getElementById("find-skeleton");

  var LEVEL_CLASS = {
    Light: "level-light",
    Moderate: "level-moderate",
    Intensive: "level-intensive",
    Unknown: "level-unknown"
  };

  var hasSearched = false;

  function currentParams() {
    return {
      condition: document.getElementById("condition").value.trim(),
      location: document.getElementById("location").value.trim(),
      max_time: document.getElementById("max_time").value
    };
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!currentParams().condition) return;
    runSearch(currentParams());
  });

  // Changing the time filter re-runs the search immediately once one has run.
  document.getElementById("max_time").addEventListener("change", function () {
    if (hasSearched && currentParams().condition) runSearch(currentParams());
  });

  function runSearch(params) {
    setLoading(true);
    setStatus("", false);
    placeholderEl.hidden = true;
    resultsEl.hidden = true;
    resultsEl.innerHTML = "";
    skeletonEl.hidden = false;

    var qs = new URLSearchParams(params).toString();
    fetch("/api/search?" + qs)
      .then(function (r) {
        return r.json().then(function (body) { return { ok: r.ok, body: body }; });
      })
      .then(function (payload) {
        skeletonEl.hidden = true;
        if (!payload.ok) {
          setStatus(payload.body.error || "Something went wrong.", true);
          placeholderEl.hidden = false;
          return;
        }
        hasSearched = true;
        render(payload.body);
      })
      .catch(function () {
        skeletonEl.hidden = true;
        placeholderEl.hidden = false;
        setStatus("Could not reach the server. Please try again.", true);
      })
      .finally(function () { setLoading(false); });
  }

  function render(data) {
    resultsEl.innerHTML = "";

    var results = data.results || [];
    var summary = document.createElement("p");
    summary.className = "results-count";
    if (!results.length) {
      summary.textContent = "No recruiting trials matched. Try a broader condition or removing the location or time filter.";
      resultsEl.appendChild(summary);
      resultsEl.hidden = false;
      return;
    }
    var total = data.total_matching;
    summary.textContent = "Showing " + results.length +
      (typeof total === "number" && total > results.length ? " of " + total + " matching" : "") +
      " recruiting trials, lightest time commitment first.";
    resultsEl.appendChild(summary);

    results.forEach(function (r) { resultsEl.appendChild(renderCard(r)); });
    if (window.Glossary) window.Glossary.apply(resultsEl);
    resultsEl.hidden = false;
  }

  function renderCard(r) {
    var card = document.createElement("article");
    card.className = "trial-card";

    // Time-commitment badge
    var time = r.time || {};
    var badge = document.createElement("div");
    badge.className = "level-badge " + (LEVEL_CLASS[time.level] || "level-unknown");
    var lvl = document.createElement("strong");
    lvl.textContent = time.level === "Unknown" ? "Time: unclear" : time.level + " time";
    badge.appendChild(lvl);
    if (time.hours) {
      var hrs = document.createElement("span");
      hrs.textContent = time.hours;
      badge.appendChild(hrs);
    }
    card.appendChild(badge);

    var h3 = document.createElement("h3");
    h3.className = "trial-title";
    h3.textContent = r.title;
    card.appendChild(h3);

    var meta = document.createElement("p");
    meta.className = "trial-meta";
    var bits = [];
    if (r.status) bits.push(r.status);
    if (r.conditions && r.conditions.length) bits.push(r.conditions.join(", "));
    meta.textContent = bits.join(" · ");
    card.appendChild(meta);

    if (r.locations && r.locations.length) {
      var loc = document.createElement("p");
      loc.className = "trial-loc";
      var text = r.locations.join("  •  ");
      if (r.location_count > r.locations.length) {
        text += "  (+" + (r.location_count - r.locations.length) + " more)";
      }
      loc.textContent = text;
      card.appendChild(loc);
    }

    if (time.basis) {
      var basis = document.createElement("p");
      basis.className = "trial-basis";
      basis.textContent = time.basis;
      card.appendChild(basis);
    }

    var actions = document.createElement("div");
    actions.className = "trial-actions";
    var summarize = document.createElement("a");
    summarize.className = "btn-inline";
    summarize.href = "/?nct=" + encodeURIComponent(r.nct_id);
    summarize.textContent = "View plain-language summary";
    actions.appendChild(summarize);
    if (r.url) {
      var ext = document.createElement("a");
      ext.className = "btn-inline-quiet";
      ext.href = r.url;
      ext.target = "_blank";
      ext.rel = "noopener";
      ext.textContent = "ClinicalTrials.gov · " + r.nct_id;
      actions.appendChild(ext);
    }
    card.appendChild(actions);

    return card;
  }

  function setLoading(isLoading) {
    button.disabled = isLoading;
    button.textContent = isLoading ? "Searching…" : "Search";
  }

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "status" + (isError ? " error" : "");
  }
})();
