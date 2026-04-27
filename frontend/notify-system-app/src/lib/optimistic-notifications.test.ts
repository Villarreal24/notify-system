import { describe, expect, it } from "vitest";

import type { NotificationLog } from "@/lib/api";

import {
  applyOptimisticLogAction,
  buildOptimisticLog,
} from "./optimistic-notifications";

const existingLog: NotificationLog = {
  id: "log-1",
  message: "Existing",
  category_id: 1,
  category_name: "Sports",
  channel_id: 2,
  channel_name: "E-Mail",
  user_id: "user-1",
  user_name: "Alice",
  status: "SUCCESS",
  error_message: null,
  created_at: "2026-04-26T00:00:00Z",
};

describe("optimistic notification helpers", () => {
  it("builds a pending optimistic log with the selected category name", () => {
    const log = buildOptimisticLog({
      categories: [{ id: 1, name: "Sports" }],
      categoryId: 1,
      message: "Sports update",
      temporaryId: "optimistic-1",
      createdAt: "2026-04-26T01:00:00Z",
    });

    expect(log).toMatchObject({
      id: "optimistic-1",
      message: "Sports update",
      category_id: 1,
      category_name: "Sports",
      status: "PENDING",
      channel_id: null,
      user_id: null,
    });
  });

  it("adds optimistic logs to the top of the list", () => {
    const optimistic = buildOptimisticLog({
      categories: [{ id: 1, name: "Sports" }],
      categoryId: 1,
      message: "Sports update",
      temporaryId: "optimistic-1",
      createdAt: "2026-04-26T01:00:00Z",
    });

    const logs = applyOptimisticLogAction([existingLog], {
      type: "add",
      log: optimistic,
    });

    expect(logs.map((log) => log.id)).toEqual(["optimistic-1", "log-1"]);
  });

  it("replaces a temporary log with confirmed backend logs", () => {
    const confirmed: NotificationLog = {
      ...existingLog,
      id: "log-2",
      message: "Confirmed",
      status: "PENDING",
    };
    const temporary: NotificationLog = {
      ...existingLog,
      id: "optimistic-1",
      message: "Pending",
      status: "PENDING",
    };

    const logs = applyOptimisticLogAction([temporary, existingLog], {
      type: "confirmMany",
      temporaryId: temporary.id,
      logs: [confirmed],
    });

    expect(logs.map((log) => log.id)).toEqual(["log-2", "log-1"]);
  });

  it("rolls back a temporary optimistic log", () => {
    const temporary: NotificationLog = {
      ...existingLog,
      id: "optimistic-1",
      status: "PENDING",
    };

    const logs = applyOptimisticLogAction([temporary, existingLog], {
      type: "rollback",
      temporaryId: temporary.id,
    });

    expect(logs).toEqual([existingLog]);
  });
});
