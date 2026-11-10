import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { tasks, agents } from "@/lib/db/schema";
import { desc, eq } from "drizzle-orm";

export async function GET() {
  const rows = await db
    .select({
      id: tasks.id,
      agentRole: tasks.agentRole,
      agentName: agents.name,
      description: tasks.description,
      status: tasks.status,
      result: tasks.result,
      createdAt: tasks.createdAt,
      updatedAt: tasks.updatedAt,
    })
    .from(tasks)
    .leftJoin(agents, eq(tasks.agentRole, agents.role))
    .orderBy(desc(tasks.createdAt));

  return NextResponse.json(rows);
}
