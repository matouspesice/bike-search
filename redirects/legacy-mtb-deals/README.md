# Legacy redirect: `/mtb-deals/` → `/bike-search/`

GitHub po rename repa přesměruje `github.com/.../mtb-deals`, ale **ne**
`*.github.io/mtb-deals/`.

Tenhle strom se deployuje do user site
[`matouspesice.github.io`](https://github.com/matouspesice/matouspesice.github.io)
a obnoví staré bookmarky.

```bash
bash scripts/setup_legacy_pages_redirect.sh
```
