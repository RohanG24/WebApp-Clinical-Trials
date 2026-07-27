(function () {
  "use strict";

  var form = document.getElementById("search-form");
  var input = document.getElementById("nct-input");
  var button = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");
  var resultEl = document.getElementById("result");
  var placeholderEl = document.getElementById("placeholder");
  var skeletonEl = document.getElementById("skeleton");

  // Inner markup for 24x24 line icons, drawn with currentColor.
  var ICONS = {
    clipboard: '<rect x="8" y="3" width="8" height="4" rx="1"/><path d="M9 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    activity: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
    flask: '<path d="M9 3h6"/><path d="M10 3v6l-5 8a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-8V3"/><path d="M7.5 14h9"/>',
    calendar: '<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>',
    droplet: '<path d="M12 3s6 6.5 6 10.5a6 6 0 0 1-12 0C6 9.5 12 3 12 3z"/>',
    "user-check": '<circle cx="9" cy="8" r="3.5"/><path d="M4 20a5 5 0 0 1 10 0"/><path d="M16 12l2 2 4-4"/>',
    "map-pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.5"/>',
    phone: '<path d="M21 16.5v3a2 2 0 0 1-2.2 2 19 19 0 0 1-8.3-3 18.6 18.6 0 0 1-5.7-5.7 19 19 0 0 1-3-8.4A2 2 0 0 1 3.8 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.5 2.1L7.6 9.7a15 15 0 0 0 5.7 5.7l1.3-1.3a2 2 0 0 1 2.1-.5c.8.3 1.7.5 2.6.6a2 2 0 0 1 1.7 2z"/>',
    check: '<path d="M20 6L9 17l-5-5"/>',
    alert: '<path d="M12 3l9 16H3z"/><path d="M12 10v4"/><path d="M12 17h.01"/>'
  };

  function iconSvg(name) {
    var inner = ICONS[name];
    if (!inner) return null;
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.8");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = inner;
    return svg;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var nct = input.value.trim();
    if (nct) fetchSummary(nct);
  });

  document.querySelectorAll(".example").forEach(function (chip) {
    chip.addEventListener("click", function () {
      input.value = chip.getAttribute("data-nct");
      fetchSummary(input.value);
    });
  });

  function fetchSummary(nct) {
    setLoading(true);
    setStatus("", false);
    placeholderEl.hidden = true;
    resultEl.hidden = true;
    resultEl.innerHTML = "";
    skeletonEl.hidden = false;

    fetch("/api/summary?nct=" + encodeURIComponent(nct))
      .then(function (response) {
        return response.json().then(function (body) {
          return { ok: response.ok, body: body };
        });
      })
      .then(function (payload) {
        skeletonEl.hidden = true;
        if (!payload.ok) {
          setStatus(payload.body.error || "Something went wrong.", true);
          placeholderEl.hidden = false;
          return;
        }
        render(payload.body);
      })
      .catch(function () {
        skeletonEl.hidden = true;
        placeholderEl.hidden = false;
        setStatus("Could not reach the server. Please try again.", true);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  function render(summary) {
    resultEl.innerHTML = "";

    // ---- Header ----
    var header = document.createElement("div");
    header.className = "result-header";

    if (summary.url) {
      var link = document.createElement("a");
      link.className = "eyebrow";
      link.href = summary.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "ClinicalTrials.gov · " + summary.nct_id;
      header.appendChild(link);
    }

    var h2 = document.createElement("h2");
    h2.textContent = summary.title || "Study summary";
    header.appendChild(h2);

    if (summary.relevance && summary.relevance.note) {
      var isOk = summary.relevance.is_breast_or_colon;
      var badge = document.createElement("div");
      badge.className = "badge " + (isOk ? "ok" : "warn");
      var bIcon = iconSvg(isOk ? "check" : "alert");
      if (bIcon) badge.appendChild(bIcon);
      var bText = document.createElement("span");
      bText.textContent = summary.relevance.note;
      badge.appendChild(bText);
      header.appendChild(badge);
    }
    resultEl.appendChild(header);

    // ---- Print toolbar ----
    var toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    var printBtn = document.createElement("button");
    printBtn.type = "button";
    printBtn.className = "print-btn";
    printBtn.textContent = "Print / save summary";
    printBtn.addEventListener("click", function () { window.print(); });
    toolbar.appendChild(printBtn);
    resultEl.appendChild(toolbar);

    // ---- Sections ----
    (summary.sections || []).forEach(function (section) {
      resultEl.appendChild(renderSection(section));
    });

    resultEl.hidden = false;
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderSection(section) {
    var card = document.createElement("div");
    card.className = "card" + (section.featured ? " card-featured" : "");

    var title = document.createElement("h3");
    title.className = "card-title";
    var icon = iconSvg(section.icon);
    if (icon) {
      var wrap = document.createElement("span");
      wrap.className = "card-icon";
      wrap.appendChild(icon);
      title.appendChild(wrap);
    }
    title.appendChild(document.createTextNode(section.heading));
    card.appendChild(title);

    var ul = document.createElement("ul");
    (section.bullets || []).forEach(function (bullet) {
      var li = document.createElement("li");
      if (/^\s/.test(bullet)) {
        li.className = "sub";
        li.textContent = bullet.replace(/^\s*-\s*/, "").trim();
      } else if (/:\s*$/.test(bullet)) {
        li.className = "lead";
        li.textContent = bullet;
      } else {
        li.textContent = bullet;
      }
      ul.appendChild(li);
    });
    card.appendChild(ul);
    return card;
  }

  function setLoading(isLoading) {
    button.disabled = isLoading;
    button.textContent = isLoading ? "Working…" : "Summarize";
  }

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "status" + (isError ? " error" : "");
  }
})();
