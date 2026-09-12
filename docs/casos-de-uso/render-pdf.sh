#!/usr/bin/env bash
# Renderiza los diagramas de casos de uso a PDF vectorial para la tesis.
#
#   docs/casos-de-uso/render-pdf.sh            → todos los .puml
#   docs/casos-de-uso/render-pdf.sh 04 11      → solo los que empiezan por 04 y 11
#
# PlantUML corre en la imagen plantuml/plantuml (trae Graphviz) con las fuentes del
# anfitrión montadas, para que el texto mida lo mismo que al imprimir con Chrome.
# Chrome convierte cada SVG en un PDF de una página del tamaño exacto del diagrama.
#
# Al final imprime el tamaño de cada diagrama en px: es lo que usa
# casos-de-uso-latex.txt para repartir las figuras en páginas de dos o tres.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/pdf"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)"

shopt -s nullglob
if [[ $# -gt 0 ]]; then
  sources=()
  for prefix in "$@"; do sources+=("$HERE/$prefix"*.puml); done
else
  sources=("$HERE"/*.puml)
fi
[[ ${#sources[@]} -gt 0 ]] || { echo "No hay diagramas que renderizar" >&2; exit 1; }

mkdir -p "$OUT" "$BUILD/svg"
cp "${sources[@]}" "$BUILD/svg/"

docker run --rm --user "$(id -u):$(id -g)" \
  -v "$BUILD/svg:/data" -v /usr/share/fonts:/usr/share/fonts:ro \
  plantuml/plantuml -tsvg -charset UTF-8 -failfast2 /data

printf '\n%-48s %6s %6s\n' "diagrama" "ancho" "alto"
for puml in "${sources[@]}"; do
  name="$(basename "$puml" .puml)"
  # El SVG toma el nombre de @startuml (cu-<archivo>), no el del archivo.
  svg="$BUILD/svg/cu-$name.svg"
  [[ -f "$svg" ]] || svg="$BUILD/svg/$name.svg"

  size="$(grep -o 'viewBox="[^"]*"' "$svg" | head -1 | tr -d '"' | cut -d' ' -f3,4)"
  w="${size% *}"
  h="${size#* }"

  cat > "$BUILD/$name.html" <<HTML
<!doctype html><meta charset="utf-8">
<style>
  @page { size: ${w}px ${h}px; margin: 0 }
  html, body { margin: 0; width: ${w}px; height: ${h}px; overflow: hidden }
  img { display: block; width: ${w}px; height: ${h}px }
</style>
<img src="file://$svg">
HTML

  "$CHROME" --headless=new --disable-gpu --no-first-run --no-pdf-header-footer \
    --user-data-dir="$BUILD/chrome" --print-to-pdf="$OUT/$name.pdf" \
    "file://$BUILD/$name.html" >/dev/null 2>&1

  printf '%-48s %6s %6s\n' "$name" "$w" "$h"
done
echo -e "\nPDF en $OUT"
