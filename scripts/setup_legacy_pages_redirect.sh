#!/usr/bin/env bash
# Obnoví starý GitHub Pages odkaz matouspesice.github.io/mtb-deals/
# přes user site matouspesice.github.io (GitHub po rename Pages nepřesměruje).
#
# Proč ne repo jménem mtb-deals:
#   Znovuvytvoření matouspesice/mtb-deals by zrušilo github.com redirect
#   mtb-deals → bike-search. User site to nekazí.
#
# Použití (lokálně, s přihlášeným gh):
#   bash scripts/setup_legacy_pages_redirect.sh

set -euo pipefail

OWNER="${GITHUB_OWNER:-matouspesice}"
USER_SITE_REPO="${OWNER}.github.io"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)/redirects/legacy-mtb-deals"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! command -v gh >/dev/null; then
  echo "Potřebuješ GitHub CLI (gh) přihlášené k účtu ${OWNER}." >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR/mtb-deals" ]]; then
  echo "Chybí redirect soubory v $SRC_DIR" >&2
  exit 1
fi

echo "==> Kontrola / vytvoření repo ${OWNER}/${USER_SITE_REPO}"
if gh repo view "${OWNER}/${USER_SITE_REPO}" >/dev/null 2>&1; then
  echo "    repo už existuje"
else
  gh repo create "${OWNER}/${USER_SITE_REPO}" \
    --public \
    --description "User GitHub Pages — redirect legacy /mtb-deals → bike-search" \
    --homepage "https://${OWNER}.github.io/"
fi

echo "==> Klon a deploy redirectů"
gh repo clone "${OWNER}/${USER_SITE_REPO}" "$TMP_DIR/site" -- --depth 1
cd "$TMP_DIR/site"

# Zachovej existující obsah mimo mtb-deals / 404 / kořenový index redirect stub
cp -a "$SRC_DIR/mtb-deals" .
cp -a "$SRC_DIR/404.html" .
if [[ ! -f index.html ]]; then
  cp -a "$SRC_DIR/index.html" .
fi
touch .nojekyll

git add -A
if git diff --cached --quiet; then
  echo "    nic nového k commitnutí"
else
  git commit -m "Add legacy /mtb-deals redirect to bike-search Pages"
  git push origin HEAD
fi

echo "==> Zapnutí GitHub Pages (branch main, /)"
# Idempotentní: create selže když už Pages běží — pak patch.
if ! gh api "repos/${OWNER}/${USER_SITE_REPO}/pages" >/dev/null 2>&1; then
  gh api -X POST "repos/${OWNER}/${USER_SITE_REPO}/pages" \
    -f build_type=legacy \
    -f 'source[branch]=main' \
    -f 'source[path]=/' \
    >/dev/null || true
else
  gh api -X PUT "repos/${OWNER}/${USER_SITE_REPO}/pages" \
    -f build_type=legacy \
    -f 'source[branch]=main' \
    -f 'source[path]=/' \
    >/dev/null || true
fi

echo
echo "Hotovo. Po buildu Pages (cca 1 min) by mělo fungovat:"
echo "  https://${OWNER}.github.io/mtb-deals/"
echo "  → https://${OWNER}.github.io/bike-search/"
echo "  https://${OWNER}.github.io/mtb-deals/report-gravel168.html"
echo "  → https://${OWNER}.github.io/bike-search/report-gravel168.html"
