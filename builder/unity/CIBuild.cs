using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace JNI.Editor.CI
{
    public static class CIBuild
    {
        private const string targetArg = "target";
        private const string il2cppArg = "il2cpp";
        private const string il2cppConfigArg = "il2cppCompilerConfiguration";
        private const string outputArg = "output";

        public static void Build()
        {
            Log($"Starting build");

            string[] args = Environment.GetCommandLineArgs();
            Dictionary<string, string> parsedArgs = new Dictionary<string, string>();
            for(int i = 0;i < args.Length;i++)
            {
                if(args[i].StartsWith("-"))
                {
                    string key = args[i].TrimStart('-');
                    string value = (i + 1 < args.Length && args[i + 1].StartsWith("-") == false) ? args[i + 1] : null;
                    parsedArgs[key] = value;
                }
            }

            BuildData data = new BuildData();
            if(parsedArgs.TryGetValue(targetArg, out string targetStr) == false || targetStr == null || Enum.TryParse(targetStr, out BuildTarget target) == false)
            {
                Log($"Argument {targetArg} is missing or invalid!");
                EditorApplication.Exit(1);
                return;
            }
            if(target != BuildTarget.StandaloneWindows && target != BuildTarget.StandaloneWindows64 && target != BuildTarget.StandaloneLinux64)
            {
                Log($"Platform {target} is not supported!");
                EditorApplication.Exit(1);
                return;
            }
            if(parsedArgs.TryGetValue(outputArg, out string output) == false || string.IsNullOrEmpty(output))
            {
                Log($"Argument {outputArg} is missing!");
                EditorApplication.Exit(1);
                return;
            }

            data.Target = target;
            data.IL2CPP = parsedArgs.TryGetValue(il2cppArg, out string il2cppString) && il2cppString?.ToLower() == "true";
            data.IL2CPPConfig = parsedArgs.GetValueOrDefault(il2cppConfigArg, "").ToLower() switch
            {
                "master" => Il2CppCompilerConfiguration.Master,
                "release" => Il2CppCompilerConfiguration.Release,
                "debug" => Il2CppCompilerConfiguration.Debug,
                _ => Il2CppCompilerConfiguration.Master
            };
            data.OutputFolder = output;
            string fileName = $"{Application.productName.Replace(" ", "")}{GetExtension(target)}";
            Compile(data, fileName);

            Log($"Completed build");
        }

        private static void Compile(BuildData data, string fileName)
        {
            Log($"Compile Params:\ntarget = {data.Target}\nil2cpp = {data.IL2CPP}\nil2cpp config = {data.IL2CPPConfig}\noutput = {data.OutputFolder}");

            NamedBuildTarget namedTarget = NamedBuildTarget.Standalone;
            ScriptingImplementation prevBackend = UnityEditor.PlayerSettings.GetScriptingBackend(namedTarget);
            Il2CppCompilerConfiguration prevCompilerConfig = UnityEditor.PlayerSettings.GetIl2CppCompilerConfiguration(namedTarget);

            string tmpDir = null;
            try
            {
                //Settings
                Log($"Apply settings");
                bool il2cpp = data.IL2CPP && IL2CPPSupported(data.Target);
                EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Standalone, data.Target);
                UnityEditor.PlayerSettings.SetScriptingBackend(namedTarget, il2cpp ? ScriptingImplementation.IL2CPP : ScriptingImplementation.Mono2x);
                if(il2cpp)
                {
                    UnityEditor.PlayerSettings.SetIl2CppCompilerConfiguration(namedTarget, data.IL2CPPConfig);
                }
                string[] additionalDefines = new string[] { "STEAM_BUILD" };

                //Temporary build directory
                Log($"Create build directory");
                tmpDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
                Directory.CreateDirectory(tmpDir);
                string tmpPath = Path.Combine(tmpDir, fileName);

                //Build
                Log($"Compile");
                BuildPlayerOptions options = new BuildPlayerOptions();
                options.scenes = GetScenePaths();
                options.locationPathName = tmpPath;
                options.targetGroup = BuildPipeline.GetBuildTargetGroup(data.Target);
                options.target = data.Target;
                options.options = BuildOptions.None;
                options.extraScriptingDefines = additionalDefines;
                UnityEditor.Build.Reporting.BuildReport report = BuildPipeline.BuildPlayer(options);
                Log($"Build completed with result {report.summary.result} in {report.summary.totalTime.Seconds}s");
                if(report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
                {
                    EditorApplication.Exit(1);
                    return;
                }

                //Copy
                try
                {
                    Log($"Copy dir to destination {tmpDir} -> {data.OutputFolder}");
                    CopyDirContents(tmpDir, data.OutputFolder);

                    List<string> foldersToDelete = new List<string>();
                    foreach(string d in Directory.GetDirectories(data.OutputFolder))
                    {
                        if(d.Contains("BackUpThisFolder") || d.EndsWith("_DoNotShip"))
                        {
                            foldersToDelete.Add(d);
                        }
                    }
                    foldersToDelete.ForEach(n => Directory.Delete(n, true));
                }
                catch(Exception e)
                {
                    Log($"Could not copy build to output folder {data.OutputFolder} ({e.Message})");
                    EditorApplication.Exit(1);
                    return;
                }
            }
            finally
            {
                try
                {
                    Directory.Delete(tmpDir, true);
                }
                catch
                {
                    Log($"(Warning) Could not delete tmp build directory! ({tmpDir})");
                }

                Log($"Restore settings");
                UnityEditor.PlayerSettings.SetScriptingBackend(namedTarget, prevBackend);
                UnityEditor.PlayerSettings.SetIl2CppCompilerConfiguration(namedTarget, prevCompilerConfig);
            }
        }

        private static string GetExtension(BuildTarget target) => target switch
        {
            BuildTarget.StandaloneWindows => ".exe",
            BuildTarget.StandaloneWindows64 => ".exe",
            BuildTarget.StandaloneLinux64 => ".x86_64",
            _ => null
        };

        private static bool IL2CPPSupported(BuildTarget target)
            => target == BuildTarget.StandaloneWindows64 || target == BuildTarget.StandaloneWindows || target == BuildTarget.StandaloneLinux64;

        private static string[] GetScenePaths()
            => EditorBuildSettings.scenes.Select(n => n.path).ToArray();

        private static void CopyDirContents(string sourceDirectory, string targetDirectory)
            => CopyAll(new DirectoryInfo(sourceDirectory), new DirectoryInfo(targetDirectory));

        private static void CopyAll(DirectoryInfo source, DirectoryInfo target)
        {
            Directory.CreateDirectory(target.FullName);
            foreach(FileInfo fi in source.GetFiles())
            {
                fi.CopyTo(Path.Combine(target.FullName, fi.Name), true);
            }
            foreach(DirectoryInfo diSourceSubDir in source.GetDirectories())
            {
                DirectoryInfo nextTargetSubDir = target.CreateSubdirectory(diSourceSubDir.Name);
                CopyAll(diSourceSubDir, nextTargetSubDir);
            }
        }

        private static void Log(string message)
            => Console.WriteLine($"[CIBuild] {message}");
    }

    public class BuildData
    {
        public BuildTarget Target { get; set; }
        public bool IL2CPP { get; set; }
        public Il2CppCompilerConfiguration IL2CPPConfig { get; set; }
        public string OutputFolder { get; set; }
    }
}
