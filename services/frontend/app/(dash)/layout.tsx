import { DashProviders } from "@/lib/dash-providers";

export default function DashLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return <DashProviders>{children}</DashProviders>;
}
