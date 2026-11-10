import { db } from "./index";
import { agents } from "./schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";

let seeded = false;

export async function seed() {
  if (seeded) return;
  seeded = true;

  const existing = await db
    .select()
    .from(agents)
    .where(eq(agents.role, "research"))
    .get();

  if (!existing) {
    await db.insert(agents).values({
      id: randomUUID(),
      name: "Research Agent",
      role: "research",
      systemPrompt:
        "You are a research agent helping a Swedish ecommerce operator running a Shopify store. Given a topic, return a concise summary in 3–5 bullet points. Be specific, factual, and cite sources when relevant. Reply in Swedish.",
      createdAt: Date.now(),
    });
  }
}
