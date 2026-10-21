using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

// Portable process setup only. All agent behavior and tools come from OpenCode.
internal static class PocketAgent
{
    private static readonly string Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);

    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        try { return Launch(args); }
        catch (Exception ex)
        {
            Console.Error.WriteLine("PocketAgent: " + ex.Message);
            if (!Console.IsInputRedirected)
            {
                Console.Error.WriteLine("Press Enter to close.");
                Console.ReadLine();
            }
            return 1;
        }
    }

    private static int Launch(string[] input)
    {
        if (!Environment.Is64BitOperatingSystem)
            throw new InvalidOperationException("Windows 10/11 x64 is required.");

        var args = new List<string>(input);
        var project = Path.Combine(Root, "workspaces", "default");
        if (args.Count > 0 && Directory.Exists(args[0]))
        {
            project = Path.GetFullPath(args[0]);
            args.RemoveAt(0);
        }
        if (args.Count > 0 && args[0] == "--project")
        {
            if (args.Count < 2 || !Directory.Exists(args[1]))
                throw new ArgumentException("--project requires an existing directory.");
            project = Path.GetFullPath(args[1]);
            args.RemoveRange(0, 2);
        }

        var folders = new[] {
            "data/config/opencode", "data/share", "data/cache", "data/state", "data/tmp",
            "data/npm-global", "data/python-user", "data/uv-tools", "data/uv-python",
            "workspaces/default"
        };
        foreach (var folder in folders) Directory.CreateDirectory(Path.Combine(Root, folder));
        foreach (var file in new[] { "opencode.json", "AGENTS.md" })
        {
            var target = Path.Combine(Root, "data/config/opencode", file);
            if (!File.Exists(target)) File.Copy(Path.Combine(Root, "defaults", file), target);
        }
        foreach (var file in new[] { "data/gitconfig", "data/npmrc" })
        {
            var target = Path.Combine(Root, file);
            if (!File.Exists(target)) File.WriteAllText(target, "", new UTF8Encoding(false));
        }

        var bins = new[] {
            "runtime/opencode", "runtime/git/cmd", "runtime/git/bin", "runtime/git/usr/bin",
            "runtime/node", "runtime/python", "runtime/python/Scripts", "runtime/uv", "runtime/ripgrep",
            "data/npm-global"
        };
        var env = new Dictionary<string, string> {
            { "POCKETAGENT_ROOT", Root.TrimEnd(Path.DirectorySeparatorChar) },
            { "XDG_CONFIG_HOME", Path.Combine(Root, "data/config") },
            { "XDG_DATA_HOME", Path.Combine(Root, "data/share") },
            { "XDG_CACHE_HOME", Path.Combine(Root, "data/cache") },
            { "XDG_STATE_HOME", Path.Combine(Root, "data/state") },
            { "OPENCODE_CONFIG_DIR", Path.Combine(Root, "data/config/opencode") },
            { "OPENCODE_DISABLE_AUTOUPDATE", "1" },
            { "OPENCODE_GIT_BASH_PATH", Path.Combine(Root, "runtime/git/bin/bash.exe") },
            { "SHELL", Path.Combine(Root, "runtime/git/bin/bash.exe") },
            { "PWD", project },
            { "GIT_CONFIG_GLOBAL", Path.Combine(Root, "data/gitconfig") },
            { "NPM_CONFIG_CACHE", Path.Combine(Root, "data/cache/npm") },
            { "NPM_CONFIG_PREFIX", Path.Combine(Root, "data/npm-global") },
            { "NPM_CONFIG_USERCONFIG", Path.Combine(Root, "data/npmrc") },
            { "PIP_CACHE_DIR", Path.Combine(Root, "data/cache/pip") },
            { "PYTHONUSERBASE", Path.Combine(Root, "data/python-user") },
            { "PYTHONPYCACHEPREFIX", Path.Combine(Root, "data/cache/pycache") },
            { "UV_CACHE_DIR", Path.Combine(Root, "data/cache/uv") },
            { "UV_TOOL_DIR", Path.Combine(Root, "data/uv-tools") },
            { "UV_PYTHON_INSTALL_DIR", Path.Combine(Root, "data/uv-python") },
            { "TEMP", Path.Combine(Root, "data/tmp") },
            { "TMP", Path.Combine(Root, "data/tmp") },
            { "PATH", string.Join(";", bins.Select(p => Path.Combine(Root, p))) + ";" + Environment.GetEnvironmentVariable("PATH") }
        };

        var executable = Path.Combine(Root, "runtime/opencode/opencode.exe");
        if (!File.Exists(executable)) throw new FileNotFoundException("Extract the complete PocketAgent release ZIP before starting.", executable);
        if (args.Count > 0 && args[0] == "--doctor")
        {
            Console.WriteLine("PocketAgent portable environment\nRoot: " + Root + "\nProject: " + project);
            var checks = new[] {
                new[] { "runtime/opencode/opencode.exe", "--version" },
                new[] { "runtime/git/cmd/git.exe", "--version" },
                new[] { "runtime/node/node.exe", "--version" },
                new[] { "runtime/python/python.exe", "--version" },
                new[] { "runtime/uv/uv.exe", "--version" },
                new[] { "runtime/ripgrep/rg.exe", "--version" }
            };
            foreach (var check in checks)
                if (Run(Path.Combine(Root, check[0]), new[] { check[1] }, project, env) != 0) return 1;
            return Run(executable, new[] { "debug", "paths" }, project, env);
        }
        if (args.Count > 0 && args[0] == "--configure")
            args = new List<string> { "auth", "login" };
        if (args.Count > 0 && args[0] == "--shell")
            return Run(Environment.GetEnvironmentVariable("COMSPEC") ?? "cmd.exe", new[] { "/d", "/k" }, project, env);

        return Run(executable, args, project, env);
    }

    private static int Run(string executable, IEnumerable<string> args, string directory, IDictionary<string, string> env)
    {
        var start = new ProcessStartInfo(executable, string.Join(" ", args.Select(Quote))) {
            UseShellExecute = false,
            WorkingDirectory = directory
        };
        foreach (var pair in env) start.EnvironmentVariables[pair.Key] = pair.Value;
        // Child retains console input/output, so the native OpenCode TUI handles all interaction.
        using (var process = Process.Start(start))
        {
            process.WaitForExit();
            return process.ExitCode;
        }
    }

    // Windows CRT command-line escaping: preserve quotes and trailing backslashes.
    private static string Quote(string value)
    {
        return "\"" + Regex.Replace(value, "(\\\\*)\"", "$1$1\\\"")
            .ReplaceTrailingBackslashes() + "\"";
    }

    private static string ReplaceTrailingBackslashes(this string value)
    {
        return Regex.Replace(value, "(\\\\+)$", "$1$1");
    }
}

