(function () {
  "use strict";

  var form = document.getElementById("search-form");
  var input = document.getElementById("nct-input");
  var button = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");
  var resultEl = document.getElementById("result");

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var nct = input.value.trim();
    if (!nct) {
      return;
    }
    fetchSummary(nct);
  });

  function fetchSummary(nct) {
    setLoading(true);
    setStatus("Fetching and summarizing " + nct + "…", false);
    resultEl.hidden = true;
    resultEl.innerHTML = "";

    fetch("/api/summary?nct=" + encodeURIComponent(nct))
      .then(function (response) {
        return response.json().then(function (body) {
          return { ok: response.ok, body: body };
        });
      })
      .then(function (payload) {
        if (!payload.ok) {
          setStatus(payload.body.error || "Something went wrong.", true);
          return;
        }
        setStatus("", false);
        render(payload.body);
      })
      .catch(function () {
        setStatus("Could not reach the server. Please try again.", true);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  function render(summary) {
    resultEl.innerHTML = "";

    var header = document.createElement("div");
    header.className = "result-header";

    var h2 = document.createElement("h2");
    h2.textContent = summary.title || "Study summary";
    header.appendChild(h2);

    if (summary.url) {
      var link = document.createElement("a");
      link.href = summary.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "View full study on ClinicalTrials.gov (" + summary.nct_id + ") →";
      header.appendChild(link);
    }

    if (summary.relevance && summary.relevance.note) {
      var badge = document.createElement("div");
      badge.className = "badge " + (summary.relevance.is_breast_or_colon ? "ok" : "warn");
      badge.textContent = summary.relevance.note;
      header.appendChild(badge);
    }

    resultEl.appendChild(header);

    (summary.sections || []).forEach(function (section) {
      resultEl.appendChild(renderSection(section));
    });

    resultEl.hidden = false;
  }

  function renderSection(section) {
    var card = document.createElement("div");
    card.className = "card";

    var h3 = document.createElement("h3");
    h3.textContent = section.heading;
    card.appendChild(h3);

    var ul = document.createElement("ul");
    (section.bullets || []).forEach(function (bullet) {
      var li = document.createElement("li");
      // Bullets indented in the data are shown as sub-items.
      if (/^\s/.test(bullet)) {
        li.className = "sub";
        li.textContent = bullet.replace(/^\s*-\s*/, "").trim();
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
