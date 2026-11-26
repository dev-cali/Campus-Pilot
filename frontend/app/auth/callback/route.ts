
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/utils/supabase/server";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const requestedNext =
    request.nextUrl.searchParams.get("next") || "/";

  // Only allow redirects to paths on this application.
  const redirectTarget = new URL(
    requestedNext,
    request.nextUrl.origin
  );

  const safeNext =
    requestedNext.startsWith("/") &&
    !requestedNext.startsWith("//") &&
    !requestedNext.includes("\\") &&
    redirectTarget.origin === request.nextUrl.origin
      ? redirectTarget
      : new URL("/", request.nextUrl.origin);

  if (!code) {
    const loginUrl = new URL("/login", request.nextUrl.origin);
    loginUrl.searchParams.set(
      "error",
      "confirmation_failed"
    );

    return NextResponse.redirect(loginUrl);
  }

  try {
    const supabase = await createClient();

    const { error } =
      await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      const loginUrl = new URL("/login", request.nextUrl.origin);

      loginUrl.searchParams.set(
        "error",
        "confirmation_failed"
      );

      return NextResponse.redirect(loginUrl);
    }

    return NextResponse.redirect(safeNext);
  } catch {
    const loginUrl = new URL("/login", request.nextUrl.origin);

    loginUrl.searchParams.set(
      "error",
      "confirmation_failed"
    );

    return NextResponse.redirect(loginUrl);
  }
}
