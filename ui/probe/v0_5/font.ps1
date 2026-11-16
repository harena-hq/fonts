# SPDX-License-Identifier: Apache-2.0
# Print, as JSON, Segoe Fluent Icons' geometry: the file's SHA-256, its metrics and, per
# code point, the advance, ink box and a group number shared by points drawing one glyph.
# Runs on the machine where the font is installed. No outline, glyph ID or glyph name
# leaves it: groups are renumbered in code point order.
param([string]$Path = 'C:\Windows\Fonts\SegoeIcons.ttf')
Add-Type -AssemblyName PresentationCore
Add-Type -Language CSharp -TypeDefinition @'
using System; using System.Collections.Generic; using System.Linq; using System.Text;
public static class Geometry {
  static byte[] b;
  static int U16(int o) { return (b[o] << 8) | b[o + 1]; }
  static int S16(int o) { return (short)U16(o); }
  static int U32(int o) { return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]; }
  public static string Run(byte[] bytes) {
    b = bytes; var t = new Dictionary<string, int>();
    for (int i = 0; i < U16(4); i++) t[Encoding.ASCII.GetString(b, 12 + 16 * i, 4)] = U32(12 + 16 * i + 8);
    int head = t["head"], hhea = t["hhea"], os2 = t["OS/2"], hmtx = t["hmtx"], loca = t["loca"], glyf = t["glyf"], cm = t["cmap"];
    int nh = U16(hhea + 34), longLoca = U16(head + 50);
    var map = new SortedDictionary<int, int>();
    for (int i = 0; i < U16(cm + 2); i++) {
      int r = cm + 4 + 8 * i, s = cm + U32(r + 4);
      if (U16(r) != 3 || U16(r + 2) != 1 || U16(s) != 4) continue;
      int seg = U16(s + 6) / 2, e = s + 14, st = e + 2 * seg + 2, d = st + 2 * seg, ro = d + 2 * seg;
      for (int k = 0; k < seg; k++) {
        int ee = U16(e + 2 * k), ss = U16(st + 2 * k), dd = U16(d + 2 * k), rr = U16(ro + 2 * k);
        for (int c = ss; c <= ee && c != 0xFFFF; c++) {
          int g = rr == 0 ? (c + dd) & 0xFFFF : U16(ro + 2 * k + rr + 2 * (c - ss));
          if (rr != 0 && g != 0) g = (g + dd) & 0xFFFF;
          if (g != 0) map[c] = g;
        }
      }
    }
    var groups = new Dictionary<int, int>(); var rows = new List<string>();
    foreach (var kv in map) {
      int g = kv.Value;
      if (!groups.ContainsKey(g)) groups[g] = groups.Count;
      int adv = U16(hmtx + 4 * Math.Min(g, nh - 1));
      int a = longLoca != 0 ? U32(loca + 4 * g) : 2 * U16(loca + 2 * g), z = longLoca != 0 ? U32(loca + 4 * g + 4) : 2 * U16(loca + 2 * g + 2);
      string box = a == z ? "null" : "[" + S16(glyf + a + 2) + "," + S16(glyf + a + 6) + "," + S16(glyf + a + 4) + "," + S16(glyf + a + 8) + "]";
      rows.Add("[\"" + kv.Key.ToString("X4") + "\"," + groups[g] + "," + adv + "," + box + "]");
    }
    return "\"upm\":" + U16(head + 18) + ",\"hhea\":[" + S16(hhea + 4) + "," + S16(hhea + 6) + "," + S16(hhea + 8) + "]" +
      ",\"typo\":[" + S16(os2 + 68) + "," + S16(os2 + 70) + "," + S16(os2 + 72) + "],\"win\":[" + U16(os2 + 74) + "," + U16(os2 + 76) + "]" +
      ",\"points\":[" + string.Join(",", rows) + "]";
  }
}
'@
$sha = (Get-FileHash -Algorithm SHA256 $Path).Hash.ToLower()
$ver = (New-Object System.Windows.Media.GlyphTypeface([uri]$Path)).VersionStrings.Values | Select-Object -First 1
'{"sha256":"' + $sha + '","version":"' + $ver + '",' + [Geometry]::Run([IO.File]::ReadAllBytes($Path)) + '}'
