import type { ChatMessage, Agent } from "./types";

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── Pattern matchers ────────────────────────────────────────

const FILE_PATTERN = /\b[\w/-]+\.\w{1,5}\b/;
const WHAT_IF_PATTERN = /what\s*if|simulate|impact.*chang|what.*happen/i;
const WHO_OWNS_PATTERN = /who\s*owns|owner|maintainer|responsible/i;
const BLAST_PATTERN = /blast\s*radius|affect|depend|downstream|break/i;
const DEBUG_PATTERN = /debug|error|500|bug|crash|fail|exception|issue/i;
const EXPLAIN_PATTERN = /explain|how\s*does|what\s*does|walk.*through|trace/i;

// ─── Response builders ──────────────────────────────────────

function buildFileAnalysis(file: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  return {
    messages: [
      {
        id: generateId(),
        role: "system",
        content: "Analyzing file dependencies...",
        timestamp: now(),
      },
      {
        id: generateId(),
        role: "assistant",
        content: `I analyzed **${file}** and found:\n\n- **12 direct dependents** that import from this file\n- **3 processes** that include this file in their execution path: Auth Flow, API Gateway, Checkout Flow\n- **Risk level: HIGH** — changes here affect the authentication pipeline\n\nKey callers: \`validateUser\`, \`authMiddleware\`, \`apiGateway\`\n\nWould you like me to trace any specific execution path?`,
        timestamp: now(),
        agent: "Code Explorer",
        status: "complete",
        files: [file, "src/auth/validate.ts", "src/middleware/auth.ts"],
      },
    ],
    files: [file, "src/auth/validate.ts", "src/middleware/auth.ts"],
    patterns: ["High coupling", "Shared dependency"],
    problems: [],
  };
}

function buildWhatIfResponse(message: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  const file = message.match(FILE_PATTERN)?.[0] || "src/auth/validate.ts";
  return {
    messages: [
      {
        id: generateId(),
        role: "system",
        content: "Running impact simulation...",
        timestamp: now(),
      },
      {
        id: generateId(),
        role: "assistant",
        content: `Simulation complete for modifying **${file}**:\n\n**Blast Radius:**\n- 8 files directly affected\n- 3 execution flows impacted\n- 2 test suites would need updates\n\n**Risk Assessment: MEDIUM**\n\nAffected processes:\n1. Auth Flow — token validation will change\n2. API Gateway — middleware depends on this\n3. Test Suite — 4 test cases reference this function\n\n**Recommendation:** Add a feature flag to roll out changes incrementally. Update tests first.`,
        timestamp: now(),
        agent: "Cross-Checker",
        status: "complete",
        files: [file],
      },
    ],
    files: [file, "tests/auth.test.ts", "src/middleware/auth.ts"],
    patterns: ["Impact cascade", "Feature flag recommended"],
    problems: ["3 execution flows would be affected"],
  };
}

function buildOwnerResponse(message: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  const file = message.match(FILE_PATTERN)?.[0] || "src/auth/validate.ts";
  return {
    messages: [
      {
        id: generateId(),
        role: "assistant",
        content: `Ownership analysis for **${file}**:\n\n| Owner | Commits | Last Modified | Coverage |\n|-------|---------|---------------|----------|\n| Alice Chen | 47 | 2 days ago | 62% |\n| Bob Smith | 23 | 1 week ago | 28% |\n| Carol Davis | 8 | 3 weeks ago | 10% |\n\n**Primary owner:** Alice Chen (62% of recent changes)\n**Code review recommended from:** Bob Smith (deep knowledge of auth flow)`,
        timestamp: now(),
        agent: "Code Explorer",
        status: "complete",
        files: [file],
      },
    ],
    files: [file],
    patterns: ["Single primary owner"],
    problems: [],
  };
}

function buildBlastResponse(message: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  const file = message.match(FILE_PATTERN)?.[0] || "src/checkout/handler.ts";
  return {
    messages: [
      {
        id: generateId(),
        role: "system",
        content: "Computing blast radius...",
        timestamp: now(),
      },
      {
        id: generateId(),
        role: "assistant",
        content: `Blast radius for **${file}**:\n\n**Depth 1 (WILL BREAK):**\n- \`processPayment\` — direct caller\n- \`sendReceipt\` — direct caller\n- \`routeRequest\` — imports this handler\n\n**Depth 2 (LIKELY AFFECTED):**\n- \`apiGateway\` — routes through routeRequest\n- \`checkout.test.ts\` — tests this directly\n\n**Depth 3 (MAY NEED TESTING):**\n- \`httpServer\` — top-level entry point\n\n**Total affected: 6 files, 2 processes, 1 test suite**`,
        timestamp: now(),
        agent: "Code Tracer",
        status: "complete",
        files: [file, "src/checkout/payment.ts", "src/api/router.ts"],
      },
    ],
    files: [file, "src/checkout/payment.ts", "src/api/router.ts", "tests/checkout.test.ts"],
    patterns: ["Deep dependency chain", "Cross-module impact"],
    problems: ["6 files in blast radius"],
  };
}

function buildDebugResponse(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  message: string
): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  return {
    messages: [
      {
        id: generateId(),
        role: "system",
        content: "Spawning investigation agents...",
        timestamp: now(),
      },
      {
        id: generateId(),
        role: "assistant",
        content: `I investigated the issue and found a likely root cause:\n\n**Problem:** Missing null check on \`user.paymentMethod\` in the checkout flow.\n\n**Evidence:**\n1. \`handleCheckout\` at line 44 calls \`processPayment(user)\` without validating payment method\n2. \`processPayment\` at line 28 assumes \`user.paymentMethod\` is always present\n3. When \`paymentMethod\` is null, Stripe SDK throws an unhandled error\n\n**Impact:** ~2,400 daily users affected (those without saved payment methods)\n\n**Suggested fix:**\n\`\`\`typescript\nif (!user.paymentMethod) {\n  throw new PaymentMethodRequiredError(user.id);\n}\n\`\`\`\n\nShall I trace the full execution path or check for similar patterns?`,
        timestamp: now(),
        agent: "Code Explorer",
        status: "complete",
        files: ["src/checkout/handler.ts", "src/checkout/payment.ts"],
      },
    ],
    files: ["src/checkout/handler.ts", "src/checkout/payment.ts", "src/api/gateway.ts"],
    patterns: ["Missing null check", "No payment validation", "Unhandled error path"],
    problems: ["500 on checkout for users without payment method"],
  };
}

function buildExplainResponse(message: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  const file = message.match(FILE_PATTERN)?.[0] || "validateUser";
  return {
    messages: [
      {
        id: generateId(),
        role: "assistant",
        content: `Here is the execution trace for **${file}**:\n\n\`\`\`\nhttpServer\n  -> apiGateway\n    -> authMiddleware\n      -> validateUser\n        -> checkRole (role-based access)\n        -> getToken (JWT validation)\n        -> hashPassword (credential check)\n        -> UserRepository.findById (DB lookup)\n\`\`\`\n\n**Key observations:**\n- validateUser is called on every authenticated request\n- It sits at the intersection of 3 execution flows\n- Risk level: HIGH because 6 functions depend on its return type\n\nThe function first checks the JWT token via \`getToken\`, then validates the role via \`checkRole\`, and finally verifies credentials with \`hashPassword\` if this is a fresh login.`,
        timestamp: now(),
        agent: "Code Tracer",
        status: "complete",
        files: ["src/auth/validate.ts", "src/auth/roles.ts", "src/auth/token.ts"],
      },
    ],
    files: ["src/auth/validate.ts", "src/auth/roles.ts", "src/auth/token.ts"],
    patterns: ["High fan-out function", "Authentication bottleneck"],
    problems: [],
  };
}

function buildGenericResponse(message: string): {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
} {
  return {
    messages: [
      {
        id: generateId(),
        role: "assistant",
        content: `I searched the context graph for relevant information about "${message.slice(0, 60)}${message.length > 60 ? "..." : ""}".\n\nI found **23 nodes** and **41 edges** related to your query across 4 clusters:\n- **Auth** (6 nodes) — authentication and authorization\n- **API Gateway** (4 nodes) — request routing and middleware\n- **Checkout** (4 nodes) — payment processing flow\n- **Data Layer** (2 nodes) — database access patterns\n\nCould you be more specific? For example:\n- "What if I modify src/auth/validate.ts?"\n- "Who owns the checkout module?"\n- "Trace the execution path from apiGateway to processPayment"\n- "Debug the 500 errors in checkout"`,
        timestamp: now(),
        status: "complete",
      },
    ],
    files: [],
    patterns: [],
    problems: [],
  };
}

// ─── Hive mode agent simulation ─────────────────────────────

export function getHiveAgents(): Agent[] {
  return [
    {
      id: "agent-explorer",
      name: "Code Explorer",
      status: "pending",
      objective: "Read and analyze source files",
    },
    {
      id: "agent-tracer",
      name: "Code Tracer",
      status: "pending",
      objective: "Trace execution paths",
    },
    {
      id: "agent-checker",
      name: "Cross-Checker",
      status: "pending",
      objective: "Validate findings",
    },
  ];
}

export function getSingleAgent(): Agent[] {
  return [
    {
      id: "agent-single",
      name: "Context Agent",
      status: "pending",
      objective: "Analyze and respond",
    },
  ];
}

/** Simulate agents running sequentially with status updates. */
export async function simulateAgentExecution(
  agents: Agent[],
  onUpdate: (agents: Agent[]) => void
): Promise<void> {
  const updated = [...agents];

  for (let i = 0; i < updated.length; i++) {
    // Set current agent to running
    updated[i] = { ...updated[i], status: "running" };
    onUpdate([...updated]);

    // Simulate work
    await delay(800 + Math.random() * 1200);

    // Set to completed
    updated[i] = { ...updated[i], status: "completed" };
    onUpdate([...updated]);
  }
}

// ─── Main simulator entry point ─────────────────────────────

export interface SimulatedResponse {
  messages: ChatMessage[];
  files: string[];
  patterns: string[];
  problems: string[];
}

export async function simulateAIResponse(
  userMessage: string
): Promise<SimulatedResponse> {
  // Simulate thinking delay (1-2 seconds)
  await delay(1000 + Math.random() * 1000);

  const message = userMessage.toLowerCase();

  // Check for file references first
  if (FILE_PATTERN.test(userMessage) && !WHAT_IF_PATTERN.test(message) && !WHO_OWNS_PATTERN.test(message) && !BLAST_PATTERN.test(message)) {
    return buildFileAnalysis(userMessage.match(FILE_PATTERN)![0]);
  }

  // Pattern-based routing
  if (WHAT_IF_PATTERN.test(message)) {
    return buildWhatIfResponse(userMessage);
  }
  if (WHO_OWNS_PATTERN.test(message)) {
    return buildOwnerResponse(userMessage);
  }
  if (BLAST_PATTERN.test(message)) {
    return buildBlastResponse(userMessage);
  }
  if (DEBUG_PATTERN.test(message)) {
    return buildDebugResponse(userMessage);
  }
  if (EXPLAIN_PATTERN.test(message)) {
    return buildExplainResponse(userMessage);
  }

  return buildGenericResponse(userMessage);
}
