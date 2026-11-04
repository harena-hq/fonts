// SPDX-License-Identifier: Apache-2.0
// Lay out each case as a WinUI 3 TextBlock, with the default style an app gets from
// XamlControlsResources, and write the width WinUI gives it, unrounded, in px.
//
// Usage: Measure.exe <cases.json> <out.json>
// cases.json: [{"key", "text", "lang" ("" for none), "weight", "size"}]; out.json: {key: width}.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Text;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Markup;
using Microsoft.UI.Xaml.XamlTypeInfo;
using Windows.UI.Text;

record Case(string key, string text, string lang, int weight, double size);

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        AppDomain.CurrentDomain.UnhandledException += (_, e) => Fail(e.ExceptionObject);
        WinRT.ComWrappersSupport.InitializeComWrappers();
        Application.Start(_ =>
        {
            SynchronizationContext.SetSynchronizationContext(
                new DispatcherQueueSynchronizationContext(DispatcherQueue.GetForCurrentThread()));
            var app = new App(args);
            app.UnhandledException += (_, e) => Fail(e.Exception);
        });
    }

    // Why the run stopped, beside the output it did not write.
    public static void Fail(object error) => File.WriteAllText(Environment.GetCommandLineArgs()[^1] + ".err", error.ToString());
}

// With no XAML compiled, the app finds the controls' resources through their own metadata provider.
class App : Application, IXamlMetadataProvider
{
    const int Batch = 2000;
    readonly string[] args;
    readonly XamlControlsXamlMetaDataProvider provider = new();
    Window window;

    public App(string[] args) => this.args = args;

    public IXamlType GetXamlType(Type type) => provider.GetXamlType(type);
    public IXamlType GetXamlType(string fullName) => provider.GetXamlType(fullName);
    public XmlnsDefinition[] GetXmlnsDefinitions() => provider.GetXmlnsDefinitions();

    protected override void OnLaunched(LaunchActivatedEventArgs e)
    {
        try { Launch(); } catch (Exception error) { Program.Fail(error); Exit(); }
    }

    void Launch()
    {
        Resources.MergedDictionaries.Add(new XamlControlsResources());
        var panel = new StackPanel { UseLayoutRounding = false };
        window = new Window { Content = new ScrollViewer { Content = panel } };
        panel.Loaded += (_, _) => Run(panel);
        window.Activate();
    }

    void Run(StackPanel panel)
    {
        var cases = JsonSerializer.Deserialize<List<Case>>(File.ReadAllText(args[0]));
        var widths = new Dictionary<string, double>();
        for (int i = 0; i < cases.Count; i += Batch)
        {
            var blocks = new List<(string, TextBlock)>();
            foreach (var c in cases.GetRange(i, Math.Min(Batch, cases.Count - i)))
            {
                var block = new TextBlock
                {
                    Text = c.text,
                    FontSize = c.size,
                    FontWeight = new FontWeight((ushort)c.weight),
                    UseLayoutRounding = false,
                    HorizontalAlignment = HorizontalAlignment.Left,
                };
                if (c.lang != "") block.Language = c.lang;
                panel.Children.Add(block);
                blocks.Add((c.key, block));
            }
            panel.UpdateLayout();
            foreach (var (key, block) in blocks) widths[key] = block.ActualWidth;
            panel.Children.Clear();
        }
        File.WriteAllText(args[1], JsonSerializer.Serialize(widths));
        Exit();
    }
}
