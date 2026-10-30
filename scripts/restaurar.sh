#!/usr/bin/env bash
# Restaura un respaldo (.dump de pg_dump) en una base PostgreSQL. BORRA lo que haya en la base destino.
#
# Uso:  scripts/restaurar.sh <archivo.dump> <URL de la base destino> [--si]
#   --si   no pide confirmación (lo usa el workflow de respaldo).
#
# Para bajar el último respaldo:  scripts/restaurar.sh --bajar
# Usa pg_restore si está instalado; si no, la imagen postgres:17 de Docker.
set -euo pipefail

if [ "${1:-}" = "--bajar" ]; then
  id=$(gh run list --workflow respaldo.yml --status success --limit 1 --json databaseId --jq '.[0].databaseId')
  [ -n "$id" ] || { echo "No hay respaldos exitosos."; exit 1; }
  gh run download "$id" --dir respaldos
  find respaldos -name '*.dump'
  exit 0
fi

archivo=${1:?"Falta el archivo .dump"}
destino=${2:?"Falta la URL de la base destino"}
[ -f "$archivo" ] || { echo "No existe $archivo"; exit 1; }
# psql y pg_restore no entienden el prefijo de SQLAlchemy.
destino=${destino/postgresql+psycopg:/postgresql:}

if [ "${3:-}" != "--si" ]; then
  echo "Se va a BORRAR y reemplazar el contenido de: ${destino%%@*}@…${destino##*@}"
  read -r -p "Escribe RESTAURAR para seguir: " ok
  [ "$ok" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }
fi

if command -v pg_restore >/dev/null; then
  pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error --dbname="$destino" "$archivo"
else
  dir=$(cd "$(dirname "$archivo")" && pwd)
  docker run --rm --network host -v "$dir:/r:ro" postgres:17 \
    pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error \
    --dbname="$destino" "/r/$(basename "$archivo")"
fi
echo "Restaurado $archivo"
