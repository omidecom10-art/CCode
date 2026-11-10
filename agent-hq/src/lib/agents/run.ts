import { generateText } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { db } from "@/lib/db";
import { tasks, agents } from "@/lib/db/schema";
import { eq } from "drizzle-orm";

const MODEL_ID = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6";

export async function runTaskInBackground(taskId: string) {
  try {
    await db
      .update(tasks)
      .set({ status: "running", updatedAt: Date.now() })
      .where(eq(tasks.id, taskId));

    const task = await db.select().from(tasks).where(eq(tasks.id, taskId)).get();
    if (!task) throw new Error("Task not found");

    const agent = await db
      .select()
      .from(agents)
      .where(eq(agents.role, task.agentRole))
      .get();
    if (!agent) throw new Error("Agent not found");

    const response = await generateText({
      model: anthropic(MODEL_ID),
      system: agent.systemPrompt,
      prompt: task.description,
    });

    await db
      .update(tasks)
      .set({ status: "completed", result: response.text, updatedAt: Date.now() })
      .where(eq(tasks.id, taskId));
  } catch (err) {
    await db
      .update(tasks)
      .set({
        status: "failed",
        result: String(err),
        updatedAt: Date.now(),
      })
      .where(eq(tasks.id, taskId));
  }
}
