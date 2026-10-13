/* 演示页逻辑（外置，避免部分环境拦截 inline script） */
(() => {
  const data = window.COUNTRIES || [];
  const flagUrl = (iso) => "flags/" + iso.toLowerCase() + ".svg";

  document.getElementById("s-count").textContent = data.length;
  document.getElementById("s-flag").textContent = data.filter((d) => d.has_flag).length;
  const group = {};
  data.forEach((d) => {
    group[d.phone_prefix] = (group[d.phone_prefix] || 0) + 1;
  });
  document.getElementById("s-share").textContent =
    Object.values(group).filter((n) => n > 1).reduce((a, b) => a + b, 0) + " 个";

  let current = data.find((d) => d.iso2 === "CN") || data[0];
  let activeIdx = 0;
  let filtered = data.slice();

  const $ = (id) => document.getElementById(id);
  const drop = $("drop");
  const list = $("list");
  const q = $("q");
  const field = $("field");

  function paintCurrent() {
    if (!current) return;
    $("curFlag").style.backgroundImage = current.has_flag ? `url(${flagUrl(current.iso2)})` : "none";
    $("curCode").textContent = current.phone_prefix;
    if (current.has_flag) $("curCode").title = `${current.name_zh} ${current.phone_prefix}`;
  }

  function render() {
    if (!filtered.length) {
      list.innerHTML = '<li class="none">没有匹配的国家或地区</li>';
      return;
    }
    list.innerHTML = filtered
      .map(
        (d, i) => `
    <li role="option" data-i="${i}" aria-selected="${i === activeIdx}">
      <span class="flag lg"${d.has_flag ? ` style="background-image:url(${flagUrl(d.iso2)})"` : ""}></span>
      <span class="nm">${d.name_zh}<span class="en">${d.name_en}</span></span>
      <span class="dc">${d.phone_prefix}</span>
    </li>`,
      )
      .join("");
    const el = list.querySelector("li.active") || list.querySelector('li[aria-selected="true"]');
    if (el) el.scrollIntoView({ block: "nearest" });
  }

  function open() {
    drop.classList.add("open");
    $("ccBtn").setAttribute("aria-expanded", "true");
    q.value = "";
    filtered = data.slice();
    activeIdx = 0;
    render();
    q.focus();
  }

  function close() {
    drop.classList.remove("open");
    $("ccBtn").setAttribute("aria-expanded", "false");
  }

  function choose(d) {
    current = d;
    paintCurrent();
    close();
    $("phone").focus();
  }

  $("ccBtn").addEventListener("click", (e) => {
    e.stopPropagation();
    drop.classList.contains("open") ? close() : open();
  });

  q.addEventListener("input", () => {
    const term = q.value.trim().toLowerCase();
    filtered = !term
      ? data.slice()
      : data.filter(
          (d) =>
            d.name_zh.includes(term) ||
            d.name_en.toLowerCase().includes(term) ||
            d.iso2.toLowerCase().includes(term) ||
            (d.iso3 || "").toLowerCase().includes(term) ||
            d.phone_prefix.includes(term) ||
            d.dial_code.includes(term.replace(/^\+/, "")),
        );
    activeIdx = 0;
    render();
  });

  list.addEventListener("click", (e) => {
    const li = e.target.closest("li[data-i]");
    if (li) choose(filtered[+li.dataset.i]);
  });

  document.addEventListener("click", (e) => {
    if (!field.contains(e.target)) close();
  });

  document.addEventListener("keydown", (e) => {
    if (!drop.classList.contains("open")) return;
    if (e.key === "Escape") {
      close();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      activeIdx = Math.min(
        filtered.length - 1,
        Math.max(0, activeIdx + (e.key === "ArrowDown" ? 1 : -1)),
      );
      render();
    }
    if (e.key === "Enter" && filtered[activeIdx]) {
      e.preventDefault();
      choose(filtered[activeIdx]);
    }
  });

  const top = data
    .slice()
    .sort((a, b) => b.priority - a.priority || a.name_en.localeCompare(b.name_en))
    .slice(0, 12);
  $("tbody").innerHTML = top
    .map(
      (d) => `
  <tr>
    <td><span class="flag"${d.has_flag ? ` style="background-image:url(${flagUrl(d.iso2)})"` : ""}></span></td>
    <td>${d.name_zh} <span style="color:var(--muted);font-size:12px">${d.name_en}</span></td>
    <td class="mono">${d.iso2} / ${d.iso3 || "—"}</td>
    <td class="mono">${d.phone_prefix}</td>
  </tr>`,
    )
    .join("");

  paintCurrent();
})();
