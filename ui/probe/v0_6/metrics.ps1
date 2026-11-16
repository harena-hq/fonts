# SPDX-License-Identifier: Apache-2.0
# Print, as JSON, the vertical metrics of installed faces, found by PostScript name in the
# system font folder (.ttf and each face of a .ttc). Only the file name, the face's SHA-256 of
# its file and numbers leave the machine: unitsPerEm, hhea ascender/descender/lineGap, OS/2
# typo ascender/descender/lineGap, win ascent/descent and fsSelection. -Files narrows the search.
param([string[]]$Names = @('MalgunGothic'), [string[]]$Files = @('*.ttf', '*.ttc'))
Add-Type -Language CSharp -TypeDefinition @'
using System; using System.Collections.Generic; using System.Text;
public static class Metrics {
  static byte[] b;
  static int U16(int o) { return (b[o] << 8) | b[o + 1]; }
  static int S16(int o) { return (short)U16(o); }
  static int U32(int o) { return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]; }
  static string Face(int at, string want) {
    var t = new Dictionary<string, int>();
    for (int i = 0; i < U16(at + 4); i++) t[Encoding.ASCII.GetString(b, at + 12 + 16 * i, 4)] = U32(at + 12 + 16 * i + 8);
    int nm = t["name"], strings = nm + U16(nm + 4); string ps = null;
    for (int i = 0; i < U16(nm + 2); i++) {
      int r = nm + 6 + 12 * i;
      if (U16(r) == 3 && U16(r + 2) == 1 && U16(r + 4) == 0x409 && U16(r + 6) == 6)
        ps = Encoding.BigEndianUnicode.GetString(b, strings + U16(r + 10), U16(r + 8));
    }
    if (ps != want) return null;
    int head = t["head"], hhea = t["hhea"], os2 = t["OS/2"];
    return "{\"upem\":" + U16(head + 18) + ",\"hhea\":[" + S16(hhea + 4) + "," + S16(hhea + 6) + "," + S16(hhea + 8) +
      "],\"typo\":[" + S16(os2 + 68) + "," + S16(os2 + 70) + "," + S16(os2 + 72) + "],\"win\":[" + U16(os2 + 74) + "," +
      U16(os2 + 76) + "],\"fsSelection\":" + U16(os2 + 62) + "}";
  }
  public static string Find(byte[] bytes, string want) {
    b = bytes;
    if (Encoding.ASCII.GetString(b, 0, 4) == "ttcf") {
      for (int i = 0; i < U32(8); i++) { var f = Face(U32(12 + 4 * i), want); if (f != null) return f; }
      return null;
    }
    return Face(0, want);
  }
}
'@
$out = @()
foreach ($n in $Names) {
  $hit = $null
  foreach ($f in Get-ChildItem C:\Windows\Fonts\* -Include $Files) {
    $m = [Metrics]::Find([IO.File]::ReadAllBytes($f.FullName), $n)
    if ($m) { $hit = '"' + $n + '":{"file":"' + $f.Name + '","sha256":"' + (Get-FileHash -Algorithm SHA256 $f.FullName).Hash.ToLower() + '",' + $m.Substring(1); break }
  }
  if (-not $hit) { $hit = '"' + $n + '":null' }
  $out += $hit
}
'{' + ($out -join ',') + '}'
