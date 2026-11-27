import { parseAnswer, parseQuestion, statusCodes } from "@/lib/ai-contract";
export const maxDuration = 120;
import { createClient } from "@/utils/supabase/server";

function json(body: unknown, status: number) {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

async function limitedText(
  body: ReadableStream<Uint8Array> | null,
  limit: number
) {
  if (!body) throw new Error("missing_body");

  const reader = body.getReader();
  const decoder = new TextDecoder();

  let size = 0;
  let value = "";

  try {
    while (true) {
      const { done, value: chunk } = await reader.read();

      if (done) return value + decoder.decode();

      size += chunk.byteLength;

      if (size > limit) {
        await reader.cancel();
        throw new Error("body_too_large");
      }

      value += decoder.decode(chunk, { stream: true });
    }
  } finally {
    reader.releaseLock();
  }
}

export async function POST(request: Request) {
  // Obtain the access token, then verify that exact token before forwarding it.
  let accessToken: string;

  try {
    const supabase = await createClient();
    const { data: sessionData, error: sessionError } =
      await supabase.auth.getSession();

    const token = sessionData.session?.access_token;

    if (sessionError || !token) {
      return json(
        { detail: "Authentication required. Please sign in." },
        401
      );
    }

    const { data, error } = await supabase.auth.getClaims(token);

    if (
      error ||
      !data?.claims?.sub ||
      data.claims.role !== "authenticated" ||
      data.claims.is_anonymous === true
    ) {
      return json(
        { detail: "Authentication required. Please sign in." },
        401
      );
    }
    accessToken = token;
  } catch {
    return json(
      { detail: "Authentication service is unavailable." },
      503
    );
  }
  // Origin validation is not user authentication.
  const origin = request.headers.get("origin");

  if (origin) {
    try {
      const incoming = new URL(origin);
      const host =
        request.headers.get("host") || new URL(request.url).host;

      if (
        !["http:", "https:"].includes(incoming.protocol) ||
        incoming.host !== host
      ) {
        return json(
          { detail: "Request origin is not permitted." },
          403
        );
      }
    } catch {
      return json(
        { detail: "Request origin is not permitted." },
        403
      );
    }
  }

  if (
    !request.headers
      .get("content-type")
      ?.toLowerCase()
      .startsWith("application/json")
  ) {
    return json({ detail: "Send a JSON question." }, 415);
  }

  let question: string | null;

  try {
    question = parseQuestion(
      JSON.parse(await limitedText(request.body, 16384))
    );
  } catch {
    return json({ detail: "Invalid question request." }, 422);
  }

  if (!question) {
    return json(
      { detail: "Enter a question of 1-2,000 characters." },
      422
    );
  }

  // Private server-to-server authentication.
  const sharedSecret = process.env.AI_DEMO_SHARED_SECRET || "";

  if (sharedSecret.trim().length < 32) {
    return json(
      { detail: "AI service access is not configured." },
      503
    );
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 75000);

  try {
    const base = new URL(
      process.env.AI_API_BASE_URL || "http://127.0.0.1:8001"
    );

    if (
      !["http:", "https:"].includes(base.protocol) ||
      base.username ||
      base.password ||
      base.pathname !== "/" ||
      base.search ||
      base.hash
    ) {
      throw new Error("invalid_configuration");
    }

    // Plain HTTP is permitted only for local development.
    if (
      base.protocol === "http:" &&
      !["localhost", "127.0.0.1", "[::1]"].includes(base.hostname)
    ) {
      throw new Error("insecure_backend_configuration");
    }

    const upstream = await fetch(new URL("/api/ai/ask", base), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-AI-Demo-Secret": sharedSecret,
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ question }),
      cache: "no-store",
      redirect: "error",
      signal: controller.signal,
    });
    if (upstream.status === 429) {
      await upstream.body?.cancel();

      return json(
        {
          detail: "AI demo request limit reached. Please try again later.",
        },
        429
      );
    }

    // Sanitize backend authentication failures.
    if (upstream.status === 401) {
      await upstream.body?.cancel();

      return json(
        { detail: "AI service access is unavailable." },
        503
      );
    }

    if (upstream.status === 422) {
      await upstream.body?.cancel();

      return json(
        { detail: "The backend could not validate this question." },
        422
      );
    }

    if (
      !upstream.headers
        .get("content-type")
        ?.includes("application/json")
    ) {
      throw new Error("invalid_response");
    }

    const answer = parseAnswer(
      JSON.parse(await limitedText(upstream.body, 65536))
    );

    if (!answer || statusCodes[answer.status] !== upstream.status) {
      throw new Error("invalid_response");
    }

    return json(answer, upstream.status);
  } catch {
    // Never expose raw upstream bodies, URLs, or credentials.
    return json(
      {
        detail:
          "Could not get a valid response from the AI backend. Check that the demo server is running and try again.",
      },
      502
    );
  } finally {
    clearTimeout(timer);
  }
}
