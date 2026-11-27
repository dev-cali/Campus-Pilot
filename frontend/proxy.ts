
import { createServerClient } from "@supabase/ssr";
import { NextRequest, NextResponse } from "next/server";

function copyAuthState(
  source: NextResponse,
  destination: NextResponse
) {
  source.cookies.getAll().forEach((cookie) => {
    destination.cookies.set(cookie);
  });

  for (const name of ["cache-control", "expires", "pragma"]) {
    const value = source.headers.get(name);

    if (value) {
      destination.headers.set(name, value);
    }
  }
}

export async function proxy(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  const isApiRequest = request.nextUrl.pathname.startsWith("/api/ai/");

  // Fail closed if Supabase configuration is missing.
  if (!url || !key) {
    if (isApiRequest) {
      return NextResponse.json(
        { detail: "Authentication is not configured." },
        { status: 503 }
      );
    }

    return new NextResponse("Authentication is not configured.", {
      status: 503,
      headers: { "Cache-Control": "no-store" },
    });
  }

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },

      setAll(cookiesToSet, headers) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });

        supabaseResponse = NextResponse.next({ request });

        cookiesToSet.forEach(({ name, value, options }) => {
          supabaseResponse.cookies.set(name, value, options);
        });

        Object.entries(headers).forEach(([name, value]) => {
          supabaseResponse.headers.set(name, value);
        });
      },
    },
  });

  // Verify the JWT signature and refresh the session when necessary.
  const { data, error } = await supabase.auth.getClaims();

  const claims = error ? null : data?.claims;
  const authenticated =
    typeof claims?.sub === "string" &&
    claims.sub.length > 0 &&
    claims.role === "authenticated" &&
    claims.is_anonymous !== true;

  if (!authenticated) {
    if (isApiRequest) {
      const response = NextResponse.json(
        { detail: "Authentication required." },
        { status: 401 }
      );

      copyAuthState(supabaseResponse, response);
      response.headers.set("Cache-Control", "no-store");

      return response;
    }

    const loginUrl = request.nextUrl.clone();

    loginUrl.pathname = "/login";
    loginUrl.search = "";
    loginUrl.searchParams.set(
      "next",
      `${request.nextUrl.pathname}${request.nextUrl.search}`
    );

    const response = NextResponse.redirect(loginUrl);

    copyAuthState(supabaseResponse, response);
    response.headers.set("Cache-Control", "no-store");

    return response;
  }

  supabaseResponse.headers.set("Cache-Control", "no-store");

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/ai/:path*",
    "/api/ai/:path*",
    "/scholarships/:path*",
    "/events/:path*",
    "/documents/:path*",
    "/academics/:path*",
    "/departments/:path*",
    "/profile/:path*",
    "/settings/:path*",
  ],
};
