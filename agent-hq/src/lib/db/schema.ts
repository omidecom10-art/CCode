import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const agents = sqliteTable("agents", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  role: text("role").notNull().unique(),
  systemPrompt: text("system_prompt").notNull(),
  createdAt: integer("created_at").notNull(),
});

export const tasks = sqliteTable("tasks", {
  id: text("id").primaryKey(),
  agentRole: text("agent_role")
    .notNull()
    .references(() => agents.role),
  description: text("description").notNull(),
  status: text("status", {
    enum: ["pending", "running", "completed", "failed"],
  }).notNull(),
  result: text("result"),
  createdAt: integer("created_at").notNull(),
  updatedAt: integer("updated_at").notNull(),
});
