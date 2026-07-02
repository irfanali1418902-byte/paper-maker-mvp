// Shared API client for all frontend pages (index / dashboard / print).
//
// Ek shared key per deployment. localStorage mein rehti hai aur har /api call ke
// x-api-key header mein jaati hai. Server par key set na ho (dev) to yeh header
// harmless hai — ignore ho jata hai, is liye dev experience par koi asar nahi.
// apiFetch() hi har /api call ka single choke-point hai; 401 par key-gate khulta.
//
// Classic (non-module) script hai, is liye `apiFetch` global scope mein aata hai
// aur baaki page-scripts isse naam se call kar sakti hain.

const _rawFetch = window.fetch.bind(window);
const PM_KEY_STORAGE = "pm_api_key";
const pmGetKey = () => localStorage.getItem(PM_KEY_STORAGE) || "";

function pmShowKeyGate(msg) {
  let gate = document.getElementById("pm-key-gate");
  if (!gate) {
    gate = document.createElement("div");
    gate.id = "pm-key-gate";
    gate.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:sans-serif";
    gate.innerHTML =
      '<div style="background:#fff;padding:24px;border-radius:12px;max-width:360px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,.3)">' +
      '<h3 style="margin:0 0 8px">Access key chahiye</h3>' +
      '<p id="pm-key-msg" style="margin:0 0 12px;color:#555;font-size:14px">Is tool ko use karne ke liye apni key daalein.</p>' +
      '<input id="pm-key-input" type="password" placeholder="x-api-key" style="width:100%;padding:10px;border:1px solid #ccc;border-radius:8px;box-sizing:border-box" />' +
      '<button id="pm-key-save" style="margin-top:12px;width:100%;padding:10px;border:0;border-radius:8px;background:#1a4d2e;color:#fff;font-size:15px;cursor:pointer">Save & continue</button>' +
      "</div>";
    document.body.appendChild(gate);
    const save = () => {
      const v = gate.querySelector("#pm-key-input").value.trim();
      if (v) {
        localStorage.setItem(PM_KEY_STORAGE, v);
        location.reload();
      }
    };
    gate.querySelector("#pm-key-save").addEventListener("click", save);
    gate
      .querySelector("#pm-key-input")
      .addEventListener("keydown", (e) => {
        if (e.key === "Enter") save();
      });
  }
  if (msg) gate.querySelector("#pm-key-msg").textContent = msg;
  gate.style.display = "flex";
  gate.querySelector("#pm-key-input").focus();
}

async function apiFetch(url, opts = {}) {
  const key = pmGetKey();
  const headers = Object.assign({}, opts.headers || {});
  if (key) headers["x-api-key"] = key;
  const res = await _rawFetch(url, Object.assign({}, opts, { headers }));
  if (res.status === 401) {
    localStorage.removeItem(PM_KEY_STORAGE);
    pmShowKeyGate("Key ghalat ya missing hai — dobara daalein.");
  }
  return res;
}
