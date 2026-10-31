/** Trasy z WhatsApp Chalupa — ověřeno ze screenshotů. Časy Europe/Prague. */
window.HRA_TRACKS = {
  grid: {
    columns: "ABCDEFGHIJKLMNOPQRSTU",
    rows: 17,
    // Dual ground-truth anchors (OSM):
    // T14 = Matouš start — track×28427 crossroads Hřídelec node 313356094
    //       (50.4470249, 15.5328217); O15 = Míra start — path end by pond
    //       50880171 / node 3832194543 (50.4461299, 15.5167271).
    // Lon: both at column centers (Δcol=5). Lat: row boundary between them;
    // cellH from Úbislavice ≈ row 2–3. Villages rough-fit only.
    bounds: {
      west: 15.47005,
      east: 15.53765,
      north: 50.47866,
      south: 50.43970
    }
  },
  car: { lat: 50.4654334, lon: 15.5059966, label: "Auto / cíl (Tereza GPS)" },
  pairs: [
    { id: "honza-lucka", label: "Honza + Lucka", members: ["honza", "lucka"], note: "oba K7 @13:12" },
    { id: "martin-tereza", label: "Martin + Tereza", members: ["martin", "tereza"], note: "oba I8 @13:02" },
    { id: "anezka-matous", label: "Anežka + Matouš", members: ["anezka", "matous"], note: "oba L12 ~13:10" },
    { id: "marketa-mira", label: "Markéta + Míra", members: ["marketa", "mira"], note: "zbývající dvojice (cesty se nepotkaly)" }
  ],
  players: [
    {
      id: "martin",
      name: "Martin",
      color: "#e53935",
      path: [
        ["B14","12:32"],["C12","12:35"],["D12","12:40"],["E11","12:46"],
        ["F10","12:50"],["G9","12:54"],["H8","12:59"],["I8","13:02"]
      ]
    },
    {
      id: "mira",
      name: "Míra",
      color: "#43a047",
      path: [
        ["O15","12:32"],["M16","12:36"],["M15","12:39"],["L16","12:47"],
        ["K17","12:53"],["J16","12:58"],["I17","13:01"],["H17","13:06"]
      ]
    },
    {
      id: "anezka",
      name: "Anežka",
      color: "#ec407a",
      path: [
        ["F9","12:32"],["G10","12:35"],["H11","12:44"],["I10","12:47"],
        ["J9","12:52"],["K10","13:00"],["L11","13:05"],["L12","13:11"]
      ]
    },
    {
      id: "marketa",
      name: "Markéta",
      color: "#fb8c00",
      path: [
        ["I3","12:32"],["J4","12:35"],["J5","12:42"],["K5","12:49"],["J6","13:04"]
      ]
    },
    {
      id: "matous",
      name: "Matouš",
      color: "#1e88e5",
      path: [
        ["T14","12:32"],["U13","12:38"],["T12","12:41"],["S13","12:47"],
        ["R12","12:51"],["Q13","12:53"],["P13","12:55"],["O13","12:57"],
        ["N12","13:02"],["M13","13:05"],["L12","13:10"]
      ]
    },
    {
      id: "tereza",
      name: "Tereza",
      color: "#00897b",
      path: [
        ["P8","12:32"],["O9","12:39"],["N8","12:51"],["M7","12:51"],
        ["L6","12:52"],["K7","12:55"],["J7","13:00"],["I8","13:02"]
      ]
    },
    {
      id: "honza",
      name: "Honza",
      color: "#6d4c41",
      path: [
        ["I16","12:32"],["H15","12:40"],["I14","12:46"],["I13","12:52"],
        ["J12","12:53"],["K11","12:59"],["J10","13:02"],["K9","13:06"],
        ["K8","13:09"],["K7","13:12"]
      ]
    },
    {
      id: "lucka",
      name: "Lucka",
      color: "#f9a825",
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
