import type { Metadata } from "next";
import Assistant from "./assistant";

export const metadata: Metadata = {
  title: "CampusPilot AI Assistant",
  description: "A fictional university information demonstration.",
};

export default function AIPage() {
  return <Assistant />;
}
