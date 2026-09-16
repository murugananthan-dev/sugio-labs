using System.IO;
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
            var exitCode = 0;
            try
            {
                await using var backend = new PythonBackendClient();
                await backend.StartAsync();
                var health = await backend.SendAsync("health");
                var healthy = health.TryGetProperty("status", out var status) && status.GetString() == "healthy";
                exitCode = healthy ? 0 : 2;
            }
            catch (Exception ex)
            {
                exitCode = 3;
                var logPath = Environment.GetEnvironmentVariable("SUGIO_SELF_TEST_LOG");
                if (!string.IsNullOrWhiteSpace(logPath))
                {
                    try
                    {
                        var directory = Path.GetDirectoryName(logPath);
                        if (!string.IsNullOrWhiteSpace(directory))
                        {
                            Directory.CreateDirectory(directory);
                        }
                        File.WriteAllText(logPath, ex.ToString());
                    }
                    catch
                    {
                        // Diagnostics must never hide the original self-test result.
                    }
                }
            }

            Shutdown(exitCode);
            return;
        }

        var mainWindow = new MainWindow();
        MainWindow = mainWindow;
        mainWindow.Show();
    }
}
