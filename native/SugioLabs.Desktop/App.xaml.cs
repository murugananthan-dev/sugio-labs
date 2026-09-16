using System.Windows;
using SugioLabs.Desktop.Services;

namespace SugioLabs.Desktop;

public partial class App : Application
{
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        if (e.Args.Any(arg => string.Equals(arg, "--self-test", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                await using var backend = new PythonBackendClient();
                await backend.StartAsync();
                var health = await backend.SendAsync("health");
                var healthy = health.TryGetProperty("status", out var status) && status.GetString() == "healthy";
                Shutdown(healthy ? 0 : 2);
            }
            catch
            {
                Shutdown(3);
            }
            return;
        }

        var mainWindow = new MainWindow();
        MainWindow = mainWindow;
        mainWindow.Show();
    }
}
