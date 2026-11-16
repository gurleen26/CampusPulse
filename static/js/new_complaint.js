// Live ML analysis while the student types (debounced). Uses textContent only - no HTML injection.
(function () {
  const title = document.getElementById("f-title");
  const desc = document.getElementById("f-description");
  const loc = document.getElementById("f-location");
  const hint = document.getElementById("analysis-hint");
  const result = document.getElementById("analysis-result");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const urgencyClass = { Low: "bg-success", Medium: "bg-warning text-dark", High: "bg-danger" };
  let timer = null, counter = 0;

  async function analyse() {
    const my = ++counter;
    try {
      const res = await fetch("/student/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ title: title.value, description: desc.value, location: loc.value }),
      });
      const data = await res.json();
      if (my !== counter) return;                       // an newer request is already running
      if (!data.ready) { result.classList.add("d-none"); hint.classList.remove("d-none"); return; }
      hint.classList.add("d-none");
      result.classList.remove("d-none");
      document.getElementById("p-category").textContent = data.prediction.category;
      document.getElementById("p-category-conf").textContent = "(" + Math.round(data.prediction.category_confidence * 100) + "% confident)";
      const u = document.getElementById("p-urgency");
      u.textContent = data.prediction.urgency;
      u.className = "badge " + (urgencyClass[data.prediction.urgency] || "bg-secondary");
      document.getElementById("p-urgency-conf").textContent = "(" + Math.round(data.prediction.urgency_confidence * 100) + "% confident)";
      const list = document.getElementById("similar-list");
      list.replaceChildren();
      data.similar.forEach(function (s) {
        const li = document.createElement("li");
        li.textContent = s.complaint_id + " - " + s.title + " [" + s.status + "] " + Math.round(s.score * 100) + "% similar";
        list.appendChild(li);
      });
      document.getElementById("similar-box").classList.toggle("d-none", data.similar.length === 0);
    } catch (e) { /* analysis is optional - ignore network errors */ }
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(analyse, 600); }
  [title, desc, loc].forEach(function (el) { el.addEventListener("input", schedule); el.addEventListener("change", schedule); });
  if (title.value || desc.value) schedule();
})();
