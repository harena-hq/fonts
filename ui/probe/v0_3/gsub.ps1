# SPDX-License-Identifier: Apache-2.0
# Print, as JSON, what Segoe UI Variable's layout features reach, in code points.
# Runs on the machine where the font is installed. Only the file's SHA-256, feature
# and language system tags, and code points leave it: no glyph IDs, lookup
# structure, outlines, advances or positioning values.
#
# Printed: per language system of GSUB and GPOS, its feature tags; Segoe's `dlig`
# as the character sequences its ligatures read and, per contextual rule, the
# characters it changes and the characters that must follow; and the characters
# `frac` reads anywhere. What the rest of the probe relies on is asserted here,
# and a failed assertion prints {"error": ...} instead, with a fixed message that
# names no lookup, type or format: no feature variations, no
# required feature, no lookup flag in what dlig and frac reach, no lookup form other
# than single, ligature and chaining-context (format 3) substitution, every
# chaining context of dlig one input and one lookahead position with no backtrack,
# every glyph dlig reads reachable from a character, and every lookup a dlig
# context applies a single substitution. A glyph with several characters stands for
# all of them in a set, and for its lowest in a ligature sequence. dlig's sequences
# and contexts are the union over language systems; they are Latin, shaped as latn.
# frac reads glyphs no character maps (its own numerators); only mapped ones print.
param([string]$Path = 'C:\Windows\Fonts\SegUIVar.ttf')
Add-Type -Language CSharp -TypeDefinition @'
using System; using System.Collections.Generic; using System.Linq; using System.Text;
public static class Gsub {
  static byte[] b;
  static int U16(int o) { return (b[o] << 8) | b[o + 1]; }
  static int U32(int o) { return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]; }
  static string Tag(int o) { return Encoding.ASCII.GetString(b, o, 4); }
  static Dictionary<int, List<int>> cp = new Dictionary<int, List<int>>();
  static void Map(int g, int c) { if (!cp.ContainsKey(g)) cp[g] = new List<int>(); cp[g].Add(c); }
  class Unmet : Exception { public Unmet(string what) : base(what) { } }
  static void Need(bool ok, string what) { if (!ok) throw new Unmet(what); }
  static List<int> Cov(int o) {
    var r = new List<int>(); int f = U16(o), n = U16(o + 2);
    Need(f == 1 || f == 2, "an unknown coverage format");
    for (int i = 0; i < n; i++) {
      if (f == 1) r.Add(U16(o + 4 + 2 * i));
      else { int q = o + 4 + 6 * i; for (int g = U16(q); g <= U16(q + 2); g++) r.Add(g); }
    }
    return r;
  }
  static IEnumerable<int> Chars(IEnumerable<int> gs) {
    return gs.Where(g => cp.ContainsKey(g)).SelectMany(g => cp[g]);
  }
  static string Set(IEnumerable<int> cs) { return "[" + string.Join(",", cs.Distinct().OrderBy(c => c)) + "]"; }

  static int ll;
  // (type, subtable offset) for every subtable of a lookup, extensions resolved
  static List<KeyValuePair<int, int>> Subtables(int li, out int flag) {
    int lo = ll + U16(ll + 2 + 2 * li), ty = U16(lo); flag = U16(lo + 2);
    var r = new List<KeyValuePair<int, int>>();
    for (int s = 0; s < U16(lo + 4); s++) {
      int so = lo + U16(lo + 6 + 2 * s), t = ty;
      if (t == 7) { Need(U16(so) == 1, "an unknown extension format"); t = U16(so + 2); so = so + U32(so + 4); }
      r.Add(new KeyValuePair<int, int>(t, so));
    }
    return r;
  }

  public static string Run(byte[] bytes) {
    try { return Inner(bytes); }
    // an assertion's message is fixed text; any other failure says only that it failed
    catch (Unmet e) {
      var m = new string(e.Message.Where(ch => ch >= ' ' && ch != '\\' && ch != '"').ToArray());
      return "{\"error\":\"" + m + "\"}";
    }
    catch (Exception) { return "{\"error\":\"the reader failed\"}"; }
  }

  static string Inner(byte[] bytes) {
    b = bytes; var tabs = new Dictionary<string, int>();
    for (int i = 0; i < U16(4); i++) tabs[Tag(12 + 16 * i)] = U32(12 + 16 * i + 8);
    // the (3,10) format 12 subtable if there is one, else (3,1) format 4
    int cm = tabs["cmap"], t12 = -1, t4 = -1;
    for (int i = 0; i < U16(cm + 2); i++) {
      int r = cm + 4 + 8 * i, t = cm + U32(r + 4);
      if (U16(r) == 3 && U16(r + 2) == 10 && U16(t) == 12) t12 = t;
      if (U16(r) == 3 && U16(r + 2) == 1 && U16(t) == 4) t4 = t;
    }
    if (t12 >= 0) {
      for (int k = 0; k < U32(t12 + 12); k++) {
        int q = t12 + 16 + 12 * k, s = U32(q), e = U32(q + 4), gid = U32(q + 8);
        for (int c = s; c <= e; c++) Map(gid + c - s, c);
      }
    } else {
      int seg = U16(t4 + 6) / 2, ends = t4 + 14, starts = ends + 2 * seg + 2, deltas = starts + 2 * seg, ranges = deltas + 2 * seg;
      for (int i = 0; i < seg; i++) {
        int e = U16(ends + 2 * i), s = U16(starts + 2 * i), d = U16(deltas + 2 * i), ro = U16(ranges + 2 * i);
        for (int c = s; c <= e && c != 0xFFFF; c++) {
          int g = ro == 0 ? (c + d) & 0xFFFF : U16(ranges + 2 * i + ro + 2 * (c - s));
          if (ro != 0 && g != 0) g = (g + d) & 0xFFFF;
          if (g != 0) Map(g, c);
        }
      }
    }
    var o = new StringBuilder("{");
    var reach = new Dictionary<string, SortedSet<int>> { { "dlig", new SortedSet<int>() }, { "frac", new SortedSet<int>() } };
    foreach (var tn in new[] { "GSUB", "GPOS" }) {
      int bs = tabs[tn], sl = bs + U16(bs + 4), fl = bs + U16(bs + 6);
      Need(U16(bs + 2) == 0 || U32(bs + 10) == 0, tn + " has feature variations");
      var sys = new List<string>();
      for (int i = 0; i < U16(sl); i++) {
        int r = sl + 2 + 6 * i, so = sl + U16(r + 4);
        var ls = new List<KeyValuePair<string, int>>();
        if (U16(so) != 0) ls.Add(new KeyValuePair<string, int>("dflt", so + U16(so)));
        for (int j = 0; j < U16(so + 2); j++) ls.Add(new KeyValuePair<string, int>(Tag(so + 4 + 6 * j).TrimEnd(), so + U16(so + 8 + 6 * j)));
        foreach (var l in ls) {
          Need(U16(l.Value + 2) == 0xFFFF, tn + " has a required feature");
          var fs = new SortedSet<string>();
          for (int k = 0; k < U16(l.Value + 4); k++) {
            int fr = fl + 2 + 6 * U16(l.Value + 6 + 2 * k), fo = fl + U16(fr + 4); string tag = Tag(fr);
            fs.Add(tag);
            if (tn == "GSUB" && reach.ContainsKey(tag))
              for (int m = 0; m < U16(fo + 2); m++) reach[tag].Add(U16(fo + 4 + 2 * m));
          }
          sys.Add("\"" + Tag(r) + "/" + l.Key + "\":[" + string.Join(",", fs.Select(f => "\"" + f + "\"")) + "]");
        }
      }
      o.Append("\"" + tn + "\":{" + string.Join(",", sys) + "},");
      if (tn == "GSUB") ll = bs + U16(bs + 8);
    }
    // dlig: ligature sequences and contexts; frac: every character it reads
    var seqs = new SortedSet<string>(); var ctxs = new SortedSet<string>(); var frac = new SortedSet<int>();
    foreach (var feat in new[] { "dlig", "frac" }) {
      var todo = new Queue<int>(reach[feat]); var seen = new HashSet<int>(); var applied = new HashSet<int>();
      while (todo.Count > 0) {
        int li = todo.Dequeue(); if (!seen.Add(li)) continue;
        int flag; var subs = Subtables(li, out flag);
        Need(flag == 0, feat + " has a lookup flag");
        foreach (var st in subs) {
          int t = st.Key, so = st.Value, f = U16(so);
          var read = new List<int>();
          if (feat == "dlig" && applied.Contains(li) && !reach[feat].Contains(li))
            Need(t == 1, "a dlig context applies a lookup other than single substitution");
          if (t == 1) read.AddRange(Cov(so + U16(so + 2)));
          else if (t == 4) {
            Need(f == 1, "an unknown ligature substitution format");
            var cv = Cov(so + U16(so + 2)); read.AddRange(cv);
            for (int i = 0; i < U16(so + 4); i++) {
              int ls = so + U16(so + 6 + 2 * i);
              for (int j = 0; j < U16(ls); j++) {
                int lg = ls + U16(ls + 2 + 2 * j), n = U16(lg + 2); var seq = new List<int> { cv[i] };
                for (int k = 1; k < n; k++) seq.Add(U16(lg + 2 + 2 * k));
                read.AddRange(seq);
                Need(seq.All(g => cp.ContainsKey(g)), feat + " ligature reads a glyph no character maps");
                if (feat == "dlig") seqs.Add("[" + string.Join(",", seq.Select(g => cp[g].Min())) + "]");
              }
            }
          } else if (t == 6 && f == 3) {
            int p = so + 2; var parts = new List<List<int>>[3];
            for (int x = 0; x < 3; x++) {
              parts[x] = new List<List<int>>();
              for (int i = 0; i < U16(p); i++) { var c = Cov(so + U16(p + 2 + 2 * i)); parts[x].Add(c); read.AddRange(c); }
              p += 2 + 2 * U16(p);
            }
            for (int i = 0; i < U16(p); i++) { todo.Enqueue(U16(p + 4 + 4 * i)); applied.Add(U16(p + 4 + 4 * i)); }
            if (feat == "dlig") {
              Need(parts[0].Count == 0 && parts[1].Count == 1 && parts[2].Count == 1, "dlig context of another shape");
              Need(parts[1][0].Concat(parts[2][0]).All(g => cp.ContainsKey(g)), "dlig context reads a glyph no character maps");
              ctxs.Add("{\"input\":" + Set(Chars(parts[1][0])) + ",\"lookahead\":" + Set(Chars(parts[2][0])) + "}");
            }
          } else Need(false, feat + " uses a lookup form this does not read");
          if (feat == "frac") foreach (var c in Chars(read)) frac.Add(c);
        }
      }
    }
    o.Append("\"dlig\":{\"sequences\":[" + string.Join(",", seqs) + "],\"contexts\":[" + string.Join(",", ctxs) + "]},");
    o.Append("\"frac\":{\"reads\":" + Set(frac) + "}}");
    return o.ToString();
  }
}
'@
$sha = (Get-FileHash -Algorithm SHA256 $Path).Hash.ToLower()
'{"sha256":"' + $sha + '",' + ([Gsub]::Run([IO.File]::ReadAllBytes($Path))).Substring(1)
