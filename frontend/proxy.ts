
import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "node:crypto";

function secureEqual(left: string, right: string): boolean {
  const leftHash = createHash("sha256").update(left).digest();
  const rightHash = createHash("sha256").update(right).digest();

  return timingSafeEqual(leftHash, rightHash);
}

function unauthorized() {
  return new NextResponse("Evaluator authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="CampusPilot AI Demo", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

export function proxy(request: NextRequest) {
  const username = process.env.AI_DEMO_USERNAME || "";
  const password = process.env.AI_DEMO_PASSWORD || "";

  // Fail closed if evaluator credentials are not configured.
  if (!username || password.trim().length < 24) {
    return new NextResponse("Demo access is not configured.", {
      status: 503,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  }

  const authorization = request.headers.get("authorization");

  if (!authorization || !authorization.startsWith("Basic ")) {
    return unauthorized();
  }

  const expectedCredentials = Buffer.from(
    `${username}:${password}`,
    "utf8"
  ).toString("base64");

  const suppliedCredentials = authorization.slice(6);

  if (!secureEqual(suppliedCredentials, expectedCredentials)) {
    return unauthorized();
  }

  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");

  return response;
}

// Protect both the AI page and its server-side API endpoints.
export const config = {
  matcher: ["/ai/:path*", "/api/ai/:path*"],
};
