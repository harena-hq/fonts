#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
#
# Fetch every build input, pinned by SHA-256, and unpack it under sources/.
#
# If a hash changes, the upstream file changed: that is a finding, not a
# nuisance, because these bytes decide what the font is.
#
# Usage:
#   scripts/fetch_sources.sh          fetch and unpack everything
#   scripts/fetch_sources.sh --list   print the pinned files, one per line
#
# Optional: set HARENA_SOURCE_MIRROR to a base URL holding these files by
# basename, used only when an upstream fetch fails. A hash detects a changed
# upstream; it cannot resurrect a deleted one.

set -euo pipefail

cd "$(dirname "$0")/.."

LIST_ONLY=0
[ "${1:-}" = --list ] && LIST_ONLY=1

MIRROR="${HARENA_SOURCE_MIRROR:-}"

# --- pins --------------------------------------------------------------------
# google/fonts is a live repository, so its files are pinned to a commit, never
# to a branch.
GF_COMMIT=6157dfaa640ca5738b4d1a7070fe389c3036d7fc
GF=https://raw.githubusercontent.com/google/fonts/$GF_COMMIT/ofl
# Noto Sans CJK 2.004, the regional variable subsets.
NOTO_CJK_COMMIT=f8d157532fbfaeda587e826d4cd5b21a49186f7c
NOTO_CJK=https://raw.githubusercontent.com/notofonts/noto-cjk/$NOTO_CJK_COMMIT/Sans/Variable/TTF/Subset

# One table, read by both the fetcher and `--list`.
#
#      url | sha256 | destination
PINS="\
https://github.com/orioncactus/pretendard/releases/download/v1.3.9/PretendardJP-1.3.9.zip|8dab678c371a1530106ca643b76b2b80d47653d5ba670b01265b48e4c6615d63|sources/PretendardJP-1.3.9.zip
$GF/opensans/OpenSans%5Bwdth,wght%5D.ttf|36643644f318a812aab2d2ed3bb98f8cf0872527f835fe9398d95fe6b9adb878|sources/opensans/OpenSans[wdth,wght].ttf
$GF/opensans/OFL.txt|fbbbcfef55318de350562559b671360de6d597112ecc5c73881b05092db89602|sources/opensans/OFL.txt
$GF/opensans/OpenSans-Italic%5Bwdth,wght%5D.ttf|fe269381e992f32e135801740998544d6235061e37c93ec067ad2be3edd5b17b|sources/opensans/OpenSans-Italic[wdth,wght].ttf
$GF/notosans/NotoSans%5Bwdth,wght%5D.ttf|bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d|sources/notosans/NotoSans[wdth,wght].ttf
$GF/notosans/NotoSans-Italic%5Bwdth,wght%5D.ttf|58e6e0ebd1931b29a365aa2d3e2ee9a9e831a3af7cf3ad1462d4e72154f0b291|sources/notosans/NotoSans-Italic[wdth,wght].ttf
$NOTO_CJK/NotoSansJP-VF.ttf|f4b373b226668ee33a6e54b02823dcd2d1209f17159f777421ae8c2275160369|sources/notocjk/NotoSansJP-VF.ttf
$NOTO_CJK/NotoSansKR-VF.ttf|9e1d729e7e2b36f9ef439da102f8c134c10aabe46f1c843bf0aca5c043b86f76|sources/notocjk/NotoSansKR-VF.ttf
https://github.com/microsoft/Selawik/releases/download/1.01/Selawik_Release.zip|3f62c51e05e3b5a1e6241cf92a371f0be2ea1183aa87b30718bbd40832a8d423|sources/Selawik_Release.zip
https://registry.npmjs.org/@fluentui/svg-icons/-/svg-icons-1.1.345.tgz|6610366b1eb5ce4ce70c95d11accbf8858b01ec81c71d31bc6493586ac8cc905|sources/svg-icons-1.1.345.tgz
https://raw.githubusercontent.com/robloo/SymbolIconManager/8bf48d1ce7f1dd5ff2e1ed48410a62e6cabeacce/Source/IconManager.IconSets/Mappings/SegoeFluent.json|2013ee1390a01cf0384315c65357f2fca3c6f7eb92bcf1904ae9be6e586f2cd7|sources/symboliconmanager/SegoeFluent.json
"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }

verify() {  # verify <file> <sha256>
  local got
  got=$(sha256sum "$1" | cut -d' ' -f1)
  if [ "$got" != "$2" ]; then
    printf 'FAIL %s\n  expected %s\n  got      %s\n' "$1" "$2" "$got" >&2
    return 1
  fi
}

if [ "$LIST_ONLY" = 1 ]; then
  while IFS='|' read -r _url _sha dest; do
    [ -n "$dest" ] && printf '%s\n' "$dest"
  done <<LIST
$PINS
LIST
  exit 0
fi

fetch() {  # fetch <url> <sha256> <dest>
  local url=$1 sha=$2 dest=$3
  if [ -f "$dest" ] && verify "$dest" "$sha" 2>/dev/null; then
    say "have $(basename "$dest")"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  say "fetch $(basename "$dest")"
  if ! curl -fSL --retry 3 --connect-timeout 20 -o "$dest.part" "$url"; then
    if [ -n "$MIRROR" ]; then
      say "upstream failed; trying mirror"
      curl -fSL --retry 3 --connect-timeout 20 \
        -o "$dest.part" "$MIRROR/$(basename "$dest")"
    else
      printf 'upstream fetch failed and HARENA_SOURCE_MIRROR is unset\n' >&2
      return 1
    fi
  fi
  verify "$dest.part" "$sha"
  mv "$dest.part" "$dest"
}

# Here-doc, not a pipe: a pipeline runs the loop in a subshell, where `set -e`
# on a failed fetch would end only the subshell.
while IFS='|' read -r url sha dest; do
  [ -n "$url" ] || continue
  fetch "$url" "$sha" "$dest"
done <<FETCH
$PINS
FETCH

if [ ! -f sources/pjp/public/variable/PretendardJPVariable.ttf ]; then
  say "extract PretendardJP"
  mkdir -p sources/pjp
  unzip -q -o sources/PretendardJP-1.3.9.zip -d sources/pjp
fi

if [ ! -f sources/selawik/selawk.ttf ]; then
  say "extract Selawik"
  mkdir -p sources/selawik
  unzip -q -o -j sources/Selawik_Release.zip '*.ttf' -d sources/selawik
fi

if [ ! -f sources/fluent/package/package.json ]; then
  say "extract Fluent UI System Icons"
  mkdir -p sources/fluent
  tar xzf sources/svg-icons-1.1.345.tgz -C sources/fluent
fi
