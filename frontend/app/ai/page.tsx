
import type { Metadata } from "next";
import { Suspense } from "react";
import Assistant from "./assistant";

export const metadata: Metadata = {
  title: "CampusPilot AI Assistant",
  description: "A fictional university information demonstration.",
};

type AIPageProps = {
  searchParams: Promise<{ category?: string | string[] }>;
};

export default function AIPage({ searchParams }: AIPageProps) {
  return (
    <Suspense fallback={<div>Loading AI Assistant...</div>}>
      <AIPageContent searchParams={searchParams} />
    </Suspense>
  );
}

async function AIPageContent({ searchParams }: AIPageProps) {
  const params = await searchParams;
  const requestedCategory = params.category;

  const initialCategory =
    requestedCategory === "News" || requestedCategory === "Policies"
      ? requestedCategory
      : null;

  return <Assistant initialCategory={initialCategory} />;
}
