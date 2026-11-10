import { streamText, tool, stepCountIs } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { z } from "zod";
import { randomUUID } from "crypto";
import { db } from "@/lib/db";
import { tasks } from "@/lib/db/schema";
import { runTaskInBackground } from "@/lib/agents/run";

const MODEL_ID = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6";

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: anthropic(MODEL_ID),
    stopWhen: stepCountIs(5),
    system:
      "You are AgentHQ, the orchestrator for a Swedish ecommerce operator. You coordinate specialized sub-agents to do work in the background. When a request needs specialized work, call the delegate_task tool. Available agent_role values: 'research'. Keep your own replies short and direct — confirm what you delegated and tell the user they can watch progress in the sidebar. Always reply in Swedish.",
    messages,
    tools: {
      delegate_task: tool({
        description:
          "Delegate a task to a specialized sub-agent. Use this when the user's request needs research or specialized work.",
        inputSchema: z.object({
          agent_role: z.string().describe("The role of the agent to delegate to"),
          task_description: z
            .string()
            .describe("A clear description of the task to perform"),
        }),
        execute: async ({ agent_role, task_description }) => {
          const taskId = randomUUID();
          await db.insert(tasks).values({
            id: taskId,
            agentRole: agent_role,
            description: task_description,
            status: "pending",
            result: null,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          });

          runTaskInBackground(taskId);

          return { taskId, delegated_to: agent_role };
        },
      }),
    },
    onError({ error }) {
      console.error("streamText error:", error);
    },
  });

  return result.toUIMessageStreamResponse();
}
