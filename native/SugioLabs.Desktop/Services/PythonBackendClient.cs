using System.Diagnostics;
using System.Text.Json;

namespace SugioLabs.Desktop.Services;

public sealed class PythonBackendClient : IAsyncDisposable
{
    private readonly SemaphoreSlim _gate = new(1, 1);
    private Process? _process;
    private int _sequence;

    public bool IsRunning => _process is { HasExited: false };

    public async Task StartAsync()
    {
        if (IsRunning)
        {
            return;
        }

        var baseDir = AppContext.BaseDirectory;
        var candidates = new[]
        {
            Path.Combine(baseDir, "engine", "SugioLabsEngine.exe"),
            Path.Combine(baseDir, "SugioLabsEngine.exe"),
        };

        var enginePath = candidates.FirstOrDefault(File.Exists)
            ?? throw new FileNotFoundException("Sugio Labs Python backend executable was not found.", candidates[0]);

        var startInfo = new ProcessStartInfo
        {
            FileName = enginePath,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
        };

        startInfo.Environment["PYTHONUTF8"] = "1";
        startInfo.Environment["SUGIO_DESKTOP"] = "1";

        _process = new Process
        {
            StartInfo = startInfo,
            EnableRaisingEvents = true,
        };

        if (!_process.Start())
        {
            throw new InvalidOperationException("Sugio Labs Python backend could not be started.");
        }

        _ = Task.Run(async () =>
        {
            while (_process is { HasExited: false })
            {
                var line = await _process.StandardError.ReadLineAsync();
                if (line is null)
                {
                    break;
                }
                Debug.WriteLine($"[Python] {line}");
            }
        });

        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        while (!timeout.IsCancellationRequested)
        {
            try
            {
                var result = await SendAsync("ping", cancellationToken: timeout.Token);
                if (result.TryGetProperty("status", out var status) && status.GetString() == "ok")
                {
                    return;
                }
            }
            catch when (!timeout.IsCancellationRequested)
            {
                await Task.Delay(200, timeout.Token);
            }
        }

        throw new TimeoutException("Sugio Labs Python backend did not become ready.");
    }

    public async Task<JsonElement> SendAsync(
        string command,
        object? payload = null,
        CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            if (_process is null || _process.HasExited)
            {
                throw new InvalidOperationException("Python backend is not running.");
            }

            var id = Interlocked.Increment(ref _sequence).ToString();
            var request = JsonSerializer.Serialize(new
            {
                id,
                command,
                payload = payload ?? new { },
            });

            await _process.StandardInput.WriteLineAsync(request.AsMemory(), cancellationToken);
            await _process.StandardInput.FlushAsync(cancellationToken);

            var line = await _process.StandardOutput.ReadLineAsync(cancellationToken);
            if (string.IsNullOrWhiteSpace(line))
            {
                throw new InvalidOperationException("Python backend closed the IPC stream unexpectedly.");
            }

            using var document = JsonDocument.Parse(line);
            var root = document.RootElement;

            if (!root.TryGetProperty("id", out var responseId) || responseId.GetString() != id)
            {
                throw new InvalidOperationException("Python backend returned an invalid IPC response.");
            }

            if (!root.GetProperty("ok").GetBoolean())
            {
                var message = root.TryGetProperty("error", out var error) &&
                              error.TryGetProperty("message", out var errorMessage)
                    ? errorMessage.GetString()
                    : "Unknown Python backend error.";
                throw new InvalidOperationException(message);
            }

            return root.GetProperty("result").Clone();
        }
        finally
        {
            _gate.Release();
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_process is null)
        {
            _gate.Dispose();
            return;
        }

        try
        {
            if (!_process.HasExited)
            {
                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                try
                {
                    await SendAsync("shutdown", cancellationToken: cts.Token);
                }
                catch
                {
                    // Best-effort graceful shutdown.
                }
            }
        }
        finally
        {
            if (!_process.HasExited)
            {
                _process.Kill(entireProcessTree: true);
            }
            _process.Dispose();
            _process = null;
            _gate.Dispose();
        }
    }
}
