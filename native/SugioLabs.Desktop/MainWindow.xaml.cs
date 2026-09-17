using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using SugioLabs.Desktop.Services;

namespace SugioLabs.Desktop;

public partial class MainWindow : Window
{
    private readonly PythonBackendClient _backend = new();
    private string _currentQuestionId = string.Empty;
    private string _readyStatusText = "Python backend online";

    public MainWindow()
    {
        InitializeComponent();
        Loaded += Window_Loaded;
        Closed += Window_Closed;
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            SetBusy(true, "Starting Python backend...");
            await _backend.StartAsync();
            BackendStatusDot.Fill = Brushes.MediumSpringGreen;
            _readyStatusText = "Python backend online";
            BackendStatusText.Text = _readyStatusText;
            AddActivity("Python backend started");

            await RefreshSystemAsync();
            await StartInterviewAsync();
        }
        catch (Exception ex)
        {
            BackendStatusDot.Fill = Brushes.IndianRed;
            BackendStatusText.Text = "Backend unavailable";
            MessageBox.Show(
                ex.Message,
                "Sugio Labs could not start",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void Window_Closed(object? sender, EventArgs e)
    {
        await _backend.DisposeAsync();
    }

    private void NavButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string page })
        {
            ShowPage(page);
        }
    }

    private void ShowPage(string page)
    {
        PlanPage.Visibility = Visibility.Collapsed;
        BlueprintPage.Visibility = Visibility.Collapsed;
        ContractsPage.Visibility = Visibility.Collapsed;
        ImpactPage.Visibility = Visibility.Collapsed;
        GitPage.Visibility = Visibility.Collapsed;
        AssistantPage.Visibility = Visibility.Collapsed;
        SystemPage.Visibility = Visibility.Collapsed;

        switch (page)
        {
            case "Blueprint": BlueprintPage.Visibility = Visibility.Visible; break;
            case "Contracts": ContractsPage.Visibility = Visibility.Visible; break;
            case "Impact": ImpactPage.Visibility = Visibility.Visible; break;
            case "Git": GitPage.Visibility = Visibility.Visible; break;
            case "Assistant": AssistantPage.Visibility = Visibility.Visible; break;
            case "System": SystemPage.Visibility = Visibility.Visible; break;
            default: PlanPage.Visibility = Visibility.Visible; page = "Plan"; break;
        }

        PageTitleText.Text = page == "Git" ? "Git Safety" : page;
    }

    private async Task StartInterviewAsync()
    {
        var result = await _backend.SendAsync("interview_start");
        if (result.TryGetProperty("question", out var question))
        {
            LoadQuestion(question);
        }
        ShowPage("Plan");
        await RefreshActivityAsync();
    }

    private void LoadQuestion(JsonElement question)
    {
        _currentQuestionId = question.GetProperty("id").GetString() ?? string.Empty;
        CurrentQuestionText.Text = question.GetProperty("question").GetString() ?? "Planning question";

        var recommended = question.TryGetProperty("recommended_option", out var recommendation)
            ? recommendation.GetString()
            : null;
        var reason = question.TryGetProperty("recommendation_reason", out var recommendationReason)
            ? recommendationReason.GetString()
            : null;
        RecommendationText.Text = string.IsNullOrWhiteSpace(recommended)
            ? "No preset recommendation."
            : $"{recommended}\n{reason}";

        AnswerOptionsCombo.Items.Clear();
        if (question.TryGetProperty("options", out var options) && options.ValueKind == JsonValueKind.Array)
        {
            foreach (var option in options.EnumerateArray())
            {
                AnswerOptionsCombo.Items.Add(option.GetString() ?? string.Empty);
            }
        }

        AnswerOptionsCombo.SelectedIndex = AnswerOptionsCombo.Items.Count > 0 ? 0 : -1;
        CustomAnswerBox.Text = string.Empty;
    }

    private void AnswerOptionsCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (AnswerOptionsCombo.SelectedItem is string selected)
        {
            CustomAnswerBox.Text = selected;
        }
    }

    private async void SubmitAnswerButton_Click(object sender, RoutedEventArgs e)
    {
        var answer = CustomAnswerBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(answer) && AnswerOptionsCombo.SelectedItem is string selected)
        {
            answer = selected;
        }

        if (string.IsNullOrWhiteSpace(_currentQuestionId) || string.IsNullOrWhiteSpace(answer))
        {
            MessageBox.Show("Choose or enter an answer before continuing.", "Planning", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        try
        {
            SetBusy(true, "Python agent is updating the plan...");
            var result = await _backend.SendAsync("interview_answer", new
            {
                question_id = _currentQuestionId,
                answer,
            });

            var status = result.GetProperty("status").GetString();
            if (status == "next_question" && result.TryGetProperty("question", out var question))
            {
                LoadQuestion(question);
            }
            else if (status == "blueprint_ready" && result.TryGetProperty("blueprint", out var blueprint))
            {
                BlueprintTextBox.Text = Pretty(blueprint);
                AddActivity("Architecture blueprint generated");
                ShowPage("Blueprint");
            }

            await RefreshActivityAsync();
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void RestartPlanButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            SetBusy(true, "Restarting plan...");
            await StartInterviewAsync();
            AddActivity("Planning restarted");
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void ApproveBlueprintButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            SetBusy(true, "Generating contract graph...");
            var result = await _backend.SendAsync("blueprint_approve");
            if (result.TryGetProperty("blueprint", out var blueprint))
            {
                BlueprintTextBox.Text = Pretty(blueprint);
            }
            await RefreshContractsAsync();
            await RefreshActivityAsync();
            AddActivity("Blueprint approved; contracts synchronized");
            ShowPage("Contracts");
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void RefreshContractsButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            SetBusy(true, "Refreshing contract graph...");
            await RefreshContractsAsync();
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async Task RefreshContractsAsync()
    {
        var graph = await _backend.SendAsync("contract_graph");
        ContractsList.Items.Clear();

        if (graph.TryGetProperty("nodes", out var nodes) && nodes.ValueKind == JsonValueKind.Array)
        {
            foreach (var node in nodes.EnumerateArray())
            {
                var layer = node.TryGetProperty("layer", out var layerValue) ? layerValue.GetString() : "Layer";
                var name = node.TryGetProperty("name", out var nameValue) ? nameValue.GetString() : "Contract";
                var status = node.TryGetProperty("status", out var statusValue) ? statusValue.GetString() : "unknown";
                var id = node.TryGetProperty("id", out var idValue) ? idValue.GetString() : string.Empty;
                ContractsList.Items.Add($"{layer,-12}  {name,-34}  {status,-18}  {id}");
            }
        }
    }

    private async void RunImpactButton_Click(object sender, RoutedEventArgs e)
    {
        var target = TargetEntityBox.Text.Trim();
        var change = ChangeDescriptionBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(target) || string.IsNullOrWhiteSpace(change))
        {
            MessageBox.Show("Enter both a target and the requested change.", "Impact analysis", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        try
        {
            SetBusy(true, "Python impact analyzer is tracing contracts...");
            var result = await _backend.SendAsync("impact_analysis", new
            {
                target_entity = target,
                change_description = change,
            });
            ImpactOutputBox.Text = Pretty(result);
            await RefreshActivityAsync();

            if (result.TryGetProperty("permission_request", out var permission) &&
                permission.TryGetProperty("id", out var requestIdValue))
            {
                var requestId = requestIdValue.GetString();
                var risk = permission.TryGetProperty("risk_level", out var riskValue) ? riskValue.GetString() : "medium";
                var choice = MessageBox.Show(
                    $"The Python backend requests permission to continue this change.\n\nRisk: {risk}\n\nYes = allow once\nNo = reject\nCancel = decide later",
                    "Permission required",
                    MessageBoxButton.YesNoCancel,
                    MessageBoxImage.Warning);

                if (choice is MessageBoxResult.Yes or MessageBoxResult.No)
                {
                    await _backend.SendAsync("permission_decision", new
                    {
                        request_id = requestId,
                        decision = choice == MessageBoxResult.Yes ? "allow_once" : "reject",
                        reason = choice == MessageBoxResult.No ? "Rejected from native desktop UI" : null,
                    });
                    await RefreshActivityAsync();
                }
            }
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void CreateCheckpointButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            SetBusy(true, "Creating Git checkpoint...");
            await _backend.SendAsync("checkpoint_create", new
            {
                name = string.IsNullOrWhiteSpace(CheckpointNameBox.Text) ? "Checkpoint" : CheckpointNameBox.Text.Trim(),
                description = "Created from native Sugio Labs desktop UI",
            });
            await RefreshGitAsync();
            AddActivity("Git checkpoint created");
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void RefreshGitButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await RefreshGitAsync();
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
    }

    private async Task RefreshGitAsync()
    {
        var checkpoints = await _backend.SendAsync("checkpoint_list");
        CheckpointsList.Items.Clear();
        if (checkpoints.ValueKind == JsonValueKind.Array)
        {
            foreach (var checkpoint in checkpoints.EnumerateArray())
            {
                CheckpointsList.Items.Add(Pretty(checkpoint));
            }
        }

        var diff = await _backend.SendAsync("git_diff");
        DiffTextBox.Text = diff.TryGetProperty("diff", out var diffValue) ? diffValue.GetString() ?? string.Empty : string.Empty;
    }

    private async void SendChatButton_Click(object sender, RoutedEventArgs e)
    {
        var message = ChatInputBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(message))
        {
            return;
        }

        var language = (ChatLanguageCombo.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "en";
        try
        {
            SetBusy(true, "Python assistant is responding...");
            var result = await _backend.SendAsync("chat", new { message, language });
            var reply = result.TryGetProperty("reply", out var replyValue) ? replyValue.GetString() : "No response.";
            ChatOutputBox.Text += $"You:\n{message}\n\nSugio Labs:\n{reply}\n\n────────────────────────\n\n";
            ChatInputBox.Clear();
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void RefreshSystemButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await RefreshSystemAsync();
        }
        catch (Exception ex)
        {
            ShowError(ex);
        }
    }

    private async Task RefreshSystemAsync()
    {
        var health = await _backend.SendAsync("health");
        SystemStatusTextBox.Text = Pretty(health);
        if (health.TryGetProperty("ollama_online", out var ollama))
        {
            _readyStatusText = ollama.GetBoolean()
                ? "Python backend online · Ollama connected"
                : "Python backend online · offline fallback";
            BackendStatusText.Text = _readyStatusText;
        }
    }

    private async Task RefreshActivityAsync()
    {
        var state = await _backend.SendAsync("session_state");
        ActivityList.Items.Clear();

        if (state.TryGetProperty("activity_logs", out var logs) && logs.ValueKind == JsonValueKind.Array)
        {
            foreach (var log in logs.EnumerateArray().Reverse().Take(18))
            {
                var step = log.TryGetProperty("step", out var stepValue) ? stepValue.GetString() : "Activity";
                var agent = log.TryGetProperty("agent_name", out var agentValue) ? agentValue.GetString() : "Python";
                var status = log.TryGetProperty("status", out var statusValue) ? statusValue.GetString() : string.Empty;
                ActivityList.Items.Add($"{agent} · {status}\n{step}");
            }
        }
    }

    private void SetBusy(bool busy, string? status = null)
    {
        SubmitAnswerButton.IsEnabled = !busy;
        ApproveBlueprintButton.IsEnabled = !busy;

        if (busy && !string.IsNullOrWhiteSpace(status))
        {
            BackendStatusText.Text = status;
            return;
        }

        if (!busy && _backend.IsRunning &&
            !string.Equals(BackendStatusText.Text, "Backend unavailable", StringComparison.OrdinalIgnoreCase))
        {
            BackendStatusText.Text = _readyStatusText;
        }
    }

    private void AddActivity(string message)
    {
        ActivityList.Items.Insert(0, $"Desktop\n{message}");
        while (ActivityList.Items.Count > 20)
        {
            ActivityList.Items.RemoveAt(ActivityList.Items.Count - 1);
        }
    }

    private static string Pretty(JsonElement element)
    {
        return JsonSerializer.Serialize(element, new JsonSerializerOptions { WriteIndented = true });
    }

    private static void ShowError(Exception ex)
    {
        MessageBox.Show(ex.Message, "Sugio Labs", MessageBoxButton.OK, MessageBoxImage.Error);
    }
}
