async function fetchParticipants() {
  const res = await fetch("data/participants.json");
  if (!res.ok) {
    throw new Error("Unable to load participants.json");
  }
  return res.json();
}

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function makeTileLink(href, idText, metaText) {
  const a = document.createElement("a");
  a.className = "tile-link";
  a.href = href;

  const idLine = document.createElement("p");
  idLine.className = "id-line";
  idLine.textContent = idText;

  const metaLine = document.createElement("p");
  metaLine.className = "meta-line";
  metaLine.textContent = metaText;

  a.appendChild(idLine);
  a.appendChild(metaLine);
  return a;
}

function escapeQueryValue(value) {
  return encodeURIComponent(value ?? "");
}
