/** Trasy z WhatsApp Chalupa — ověřeno ze screenshotů. Časy Europe/Prague. */
window.HRA_TRACKS = {
  grid: {
    columns: "ABCDEFGHIJKLMNOPQRSTU",
    rows: 17,
    // Georeference papírové mapy: Úbislavice–Hřídelec / Pustá Proseč (WGS84).
    // A–U × 1–17; U kvůli Matouš U13.
    bounds: {
      west: 15.448,
      east: 15.552,
      north: 50.491,
      south: 50.437
    }
  },
  car: { lat: 50.4654334, lon: 15.5059966, label: "Auto / cíl (Tereza GPS)" },
  pairs: [
    { id: "tatka-mamka", label: "Taťka + Mamka", members: ["tatka", "mamka"], note: "oba K7 @13:12" },
    { id: "martin-tereza", label: "Martin + Tereza", members: ["martin", "tereza"], note: "oba I8 @13:02" },
    { id: "anezka-matous", label: "Anežka + Matouš", members: ["anezka", "matous"], note: "oba L12 ~13:10" },
    { id: "marketa-mira", label: "Markéta + Míra", members: ["marketa", "mira"], note: "zbývající dvojice (cesty se nepotkaly)" }
  ],
  players: [
    {
      id: "martin",
      name: "Martin Kolda",
      color: "#c0392b",
      path: [
        ["B14","12:32"],["C12","12:35"],["D12","12:40"],["E11","12:46"],
        ["F10","12:50"],["G9","12:54"],["H8","12:59"],["I8","13:02"]
      ]
    },
    {
      id: "mira",
      name: "Míra Kubíček",
      color: "#1e8449",
      path: [
        ["O15","12:32"],["M16","12:36"],["M15","12:39"],["L16","12:47"],
        ["K17","12:53"],["J16","12:58"],["I17","13:01"],["H17","13:06"]
      ]
    },
    {
      id: "anezka",
      name: "Anežka Pešicová",
      color: "#8e44ad",
      path: [
        ["F9","12:32"],["G10","12:35"],["H11","12:44"],["I10","12:47"],
        ["J9","12:52"],["K10","13:00"],["L11","13:05"],["L12","13:11"]
      ]
    },
    {
      id: "marketa",
      name: "Markéta Vrabcová",
      color: "#d35400",
      path: [
        ["I3","12:32"],["J4","12:35"],["J5","12:42"],["K5","12:49"],["J6","13:04"]
      ]
    },
    {
      id: "matous",
      name: "Matouš Pešice",
      color: "#2471a3",
      path: [
        ["T14","12:32"],["U13","12:38"],["T12","12:41"],["S13","12:47"],
        ["R12","12:51"],["Q13","12:53"],["P13","12:55"],["O13","12:57"],
        ["N12","13:02"],["M13","13:05"],["L12","13:10"]
      ]
    },
    {
      id: "tereza",
      name: "Tereza Vrabcová",
      color: "#117a65",
      path: [
        ["P8","12:32"],["O9","12:39"],["N8","12:51"],["M7","12:51"],
        ["L6","12:52"],["K7","12:55"],["J7","13:00"],["I8","13:02"]
      ]
    },
    {
      id: "tatka",
      name: "Taťka",
      color: "#6c3483",
      path: [
        ["I16","12:32"],["H15","12:40"],["I14","12:46"],["I13","12:52"],
        ["J12","12:53"],["K11","12:59"],["J10","13:02"],["K9","13:06"],
        ["K8","13:09"],["K7","13:12"]
      ]
    },
    {
      id: "mamka",
      name: "Mamka",
      color: "#b7950b",
      path: [
        ["N1","12:33"],["M2","12:43"],["M3","12:46"],["M4","12:51"],
        ["M5","12:58"],["L6","13:04"],["K7","13:12"]
      ]
    }
  ],
  uncertain: [
    "Anežka K12 — v briefu volitelně, na screenshotech nepotvrzeno",
    "Markéta + Míra — párování jen eliminací, trasy se neprotínají",
    "Georeference mřížky je vizuální odhad vůči obcím (ne přesný scan papíru)"
  ]
};
