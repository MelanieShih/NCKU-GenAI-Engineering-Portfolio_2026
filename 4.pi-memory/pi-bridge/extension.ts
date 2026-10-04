import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

function resolvePython(): string {
  if (process.env.PYTHON?.trim()) {
    return process.env.PYTHON.trim();
  }

  const venv = process.env.VIRTUAL_ENV?.trim();
  if (venv) {
    const candidate = process.platform === "win32"
      ? join(venv, "Scripts", "python.exe")
      : join(venv, "bin", "python");
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

const PY = resolvePython();
const REPO_ROOT = fileURLToPath(new URL("..", import.meta.url));

type MemoryCallResult = {
  ok: boolean;
  command: string;
  stdout: string;
  stderr: string;
  output: string;
  error?: string;
};

type NotifyLevel = "info" | "warning" | "error";

function stripBom(text: string): string {
  return text.replace(/^\uFEFF/, "");
}

function callMemory(args: string[]): MemoryCallResult {
  const result = spawnSync(PY, ["-m", "memory.cli", ...args], {
    encoding: "utf8",
    cwd: REPO_ROOT,
    env: { ...process.env, PYTHONPATH: REPO_ROOT },
  });
  const stdout = stripBom((result.stdout ?? "").trim());
  const stderr = stripBom((result.stderr ?? "").trim());
  const error = result.error?.message;
  const output = stdout || stderr || error || "";
  const command = [PY, "-m", "memory.cli", ...args].join(" ");
  return {
    ok: result.status === 0 && !result.error,
    command,
    stdout,
    stderr,
    output,
    error,
  };
}

function formatCliError(result: MemoryCallResult): string {
  return [
    "Python memory CLI failed.",
    `command: ${result.command}`,
    result.error ? `error: ${result.error}` : undefined,
    result.stderr ? `stderr: ${result.stderr}` : `output: ${result.output || "(empty)"}`,
    "Please confirm you started Pi from the repo root and set PYTHONPATH=.",
  ].filter(Boolean).join("\n");
}

function showCommandMessage(ctx: { hasUI: boolean; ui: { notify: (message: string, level?: NotifyLevel) => void } }, message: string, level: NotifyLevel = "info"): void {
  if (ctx.hasUI) {
    ctx.ui.notify(message, level);
    return;
  }
  if (level === "error") {
    console.error(message);
    return;
  }
  console.log(message);
}

function formatMemoryItem(item: Record<string, unknown>, index: number): string {
  const id = typeof item.id === "string" ? item.id : "unknown";
  const shortId = id.slice(0, 8);
  const summary = typeof item.summary === "string" && item.summary.trim()
    ? item.summary.trim()
    : "(no summary)";
  const rawTags = Array.isArray(item.tags) ? item.tags.filter((tag) => typeof tag === "string") as string[] : [];
  const tags = rawTags.length > 0 ? rawTags.join(", ") : "(none)";
  return `${index + 1}. [${shortId}] ${summary}\n   tags: ${tags}`;
}

function formatRecallOutput(jsonText: string): string {
  try {
    const parsed = JSON.parse(stripBom(jsonText));
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return "No memories found.";
    }
    return parsed
      .map((item, index) => formatMemoryItem(item as Record<string, unknown>, index))
      .join("\n");
  } catch {
    return jsonText || "No memories found.";
  }
}

function parseRecallArgs(args: string): string[] {
  const trimmed = args.trim();
  if (!trimmed || trimmed === "--list") {
    return ["recall", "--list", "20"];
  }

  const tokens = trimmed.split(/\s+/);
  let mode: string | null = null;
  const queryTokens: string[] = [];

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "--list") {
      return ["recall", "--list", "20"];
    }
    if (token === "--mode") {
      const next = tokens[index + 1];
      if (next === "bm25" || next === "hybrid") {
        mode = next;
        index += 1;
        continue;
      }
    }
    queryTokens.push(token);
  }

  if (queryTokens.length === 0) {
    return ["recall", "--list", "20"];
  }

  const cliArgs = ["recall", "--query", queryTokens.join(" "), "--k", "5"];
  if (mode) {
    cliArgs.push("--mode", mode);
  }
  return cliArgs;
}

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event, _ctx) => {
    const query = (event.prompt ?? "").trim();
    if (!query) return;
    const response = callMemory(["inject", "--query", query, "--budget", "2000"]);
    if (!response.ok || !response.output) return;
    return {
      message: {
        customType: "pi-memory",
        content: response.output,
        display: true,
      },
    };
  });

  pi.registerTool({
    name: "remember",
    label: "Remember",
    description:
      "Use this when the user gives durable project conventions, preferences, or facts " +
      "that should persist across sessions.",
    promptGuidelines: [
      "Remember stable project facts that will help future sessions.",
    ],
    parameters: Type.Object({
      summary: Type.String({ description: "One-sentence memory to store." }),
      tags: Type.Optional(Type.Array(Type.String())),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const tags = (params.tags ?? []).join(",");
      const response = callMemory(["capture", "--summary", params.summary, "--tags", tags]);
      return {
        content: [{ type: "text", text: response.output || `Remembered: ${params.summary}` }],
        details: {},
      };
    },
  });

  pi.registerCommand("recall", {
    description: "Recall memories. Usage: /recall, /recall --list, /recall <query>, /recall <query> --mode hybrid",
    handler: async (args, _ctx) => {
      const response = callMemory(parseRecallArgs(args ?? ""));
      if (!response.ok) {
        showCommandMessage(_ctx, formatCliError(response), "error");
        return;
      }
      showCommandMessage(_ctx, formatRecallOutput(response.stdout), "info");
    },
  });

  pi.registerCommand("forget", {
    description: "Delete a memory by id. Usage: /forget <memory_id>",
    handler: async (args, _ctx) => {
      const memoryId = (args ?? "").trim();
      if (!memoryId) {
        showCommandMessage(_ctx, "Usage: /forget <memory_id>", "warning");
        return;
      }
      const response = callMemory(["forget", "--id", memoryId]);
      if (!response.ok) {
        showCommandMessage(_ctx, formatCliError(response), "error");
        return;
      }
      showCommandMessage(_ctx, `Forgot memory: ${memoryId}`, "info");
    },
  });
}
