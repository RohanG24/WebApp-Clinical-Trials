(function () {
  "use strict";

  var form = document.getElementById("search-form");
  var input = document.getElementById("nct-input");
  var button = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");
  var resultEl = document.getElementById("result");
  var placeholderEl = document.getElementById("placeholder");
  var skeletonEl = document.getElementById("skeleton");

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var nct = input.value.trim();
    if (nct) {
      fetchSummary(nct);
    }
  });

  // Example chips fill the box and run immediately.
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
      link.className = "study-link";
      link.href = summary.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "ClinicalTrials.gov · " + summary.nct_id + " ↗";
      header.appendChild(link);
    }

    var h2 = document.createElement("h2");
    h2.textContent = summary.title || "Study summary";
    header.appendChild(h2);

    if (summary.relevance && summary.relevance.note) {
      var badge = document.createElement("div");
      badge.className = "badge " + (summary.relevance.is_breast_or_colon ? "ok" : "warn");
      badge.textContent =
        (summary.relevance.is_breast_or_colon ? "✓ " : "⚠ ") + summary.relevance.note;
      header.appendChild(badge);
    }
    resultEl.appendChild(header);

    // ---- Print toolbar ----
    var toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    var printBtn = document.createElement("button");
    printBtn.type = "button";
    printBtn.className = "print-btn";
    printBtn.textContent = "🖨 Print / save this summary";
    printBtn.addEventListener("click", function () {
      window.print();
    });
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
    if (section.icon) {
      var icon = document.createElement("span");
      icon.className = "card-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = section.icon;
      title.appendChild(icon);
    }
    title.appendChild(document.createTextNode(section.heading));
    card.appendChild(title);

    var ul = document.createElement("ul");
    (section.bullets || []).forEach(function (bullet) {
      var li = document.createElement("li");
      if (/^\s/.test(bullet)) {
        // Indented bullet -> sub-item.
        li.className = "sub";
        li.textContent = bullet.replace(/^\s*-\s*/, "").trim();
      } else if (/:\s*$/.test(bullet)) {
        // A lead-in line that introduces sub-items (e.g. "You may join if:").
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
