"use client";

import { useChat } from "@ai-sdk/react";
import { useEffect, useState, useCallback, FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface Task {
  id: string;
  agentRole: string;
  agentName: string | null;
  description: string;
  status: "pending" | "running" | "completed" | "failed";
  result: string | null;
  createdAt: number;
  updatedAt: number;
}

function statusColor(status: string) {
  switch (status) {
    case "pending":
      return "bg-zinc-600 text-zinc-200";
    case "running":
      return "bg-blue-600 text-blue-100 animate-pulse";
    case "completed":
      return "bg-emerald-600 text-emerald-100";
    case "failed":
      return "bg-rose-600 text-rose-100";
    default:
      return "bg-zinc-600 text-zinc-200";
  }
}

function getTextContent(parts: Array<{ type: string; text?: string }>): string {
  return parts
    .filter((p) => p.type === "text" && p.text)
    .map((p) => p.text)
    .join("");
}

function getToolParts(
  parts: Array<{ type: string; toolCallId?: string; input?: Record<string, unknown> }>
) {
  return parts.filter((p) => p.type.startsWith("tool-"));
}

export default function Home() {
  const { messages, sendMessage, status } = useChat();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch("/api/tasks");
      if (res.ok) {
        setTasks(await res.json());
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 2000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || status !== "ready") return;
    sendMessage({ text: input });
    setInput("");
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* LEFT: Chat */}
      <div className="flex flex-1 flex-col border-r border-zinc-800">
        <div className="border-b border-zinc-800 px-6 py-4">
          <h1 className="text-lg font-semibold text-zinc-100">Orchestrator</h1>
          <p className="text-xs text-zinc-500">AgentHQ</p>
        </div>

        <ScrollArea className="flex-1 px-6 py-4">
          <div className="space-y-4 pb-4">
            {messages.length === 0 && (
              <p className="text-sm text-zinc-500">
                Skriv ett meddelande för att börja...
              </p>
            )}
            {messages.map((m) => {
              const text = getTextContent(m.parts as Array<{ type: string; text?: string }>);
              const toolParts = getToolParts(
                m.parts as Array<{ type: string; toolCallId?: string; input?: Record<string, unknown> }>
              );

              return (
                <div key={m.id}>
                  {m.role === "user" ? (
                    <div className="flex justify-end">
                      <div className="max-w-[80%] rounded-lg bg-zinc-800 px-4 py-2 text-sm text-zinc-100">
                        {text}
                      </div>
                    </div>
                  ) : (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] space-y-2">
                        {text && (
                          <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-200">
                            {text}
                          </div>
                        )}
                        {toolParts.map((p) => {
                          const input = (p as { input?: Record<string, string> }).input;
                          return (
                            <Badge
                              key={p.toolCallId}
                              variant="outline"
                              className="border-zinc-700 font-mono text-xs text-zinc-400"
                            >
                              → Delegated: {input?.agent_role ?? "unknown"}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>

        <form onSubmit={handleSubmit} className="border-t border-zinc-800 px-6 py-4">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Skriv ett meddelande..."
              className="flex-1 border-zinc-700 bg-zinc-900 text-zinc-100 placeholder:text-zinc-500"
            />
            <Button
              type="submit"
              disabled={status !== "ready" || !input.trim()}
              className="bg-zinc-100 text-zinc-900 hover:bg-zinc-200"
            >
              Skicka
            </Button>
          </div>
        </form>
      </div>

      {/* RIGHT: Agents sidebar */}
      <div className="w-96 flex-shrink-0 overflow-y-auto p-4">
        <h2 className="mb-4 text-lg font-semibold text-zinc-100">Agents</h2>
        {tasks.length === 0 && (
          <p className="text-sm text-zinc-500">Inga agenter arbetar ännu.</p>
        )}
        <div className="space-y-3">
          {tasks.map((task) => (
            <Card
              key={task.id}
              className="cursor-pointer border-zinc-800 bg-zinc-900 transition-colors hover:bg-zinc-800/50"
              onClick={() =>
                task.status === "completed"
                  ? setExpandedTask(expandedTask === task.id ? null : task.id)
                  : undefined
              }
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-zinc-200">
                    {task.agentName ?? task.agentRole}
                  </CardTitle>
                  <Badge className={`text-xs ${statusColor(task.status)}`}>
                    {task.status}
                  </Badge>
                </div>
                <CardDescription className="line-clamp-2 text-xs text-zinc-500">
                  {task.description}
                </CardDescription>
              </CardHeader>
              {expandedTask === task.id && task.result && (
                <CardContent className="pt-0">
                  <div className="whitespace-pre-wrap rounded bg-zinc-950 p-3 text-xs text-zinc-300">
                    {task.result}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
