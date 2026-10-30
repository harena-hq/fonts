# SPDX-License-Identifier: Apache-2.0
# Print the code points a font maps, one decimal number per line. Reads the
# font's cmap on the machine where the font is installed; nothing else leaves it.
# Prefers the (3,10) format 12 subtable, else (3,1) format 4.
param([string]$Path = 'C:\Windows\Fonts\SegUIVar.ttf')
$b = [IO.File]::ReadAllBytes($Path)
function U16($o) { ([int]$b[$o] -shl 8) -bor [int]$b[$o+1] }
function U32($o) { ([uint32]$b[$o] -shl 24) -bor ([uint32]$b[$o+1] -shl 16) -bor ([uint32]$b[$o+2] -shl 8) -bor [uint32]$b[$o+3] }
$n = U16 4; $cmap = $null
for ($i = 0; $i -lt $n; $i++) { $r = 12 + 16*$i
  if ([Text.Encoding]::ASCII.GetString($b, $r, 4) -eq 'cmap') { $cmap = U32 ($r+8) } }
$count = U16 ($cmap+2); $sub = @{}
for ($i = 0; $i -lt $count; $i++) { $r = $cmap + 4 + 8*$i
  $sub["$(U16 $r),$(U16 ($r+2))"] = $cmap + (U32 ($r+4)) }
$out = New-Object System.Collections.Generic.List[int]
if ($sub.ContainsKey('3,10') -and (U16 $sub['3,10']) -eq 12) {
  $t = $sub['3,10']; $groups = U32 ($t+12)
  for ($g = 0; $g -lt $groups; $g++) { $r = $t + 16 + 12*$g
    $s = U32 $r; $e = U32 ($r+4); $gid = U32 ($r+8)
    for ($c = $s; $c -le $e; $c++) { if ($gid + ($c - $s) -ne 0) { $out.Add([int]$c) } } }
} else {
  $t = $sub['3,1']; $seg = (U16 ($t+6)) / 2
  $ends = $t + 14; $starts = $ends + 2*$seg + 2; $deltas = $starts + 2*$seg; $ranges = $deltas + 2*$seg
  for ($i = 0; $i -lt $seg; $i++) {
    $e = U16 ($ends + 2*$i); $s = U16 ($starts + 2*$i); $d = U16 ($deltas + 2*$i); $ro = U16 ($ranges + 2*$i)
    for ($c = $s; $c -le $e -and $c -ne 0xFFFF; $c++) {
      if ($ro -eq 0) { $gid = ($c + $d) -band 0xFFFF }
      else { $a = $ranges + 2*$i + $ro + 2*($c - $s); $gid = U16 $a; if ($gid -ne 0) { $gid = ($gid + $d) -band 0xFFFF } }
      if ($gid -ne 0) { $out.Add($c) } } }
}
$out -join "`n"
